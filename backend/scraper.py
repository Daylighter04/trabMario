"""
Scraper do IMDb Top 250 usando httpx e BeautifulSoup,
com suporte a fallback estruturado de filmes clássicos.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MOVIES_FILE = DATA_DIR / "movies.csv"

# Fallback curado dos maiores filmes clássicos do IMDb Top 250
FALLBACK_MOVIES = [
    {"title": "The Shawshank Redemption", "year": 1994, "duration": "142 min", "duration_min": 142, "rating": 9.3, "votes": 2850000, "genre": "Drama"},
    {"title": "The Godfather", "year": 1972, "duration": "175 min", "duration_min": 175, "rating": 9.2, "votes": 2000000, "genre": "Crime"},
    {"title": "The Dark Knight", "year": 2008, "duration": "152 min", "duration_min": 152, "rating": 9.0, "votes": 2800000, "genre": "Action"},
    {"title": "The Godfather Part II", "year": 1974, "duration": "202 min", "duration_min": 202, "rating": 9.0, "votes": 1350000, "genre": "Crime"},
    {"title": "12 Angry Men", "year": 1957, "duration": "96 min", "duration_min": 96, "rating": 9.0, "votes": 850000, "genre": "Drama"},
    {"title": "Schindler's List", "year": 1993, "duration": "195 min", "duration_min": 195, "rating": 9.0, "votes": 1420000, "genre": "Biography"},
    {"title": "The Lord of the Rings: The Return of the King", "year": 2003, "duration": "201 min", "duration_min": 201, "rating": 9.0, "votes": 1950000, "genre": "Adventure"},
    {"title": "Pulp Fiction", "year": 1994, "duration": "154 min", "duration_min": 154, "rating": 8.9, "votes": 2180000, "genre": "Crime"},
    {"title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001, "duration": "178 min", "duration_min": 178, "rating": 8.9, "votes": 1980000, "genre": "Adventure"},
    {"title": "The Good, the Bad and the Ugly", "year": 1966, "duration": "178 min", "duration_min": 178, "rating": 8.8, "votes": 800000, "genre": "Western"},
    {"title": "Forrest Gump", "year": 1994, "duration": "142 min", "duration_min": 142, "rating": 8.8, "votes": 2220000, "genre": "Drama"},
    {"title": "Fight Club", "year": 1999, "duration": "139 min", "duration_min": 139, "rating": 8.8, "votes": 2270000, "genre": "Drama"},
    {"title": "The Lord of the Rings: The Two Towers", "year": 2002, "duration": "179 min", "duration_min": 179, "rating": 8.8, "votes": 1760000, "genre": "Adventure"},
    {"title": "Inception", "year": 2010, "duration": "148 min", "duration_min": 148, "rating": 8.8, "votes": 2500000, "genre": "Sci-Fi"},
    {"title": "Star Wars: Episode V - The Empire Strikes Back", "year": 1980, "duration": "124 min", "duration_min": 124, "rating": 8.7, "votes": 1360000, "genre": "Action"},
    {"title": "The Matrix", "year": 1999, "duration": "136 min", "duration_min": 136, "rating": 8.7, "votes": 2030000, "genre": "Sci-Fi"},
    {"title": "Goodfellas", "year": 1990, "duration": "145 min", "duration_min": 145, "rating": 8.7, "votes": 1240000, "genre": "Biography"},
    {"title": "One Flew Over the Cuckoo's Nest", "year": 1975, "duration": "133 min", "duration_min": 133, "rating": 8.7, "votes": 1060000, "genre": "Drama"},
    {"title": "Interstellar", "year": 2014, "duration": "169 min", "duration_min": 169, "rating": 8.7, "votes": 2020000, "genre": "Sci-Fi"},
    {"title": "Seven", "year": 1995, "duration": "127 min", "duration_min": 127, "rating": 8.6, "votes": 1760000, "genre": "Crime"},
    {"title": "The Silence of the Lambs", "year": 1991, "duration": "118 min", "duration_min": 118, "rating": 8.6, "votes": 1530000, "genre": "Thriller"},
    {"title": "Saving Private Ryan", "year": 1998, "duration": "169 min", "duration_min": 169, "rating": 8.6, "votes": 1470000, "genre": "War"},
    {"title": "City of God", "year": 2002, "duration": "130 min", "duration_min": 130, "rating": 8.6, "votes": 790000, "genre": "Crime"},
    {"title": "Spirited Away", "year": 2001, "duration": "125 min", "duration_min": 125, "rating": 8.6, "votes": 830000, "genre": "Animation"},
    {"title": "Life Is Beautiful", "year": 1997, "duration": "116 min", "duration_min": 116, "rating": 8.6, "votes": 730000, "genre": "Comedy"},
    {"title": "The Green Mile", "year": 1999, "duration": "189 min", "duration_min": 189, "rating": 8.6, "votes": 1380000, "genre": "Drama"},
    {"title": "Star Wars: Episode IV - A New Hope", "year": 1977, "duration": "121 min", "duration_min": 121, "rating": 8.6, "votes": 1430000, "genre": "Action"},
    {"title": "Terminator 2: Judgment Day", "year": 1991, "duration": "137 min", "duration_min": 137, "rating": 8.6, "votes": 1150000, "genre": "Action"},
    {"title": "Back to the Future", "year": 1985, "duration": "116 min", "duration_min": 116, "rating": 8.5, "votes": 1280000, "genre": "Adventure"},
    {"title": "The Pianist", "year": 2002, "duration": "150 min", "duration_min": 150, "rating": 8.5, "votes": 890000, "genre": "Biography"},
    {"title": "Psycho", "year": 1960, "duration": "109 min", "duration_min": 109, "rating": 8.5, "votes": 700000, "genre": "Horror"},
    {"title": "Parasite", "year": 2019, "duration": "132 min", "duration_min": 132, "rating": 8.5, "votes": 910000, "genre": "Drama"},
    {"title": "Gladiator", "year": 2000, "duration": "155 min", "duration_min": 155, "rating": 8.5, "votes": 1580000, "genre": "Action"},
    {"title": "The Lion King", "year": 1994, "duration": "88 min", "duration_min": 88, "rating": 8.5, "votes": 1110000, "genre": "Animation"},
    {"title": "Leon: The Professional", "year": 1994, "duration": "110 min", "duration_min": 110, "rating": 8.5, "votes": 1220000, "genre": "Action"},
    {"title": "The Departed", "year": 2006, "duration": "151 min", "duration_min": 151, "rating": 8.5, "votes": 1400000, "genre": "Crime"},
    {"title": "Whiplash", "year": 2014, "duration": "106 min", "duration_min": 106, "rating": 8.5, "votes": 950000, "genre": "Drama"},
    {"title": "The Prestige", "year": 2006, "duration": "130 min", "duration_min": 130, "rating": 8.5, "votes": 1410000, "genre": "Mystery"},
    {"title": "Casablanca", "year": 1942, "duration": "102 min", "duration_min": 102, "rating": 8.5, "votes": 600000, "genre": "Romance"},
    {"title": "Alien", "year": 1979, "duration": "117 min", "duration_min": 117, "rating": 8.5, "votes": 930000, "genre": "Sci-Fi"},
    {"title": "Apocalypse Now", "year": 1979, "duration": "147 min", "duration_min": 147, "rating": 8.4, "votes": 700000, "genre": "Drama"},
    {"title": "Spider-Man: Into the Spider-Verse", "year": 2018, "duration": "117 min", "duration_min": 117, "rating": 8.4, "votes": 640000, "genre": "Animation"},
    {"title": "Memento", "year": 2000, "duration": "113 min", "duration_min": 113, "rating": 8.4, "votes": 1290000, "genre": "Mystery"},
    {"title": "WALL-E", "year": 2008, "duration": "98 min", "duration_min": 98, "rating": 8.4, "votes": 1170000, "genre": "Animation"},
    {"title": "Avengers: Infinity War", "year": 2018, "duration": "149 min", "duration_min": 149, "rating": 8.4, "votes": 1170000, "genre": "Action"},
    {"title": "Django Unchained", "year": 2012, "duration": "165 min", "duration_min": 165, "rating": 8.4, "votes": 1640000, "genre": "Western"},
    {"title": "Coco", "year": 2017, "duration": "105 min", "duration_min": 105, "rating": 8.4, "votes": 570000, "genre": "Animation"},
    {"title": "Braveheart", "year": 1995, "duration": "178 min", "duration_min": 178, "rating": 8.4, "votes": 1080000, "genre": "Biography"},
    {"title": "Oldboy", "year": 2003, "duration": "120 min", "duration_min": 120, "rating": 8.4, "votes": 610000, "genre": "Action"},
    {"title": "Oppenheimer", "year": 2023, "duration": "180 min", "duration_min": 180, "rating": 8.9, "votes": 750000, "genre": "Biography"},
]


def parse_duration_to_min(dur_str: str) -> int:
    """Converte '2h 22m', '142 min' ou '142' em minutos inteiros."""
    if not dur_str:
        return 120
    dur_str = str(dur_str).strip().lower()
    h_match = re.search(r"(\d+)\s*h", dur_str)
    m_match = re.search(r"(\d+)\s*m", dur_str)

    if h_match or m_match:
        hours = int(h_match.group(1)) if h_match else 0
        mins = int(m_match.group(1)) if m_match else 0
        return hours * 60 + mins

    digits = re.findall(r"\d+", dur_str)
    if digits:
        return int(digits[0])
    return 120


def parse_votes_count(vote_str: str) -> int:
    """Converte '2.8M', '950K' ou '2,800,000' em número inteiro."""
    if not vote_str:
        return 500000
    vote_str = str(vote_str).strip().upper().replace(",", "")
    try:
        if "M" in vote_str:
            num = float(vote_str.replace("M", "").strip())
            return int(num * 1_000_000)
        elif "K" in vote_str:
            num = float(vote_str.replace("K", "").strip())
            return int(num * 1_000)
        digits = re.findall(r"\d+", vote_str)
        if digits:
            return int("".join(digits))
    except Exception:
        pass
    return 500000


def scrape_imdb_top(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Tenta extrair o ranking Top 250 do IMDb via scraping com httpx e BeautifulSoup.
    Caso haja bloqueio, desafio WAF ou rate limit, utiliza a lista mockada de clássicos.
    Salva o resultado em backend/data/movies.csv.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Se o arquivo já existe e não foi solicitado force_refresh, carrega ele
    if MOVIES_FILE.exists() and not force_refresh:
        try:
            df = pd.read_csv(MOVIES_FILE)
            if len(df) > 0:
                return {
                    "success": True,
                    "count": len(df),
                    "source": "cache",
                    "message": "Dados carregados a partir do cache local em movies.csv",
                }
        except Exception:
            pass

    movies = []
    source = "fallback_mock"

    url = "https://www.imdb.com/chart/top/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    try:
        with httpx.Client(follow_redirects=True, timeout=12.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select("li.ipc-metadata-list-summary-item")

                for item in items:
                    title_elem = item.select_one("h3.ipc-title__text")
                    if not title_elem:
                        continue
                    full_title = title_elem.text.strip()
                    # Remove numeração inicial como "1. "
                    title = re.sub(r"^\d+\.\s*", "", full_title)

                    # Metadados secundários: ano, duração, censura
                    metadata = item.select("span.cli-title-metadata-item")
                    year = 2000
                    duration_str = "120 min"
                    if len(metadata) >= 1:
                        digits = re.findall(r"\d{4}", metadata[0].text)
                        if digits:
                            year = int(digits[0])
                    if len(metadata) >= 2:
                        duration_str = metadata[1].text.strip()

                    # Avaliação (Rating)
                    rating_elem = item.select_one("span.ipc-rating-star--rating")
                    rating = 8.5
                    if rating_elem:
                        try:
                            rating = float(rating_elem.text.strip().replace(",", "."))
                        except Exception:
                            pass

                    # Votos
                    vote_elem = item.select_one("span.ipc-rating-star--voteCount")
                    votes = 1000000
                    if vote_elem:
                        votes = parse_votes_count(vote_elem.text)

                    # Gênero heurístico ou inferido
                    genre = "Drama"
                    lower_t = title.lower()
                    if any(w in lower_t for w in ["star wars", "matrix", "interstellar", "alien", "terminator", "inception"]):
                        genre = "Sci-Fi"
                    elif any(w in lower_t for w in ["godfather", "pulp fiction", "goodfellas", "seven", "city of god"]):
                        genre = "Crime"
                    elif any(w in lower_t for w in ["dark knight", "gladiator", "avengers", "leon", "oldboy"]):
                        genre = "Action"
                    elif any(w in lower_t for w in ["lord of the rings", "back to the future"]):
                        genre = "Adventure"
                    elif any(w in lower_t for w in ["spirited away", "lion king", "spider-man", "wall-e", "coco"]):
                        genre = "Animation"
                    elif any(w in lower_t for w in ["schindler", "pianist", "braveheart", "oppenheimer"]):
                        genre = "Biography"

                    dur_min = parse_duration_to_min(duration_str)
                    movies.append({
                        "title": title,
                        "year": year,
                        "duration": f"{dur_min} min",
                        "duration_min": dur_min,
                        "rating": rating,
                        "votes": votes,
                        "genre": genre,
                    })

                if len(movies) >= 10:
                    source = "imdb_live"

    except Exception as e:
        print(f"[IMDb Scraper Warning] Falha na requisição ao vivo: {e}. Usando lista mockada de clássicos.")

    # Se a raspagem falhou ou retornou poucos itens, usar fallback
    if len(movies) < 10:
        movies = FALLBACK_MOVIES.copy()
        source = "fallback_mock"

    df = pd.DataFrame(movies)
    df.to_csv(MOVIES_FILE, index=False, encoding="utf-8")

    return {
        "success": True,
        "count": len(df),
        "source": source,
        "message": (
            "Filmes atualizados via Scraping ao vivo do IMDb!"
            if source == "imdb_live"
            else "IMDb aplicou desafio anti-bot/WAF. Lista clássica mockada carregada com sucesso."
        ),
    }


def get_movies_dataframe() -> pd.DataFrame:
    """Carrega o DataFrame de filmes a partir de backend/data/movies.csv."""
    if not MOVIES_FILE.exists():
        scrape_imdb_top(force_refresh=True)

    df = pd.read_csv(MOVIES_FILE)
    if "duration_min" not in df.columns:
        df["duration_min"] = df["duration"].apply(parse_duration_to_min)
    return df


if __name__ == "__main__":
    result = scrape_imdb_top(force_refresh=True)
    print(f"Resultado do Scraper: {result}")
    df = get_movies_dataframe()
    print(df.head())
