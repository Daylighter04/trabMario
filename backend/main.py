"""
API FastAPI para o Sistema de Recomendação MovieLens (Filtragem Colaborativa k-NN)
Endpoints:
- GET /api/stats
- GET /api/users
- GET /api/movies
- GET /api/recommend/user-user
- GET /api/recommend/similar-movies
- GET /api/recommend/item-item
- GET /api/compare
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from recommender import get_recommender

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = FastAPI(
    title="MovieLens k-NN Recommender API",
    description="Sistema de Recomendação de Filmes com Filtragem Colaborativa k-NN por Cosseno (User-User e Item-Item).",
    version="3.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "online", "model": "MovieLens k-NN Cosine"}


@app.get("/api/stats")
def get_matrix_stats():
    """
    Retorna dimensões da matriz (610 x 9724), uso de memória da matriz densa vs esparsa,
    total de avaliações, média geral e distribuição de estrelas.
    """
    try:
        rec = get_recommender()
        return rec.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users")
def get_users():
    """Retorna a lista de IDs de usuários disponíveis (1 a 610)."""
    try:
        rec = get_recommender()
        users = rec.get_users_list()
        return {"total_users": len(users), "users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/movies")
def search_movies(
    search: Optional[str] = None,
    limit: int = 50,
):
    """Lista/pesquisa filmes por nome para a busca de similares e autocomplete."""
    try:
        rec = get_recommender()
        lim = int(limit) if str(limit).isdigit() else 50
        movies = rec.search_movies(query=search, limit=lim)
        return {"total": len(movies), "movies": movies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommend/user-user")
def recommend_user_user(
    user_id: int = 65,
    k: int = 20,
    n: int = 10,
):
    """
    Retorna a média do usuário, vizinhos mais próximos e o Top-N com nota prevista
    pela fórmula exata do Colab:
    r^_ui = r_bar_u + sum_v sim(u, v)(r_vi - r_bar_v) / sum_v |sim(u, v)|
    """
    try:
        rec = get_recommender()
        u_id = int(user_id)
        k_val = int(k)
        n_val = int(n)

        u_idx = rec.user_idx_map.get(u_id)
        if u_idx is None:
            raise HTTPException(status_code=404, detail=f"Usuário {u_id} não encontrado.")

        user_mean = float(rec.user_means[u_idx])
        user_ratings_count = int((rec.matriz_densa.values[u_idx] > 0).sum())

        neighbors = rec.vizinhos_usuario(u_id, k=k_val)
        recommendations = rec.recomendar_usuario(u_id, n=n_val, k=k_val)

        return {
            "user_id": u_id,
            "user_mean": round(user_mean, 2),
            "user_total_ratings": user_ratings_count,
            "k": k_val,
            "n": n_val,
            "neighbors": neighbors,
            "recommendations": recommendations,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommend/similar-movies")
def recommend_similar_movies(
    movie_id: int = 1,
    k: int = 10,
):
    """
    Retorna os filmes mais parecidos com o filme escolhido (ex: Toy Story / movieId 1)
    e a pontuação de similaridade pelo modelo k-NN Item-Item.
    """
    try:
        rec = get_recommender()
        m_id = int(movie_id)
        k_val = int(k)

        if m_id not in rec.movie_idx_map:
            raise HTTPException(status_code=404, detail=f"Filme com ID {m_id} não encontrado.")

        target = rec.movie_titles_dict.get(
            m_id, {"movieId": m_id, "title": f"Movie {m_id}", "genres": "-"}
        )
        similar_movies = rec.vizinhos_filme(m_id, k=k_val)

        return {
            "target_movie": target,
            "k": k_val,
            "similar_movies": similar_movies,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommend/item-item")
def recommend_item_item(
    user_id: int = 65,
    k: int = 20,
    n: int = 10,
    nota_min: float = 4.0,
):
    """
    Retorna o Top-N baseado nos filmes favoritos do usuário (nota >= nota_min)
    com score acumulado de similaridade.
    """
    try:
        rec = get_recommender()
        u_id = int(user_id)
        k_val = int(k)
        n_val = int(n)
        min_rating = float(nota_min)

        u_idx = rec.user_idx_map.get(u_id)
        if u_idx is None:
            raise HTTPException(status_code=404, detail=f"Usuário {u_id} não encontrado.")

        user_mean = float(rec.user_means[u_idx])
        user_ratings_count = int((rec.matriz_densa.values[u_idx] > 0).sum())
        recommendations = rec.recomendar_itemitem(u_id, n=n_val, k=k_val, nota_min=min_rating)

        return {
            "user_id": u_id,
            "user_mean": round(user_mean, 2),
            "user_total_ratings": user_ratings_count,
            "k": k_val,
            "n": n_val,
            "nota_min": min_rating,
            "recommendations": recommendations,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compare")
def compare_approaches(
    user_id: int = 65,
    n: int = 10,
    k: int = 20,
):
    """
    Parte 4 do Colab:
    Retorna o comparativo completo (User-User vs Item-Item e filmes em comum no Top-N).
    """
    try:
        rec = get_recommender()
        u_id = int(user_id)
        n_val = int(n)
        k_val = int(k)
        return rec.comparar_abordagens(user_id=u_id, n=n_val, k=k_val)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SERVIR FRONTEND ESTÁTICO
# ============================================================
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "MovieLens Recommender API online."}

    @app.get("/index.html")
    def serve_index_html():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/dataset.html")
    def serve_dataset_html():
        return FileResponse(FRONTEND_DIR / "dataset.html")

    @app.get("/analytics.html")
    def serve_analytics_html():
        return FileResponse(FRONTEND_DIR / "analytics.html")

    @app.get("/app.js")
    def serve_app_js():
        return FileResponse(FRONTEND_DIR / "app.js")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
