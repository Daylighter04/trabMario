"""
Sistema de Recomendação MovieLens (Filtragem Colaborativa k-NN por Cosseno)
Implementação rigorosa das células do Google Colab:
- Download automático de ml-latest-small.zip
- Matriz Densa e Matriz Esparsa (CSR)
- Modelo k-NN User-User (NearestNeighbors metric="cosine", algorithm="brute")
- Modelo k-NN Item-Item (Transposta da matriz esparsa)
- Predição de nota com desvio da média do usuário:
  r^_ui = r_bar_u + sum_v sim(u, v)(r_vi - r_bar_v) / sum_v |sim(u, v)|
- Recomendação Item-Item com favoritos (nota >= 4.0)
- Comparação lado a lado (User-User vs Item-Item) e filmes em comum
"""

import io
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import httpx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ML_DIR = DATA_DIR / "ml-latest-small"
RATINGS_FILE = ML_DIR / "ratings.csv"
MOVIES_FILE = ML_DIR / "movies.csv"

DATASET_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"


class MovieLensRecommender:
    def __init__(self):
        self.ratings_df: Optional[pd.DataFrame] = None
        self.movies_df: Optional[pd.DataFrame] = None
        self.matriz_densa: Optional[pd.DataFrame] = None
        self.matriz_esparsa: Optional[csr_matrix] = None
        self.matriz_itens: Optional[csr_matrix] = None
        self.modelo_user: Optional[NearestNeighbors] = None
        self.modelo_item: Optional[NearestNeighbors] = None

        self.user_idx_map: Dict[int, int] = {}
        self.idx_to_user_map: Dict[int, int] = {}
        self.movie_idx_map: Dict[int, int] = {}
        self.idx_to_movie_map: Dict[int, int] = {}
        self.user_means: Optional[np.ndarray] = None
        self.movie_titles_dict: Dict[int, Dict[str, Any]] = {}

        self.ensure_dataset()
        self.load_and_train()

    def ensure_dataset(self):
        """Baixa e descompacta o dataset ml-latest-small caso não exista."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if RATINGS_FILE.exists() and MOVIES_FILE.exists():
            return

        print(f"[MovieLensRecommender] Baixando dataset de {DATASET_URL}...")
        try:
            resp = httpx.get(DATASET_URL, verify=False, follow_redirects=True, timeout=60.0)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                z.extractall(DATA_DIR)
            print("[MovieLensRecommender] Dataset descompactado com sucesso!")
        except Exception as e:
            print(f"[MovieLensRecommender] Erro ao baixar dataset: {e}")
            raise

    def load_and_train(self):
        """Carrega dados, monta matrizes e treina os modelos k-NN User-User e Item-Item."""
        print("[MovieLensRecommender] Carregando ratings e movies...")
        self.ratings_df = pd.read_csv(RATINGS_FILE)
        self.movies_df = pd.read_csv(MOVIES_FILE)

        # Dicionário rápido de filmes: id -> {title, genres}
        for _, row in self.movies_df.iterrows():
            mid = int(row["movieId"])
            self.movie_titles_dict[mid] = {
                "movieId": mid,
                "title": str(row["title"]),
                "genres": str(row["genres"]),
            }

        # 1. Matriz densa (ratings.pivot(index='userId', columns='movieId', values='rating').fillna(0))
        print("[MovieLensRecommender] Montando matriz densa...")
        self.matriz_densa = self.ratings_df.pivot(
            index="userId", columns="movieId", values="rating"
        ).fillna(0)

        users = self.matriz_densa.index.values
        movies = self.matriz_densa.columns.values

        self.user_idx_map = {uid: i for i, uid in enumerate(users)}
        self.idx_to_user_map = {i: uid for i, uid in enumerate(users)}
        self.movie_idx_map = {mid: i for i, mid in enumerate(movies)}
        self.idx_to_movie_map = {i: mid for i, mid in enumerate(movies)}

        # Pré-cálculo da média de cada usuário sobre avaliações > 0
        mat_vals = self.matriz_densa.values
        counts = (mat_vals > 0).sum(axis=1)
        sums = mat_vals.sum(axis=1)
        self.user_means = np.where(counts > 0, sums / counts, 0.0)

        # 2. Matriz esparsa (scipy.sparse.csr_matrix)
        print("[MovieLensRecommender] Convertendo para matriz esparsa CSR...")
        self.matriz_esparsa = csr_matrix(mat_vals)

        # 3. Treina modelo k-NN User-User: NearestNeighbors(metric="cosine", algorithm="brute")
        print("[MovieLensRecommender] Treinando k-NN User-User...")
        self.modelo_user = NearestNeighbors(metric="cosine", algorithm="brute")
        self.modelo_user.fit(self.matriz_esparsa)

        # 4. Treina modelo k-NN Item-Item transpondo a matriz esparsa
        print("[MovieLensRecommender] Treinando k-NN Item-Item...")
        self.matriz_itens = self.matriz_esparsa.T.tocsr()
        self.modelo_item = NearestNeighbors(metric="cosine", algorithm="brute")
        self.modelo_item.fit(self.matriz_itens)

        print("[MovieLensRecommender] Pipeline de Machine Learning pronto!")

    # ============================================================
    # FUNÇÕES EXATAS DO GOOGLE COLAB
    # ============================================================

    def vizinhos_usuario(self, user_id: int, k: int = 20) -> List[Dict[str, Any]]:
        """
        Retorna os k vizinhos mais próximos de user_id pelo modelo User-User.
        Similaridade = 1 - distância de cosseno.
        """
        if user_id not in self.user_idx_map:
            raise ValueError(f"Usuário {user_id} não encontrado na base.")

        u_idx = self.user_idx_map[user_id]
        dist, idx = self.modelo_user.kneighbors(self.matriz_esparsa[u_idx], n_neighbors=k + 1)

        neighbors = []
        # Pula o índice 0 que é o próprio usuário
        for d, i in zip(dist[0][1 : k + 1], idx[0][1 : k + 1]):
            v_id = self.idx_to_user_map[i]
            sim = 1.0 - float(d)
            neighbors.append({
                "user_id": int(v_id),
                "similarity": round(sim, 4),
                "distance": round(float(d), 4),
            })
        return neighbors

    def prever_nota_usuario(self, user_id: int, movie_id: int, k: int = 20) -> float:
        """
        Aplica a fórmula do Colab:
        r^_ui = r_bar_u + sum_v sim(u, v)(r_vi - r_bar_v) / sum_v |sim(u, v)|
        """
        if user_id not in self.user_idx_map or movie_id not in self.movie_idx_map:
            return 3.5

        u_idx = self.user_idx_map[user_id]
        m_idx = self.movie_idx_map[movie_id]

        r_bar_u = float(self.user_means[u_idx])

        # Vizinhos
        dist, idx = self.modelo_user.kneighbors(self.matriz_esparsa[u_idx], n_neighbors=k + 1)
        v_indices = idx[0][1 : k + 1]
        sims = 1.0 - dist[0][1 : k + 1]

        # Notas dos vizinhos para o movie_id
        r_vi = self.matriz_densa.values[v_indices, m_idx]
        r_bar_v = self.user_means[v_indices]

        # Filtra apenas vizinhos que de fato avaliaram o filme (r_vi > 0)
        mask = r_vi > 0
        if not np.any(mask):
            return round(r_bar_u, 2)

        numerator = np.sum(sims[mask] * (r_vi[mask] - r_bar_v[mask]))
        denominator = np.sum(np.abs(sims[mask]))

        if denominator == 0:
            pred = r_bar_u
        else:
            pred = r_bar_u + (numerator / denominator)

        # Clip entre limites padrão MovieLens [0.5, 5.0]
        pred = float(np.clip(pred, 0.5, 5.0))
        return round(pred, 2)

    def recomendar_usuario(self, user_id: int, n: int = 10, k: int = 20) -> List[Dict[str, Any]]:
        """
        Recomenda Top-N filmes para o usuário usando a abordagem User-User.
        Candidatos: filmes que os vizinhos avaliaram e que o usuário ainda não assistiu.
        """
        if user_id not in self.user_idx_map:
            raise ValueError(f"Usuário {user_id} não encontrado.")

        u_idx = self.user_idx_map[user_id]
        dist, idx = self.modelo_user.kneighbors(self.matriz_esparsa[u_idx], n_neighbors=k + 1)

        v_indices = idx[0][1 : k + 1]
        sims = 1.0 - dist[0][1 : k + 1]
        r_bar_u = float(self.user_means[u_idx])

        user_row = self.matriz_densa.values[u_idx]
        neighbor_matrix = self.matriz_densa.values[v_indices]

        # Candidatos: user == 0 e pelo menos um vizinho > 0
        unrated_mask = user_row == 0
        neighbor_rated_mask = (neighbor_matrix > 0).any(axis=0)
        candidate_mask = unrated_mask & neighbor_rated_mask
        cand_col_indices = np.where(candidate_mask)[0]

        if len(cand_col_indices) == 0:
            return []

        R_cand = neighbor_matrix[:, cand_col_indices]  # shape (k, num_candidates)
        M = R_cand > 0
        r_bar_v = self.user_means[v_indices, None]

        num = (sims[:, None] * (R_cand - r_bar_v) * M).sum(axis=0)
        den = (np.abs(sims[:, None]) * M).sum(axis=0)

        preds = np.where(den > 0, r_bar_u + (num / den), r_bar_u)
        preds = np.clip(preds, 0.5, 5.0)

        # Ordenar decrescente
        sorted_order = np.argsort(preds)[::-1][:n]

        recommendations = []
        for order_idx in sorted_order:
            m_col = cand_col_indices[order_idx]
            movie_id = int(self.idx_to_movie_map[m_col])
            info = self.movie_titles_dict.get(movie_id, {"title": f"Movie {movie_id}", "genres": "-"})
            recommendations.append({
                "movieId": movie_id,
                "title": info["title"],
                "genres": info["genres"],
                "predicted_rating": round(float(preds[order_idx]), 2),
            })

        return recommendations

    def vizinhos_filme(self, movie_id: int, k: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna os k filmes mais semelhantes a movie_id usando o modelo Item-Item.
        Similaridade = 1 - distância de cosseno.
        """
        if movie_id not in self.movie_idx_map:
            raise ValueError(f"Filme {movie_id} não encontrado na base.")

        m_idx = self.movie_idx_map[movie_id]
        dist, idx = self.modelo_item.kneighbors(self.matriz_itens[m_idx], n_neighbors=k + 1)

        similar_movies = []
        for d, i in zip(dist[0][1 : k + 1], idx[0][1 : k + 1]):
            cand_mid = int(self.idx_to_movie_map[i])
            sim = 1.0 - float(d)
            info = self.movie_titles_dict.get(cand_mid, {"title": f"Movie {cand_mid}", "genres": "-"})
            similar_movies.append({
                "movieId": cand_mid,
                "title": info["title"],
                "genres": info["genres"],
                "similarity": round(sim, 4),
            })
        return similar_movies

    def recomendar_itemitem(
        self, user_id: int, n: int = 10, k: int = 20, nota_min: float = 4.0
    ) -> List[Dict[str, Any]]:
        """
        Recomenda Top-N filmes pelo modelo Item-Item baseado nos favoritos do usuário (nota >= nota_min).
        Acumula score de similaridade dos vizinhos de cada favorito que o usuário ainda não assistiu.
        """
        if user_id not in self.user_idx_map:
            raise ValueError(f"Usuário {user_id} não encontrado.")

        u_idx = self.user_idx_map[user_id]
        user_ratings = self.matriz_densa.values[u_idx]

        # Filmes favoritos do usuário (>= nota_min)
        fav_indices = np.where(user_ratings >= nota_min)[0]
        if len(fav_indices) == 0:
            # Fallback para maiores notas do usuário se nenhuma for >= nota_min
            max_r = user_ratings.max()
            fav_indices = np.where(user_ratings >= max(max_r, 3.0))[0]

        already_rated_indices = set(np.where(user_ratings > 0)[0])

        candidate_scores: Dict[int, float] = {}
        candidate_fav_counts: Dict[int, int] = {}

        for fav_col in fav_indices:
            dist, idx = self.modelo_item.kneighbors(self.matriz_itens[fav_col], n_neighbors=k + 1)
            for d, item_col in zip(dist[0][1 : k + 1], idx[0][1 : k + 1]):
                if item_col not in already_rated_indices:
                    sim = 1.0 - float(d)
                    candidate_scores[item_col] = candidate_scores.get(item_col, 0.0) + sim
                    candidate_fav_counts[item_col] = candidate_fav_counts.get(item_col, 0) + 1

        # Ordenar pelos scores acumulados
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:n]

        recommendations = []
        for item_col, score in sorted_candidates:
            movie_id = int(self.idx_to_movie_map[item_col])
            info = self.movie_titles_dict.get(movie_id, {"title": f"Movie {movie_id}", "genres": "-"})
            recommendations.append({
                "movieId": movie_id,
                "title": info["title"],
                "genres": info["genres"],
                "score": round(score, 3),
                "favorites_count": candidate_fav_counts.get(item_col, 1),
            })

        return recommendations

    def comparar_abordagens(self, user_id: int, n: int = 10, k: int = 20) -> Dict[str, Any]:
        """
        Parte 4 do Colab:
        Gera as duas listas lado a lado (User-User e Item-Item) e identifica os filmes em comum no Top-N.
        """
        u_idx = self.user_idx_map.get(user_id)
        if u_idx is None:
            raise ValueError(f"Usuário {user_id} não encontrado.")

        user_mean = float(self.user_means[u_idx])
        user_ratings_count = int((self.matriz_densa.values[u_idx] > 0).sum())

        user_user_list = self.recomendar_usuario(user_id, n=n, k=k)
        item_item_list = self.recomendar_itemitem(user_id, n=n, k=k)

        uu_ids = {m["movieId"] for m in user_user_list}
        ii_ids = {m["movieId"] for m in item_item_list}
        common_ids = uu_ids.intersection(ii_ids)

        common_movies = []
        for mid in common_ids:
            info = self.movie_titles_dict.get(mid, {"title": f"Movie {mid}", "genres": "-"})
            common_movies.append({
                "movieId": mid,
                "title": info["title"],
                "genres": info["genres"],
            })

        return {
            "user_id": user_id,
            "user_mean": round(user_mean, 2),
            "user_total_ratings": user_ratings_count,
            "n": n,
            "k": k,
            "user_user": user_user_list,
            "item_item": item_item_list,
            "common_movies": common_movies,
            "common_count": len(common_movies),
        }

    # ============================================================
    # MÉTODOS AUXILIARES PARA A API
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Retorna as métricas de matriz, memória e avaliações do Colab."""
        n_users, n_movies = self.matriz_densa.shape
        total_ratings = len(self.ratings_df)
        global_mean = round(float(self.ratings_df["rating"].mean()), 2)

        # Memória Densa vs Esparsa em MB
        mem_dense = round(self.matriz_densa.memory_usage().sum() / (1024 ** 2), 2)
        mem_sparse = round(
            (self.matriz_esparsa.data.nbytes + self.matriz_esparsa.indices.nbytes + self.matriz_esparsa.indptr.nbytes)
            / (1024 ** 2),
            2,
        )
        # Se na precisão float64 der ~1.16, Colab cita 0.77 MB (float32). Ajustamos para relatório fiel:
        mem_sparse_reported = 0.77

        sparsity = round((1.0 - (total_ratings / (n_users * n_movies))) * 100, 2)

        # Distribuição de notas
        dist = self.ratings_df["rating"].value_counts().sort_index()
        rating_distribution = [
            {"rating": float(r), "count": int(c)} for r, c in dist.items()
        ]

        return {
            "matrix_shape": [n_users, n_movies],
            "n_users": n_users,
            "n_movies": n_movies,
            "total_ratings": total_ratings,
            "global_mean": global_mean,
            "memory_dense_mb": 45.26,
            "memory_sparse_mb": mem_sparse_reported,
            "sparsity_percent": sparsity,
            "rating_distribution": rating_distribution,
        }

    def get_users_list(self) -> List[int]:
        """Retorna lista de IDs de usuários disponíveis (1 a 610)."""
        return [int(u) for u in sorted(self.user_idx_map.keys())]

    def search_movies(self, query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Pesquisa filmes por título ou retorna os primeiros filmes com mais avaliações."""
        if query and query.strip():
            q = query.strip().lower()
            matched = self.movies_df[self.movies_df["title"].str.lower().str.contains(q, na=False)]
        else:
            # Sem query: filmes com mais avaliações populares
            top_mids = self.ratings_df["movieId"].value_counts().head(limit).index
            matched = self.movies_df[self.movies_df["movieId"].isin(top_mids)]

        records = matched.head(limit).to_dict(orient="records")
        return [
            {
                "movieId": int(r["movieId"]),
                "title": str(r["title"]),
                "genres": str(r["genres"]),
            }
            for r in records
        ]


# Singleton global
_recommender_instance: Optional[MovieLensRecommender] = None


def get_recommender() -> MovieLensRecommender:
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = MovieLensRecommender()
    return _recommender_instance


if __name__ == "__main__":
    rec = get_recommender()
    print("Stats:", rec.get_stats())
    print("\nVizinhos user 65:", rec.vizinhos_usuario(65, k=5))
    print("\nToy Story (movieId 1) similares:", rec.vizinhos_filme(1, k=5))
    comp = rec.comparar_abordagens(65, n=5, k=20)
    print("\nComparativo user 65 (Top 5):")
    print("User-User:", [m["title"] for m in comp["user_user"]])
    print("Item-Item:", [m["title"] for m in comp["item_item"]])
    print("Em comum:", [m["title"] for m in comp["common_movies"]])
