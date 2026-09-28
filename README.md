# MovieLens k-NN Recommender Platform 🍿🎬

Plataforma completa de **Filtragem Colaborativa baseada em k-NN por Cosseno (User-User e Item-Item)**, implementando rigorosamente todas as etapas e formulações matemáticas do notebook **Google Colab MovieLens**.

O backend foi construído em **FastAPI (Python, Scipy Sparse CSR, Scikit-Learn k-NN e Pandas)**, e o frontend segue fielmente a **identidade visual oficial IMDb Dark Theme** (`#121212`, `#1f1f1f`, `#2d2d2d`, `#f5c518`).

---

## 🗂️ Estrutura do Projeto

```text
bank-marketing-analytics/
├── backend/
│   ├── data/
│   │   └── ml-latest-small/      # Dataset oficial MovieLens (ratings.csv, movies.csv, etc.)
│   ├── recommender.py            # Pipeline de ML: download, matrizes (densa/CSR), k-NN e fórmulas Colab
│   ├── main.py                   # API FastAPI com todos os endpoints e rotas estáticas
│   ├── run.py                    # Script de inicialização facilitado do servidor
│   └── requirements.txt          # Dependências: fastapi, uvicorn, pandas, numpy, scipy, scikit-learn, httpx
├── frontend/
│   ├── index.html                # Comparador & Top-N (Parte 4): User-User vs Item-Item lado a lado
│   ├── dataset.html              # Explorador de Filmes Similares (Parte 3): k-NN Item-Item com busca
│   ├── analytics.html            # Métricas do Modelo & Matrizes (Partes 1 e 2): CSR, esparsidade e vizinhança
│   └── app.js                    # Camada JS integrada à API em http://127.0.0.1:8000/api
└── README.md                     # Documentação completa
```

---

## 🚀 Como Executar

### 1. Instalar Dependências
```bash
pip install -r backend/requirements.txt
```

### 2. Iniciar a Aplicação
Execute o script no terminal:
```bash
python backend/run.py
```
*Ou via Uvicorn diretamente:*
```bash
uvicorn backend.main:app --reload --port 8000
```

### 3. Acessar no Navegador
- ⚖️ **Comparador & Top-N (Parte 4):** [http://localhost:8000/index.html](http://localhost:8000/index.html)
- 🔍 **Filmes Similares (Parte 3):** [http://localhost:8000/dataset.html](http://localhost:8000/dataset.html)
- 📊 **Métricas do Modelo (Partes 1 & 2):** [http://localhost:8000/analytics.html](http://localhost:8000/analytics.html)
- 📖 **Documentação Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔬 Algoritmos e Fórmulas Matemáticas Implementadas

### 1. Esparsidade e Matriz CSR (Compressed Sparse Row)
- **Dimensões:** $610 \text{ usuários} \times 9.724 \text{ filmes}$ ($5.931.640$ células).
- **Memória Densa:** $45,26\text{ MB}$.
- **Memória Esparsa (CSR):** $0,77\text{ MB}$ (redução de $\approx 98,3\%$).
- **Esparsidade:** $98,30\%$ de células sem avaliação preenchida.

### 2. Filtragem Colaborativa User-User (Parte 2)
Predição da nota do usuário $u$ para o item $i$ ajustada pelo viés individual (média):
$$\hat{r}_{ui} = \bar{r}_u + \frac{\sum_{v \in N_k(u)} sim(u, v) \cdot (r_{vi} - \bar{r}_v)}{\sum_{v \in N_k(u)} |sim(u, v)|}$$

Onde:
- $\bar{r}_u$: Média histórica das notas dadas pelo usuário $u$.
- $sim(u, v) = 1 - \text{distância\_cosseno}(u, v)$.
- $r_{vi} - \bar{r}_v$: Desvio da nota dada pelo vizinho $v$ em relação à sua própria média histórica.

### 3. Filtragem Colaborativa Item-Item (Parte 3)
Modelo treinado na matriz esparsa transposta ($\mathbf{M}^T$ de dimensão $9.724 \times 610$).
Para cada filme favorito do usuário ($\text{nota} \ge 4,0$), recupera-se os $k$ filmes mais similares e calcula-se a pontuação acumulada:
$$\text{Score}(i) = \sum_{j \in \text{Favoritos}(u)} sim(j, i)$$

### 4. Comparador de Abordagens (Parte 4)
Gera o ranking Top-$N$ pelas duas técnicas em paralelo e calcula a sobreposição / consenso (filmes em comum).

---

## 📡 Endpoints da API REST

| Método | Endpoint | Parâmetros | Descrição |
|---|---|---|---|
| `GET` | `/api/stats` | - | Estatísticas da matriz ($610 \times 9724$, memória, esparsidade, distribuição). |
| `GET` | `/api/users` | - | Lista de IDs de usuários disponíveis ($1$ a $610$). |
| `GET` | `/api/movies` | `search`, `limit` | Pesquisa filmes por título com suporte a autocomplete. |
| `GET` | `/api/recommend/user-user` | `user_id`, `k`, `n` | Vizinhos mais próximos e Top-$N$ com predição de nota ponderada. |
| `GET` | `/api/recommend/similar-movies` | `movie_id`, `k` | $k$ filmes mais parecidos com o título de referência por cosseno. |
| `GET` | `/api/recommend/item-item` | `user_id`, `k`, `n`, `nota_min` | Top-$N$ baseado nos favoritos do usuário com pontuação acumulada. |
| `GET` | `/api/compare` | `user_id`, `n`, `k` | Comparativo lado a lado (User-User vs Item-Item) e total em comum. |
| `GET` | `/api/health` | - | Status operacional do modelo e API. |
