"""
Minimal MCP server exposing:
  - 1 tool:      get_stock_price(ticker)      -> calls yfinance (real, no API key needed)
  - 2 resources: stock://{ticker}/profile      -> company overview (Alpha Vantage, or mock)
                 stock://{ticker}/news         -> recent news sentiment (Alpha Vantage, or mock)

This file is normally launched as a subprocess by the MCP client in graph.py
(stdio transport) — you don't need to run it directly.

Mock mode: if ALPHA_VANTAGE_API_KEY isn't set, the two resources return clearly
labeled mock data so the whole project runs out of the box with zero signup.
Add a free key (https://www.alphavantage.co/support/#api-key) to .env for real data.
"""

import os
from dotenv import load_dotenv

load_dotenv()
from pathlib import Path
import httpx
from mcp.server.fastmcp import FastMCP
import yfinance as yf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

mcp = FastMCP("stock-tools")

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"
MOCK_MODE = ALPHA_VANTAGE_KEY is None

# ---------------------------------------------------------------------------
# RAG setup — full pipeline with ingestion, chunking, and embeddings.
# 1. Load raw documents from knowledge_base/*.txt
# 2. Split into semantic chunks (~256 tokens, with overlap)
# 3. Embed chunks with sentence-transformers (semantic embeddings)
# 4. Build in-memory index for fast similarity search
# ---------------------------------------------------------------------------
KB_DIR = Path(__file__).parent / "knowledge_base"

try:
    from sentence_transformers import SentenceTransformer
    USE_SEMANTIC_EMBEDDINGS = True
except ImportError:
    USE_SEMANTIC_EMBEDDINGS = False
    import warnings
    warnings.warn("sentence-transformers not installed; falling back to TF-IDF")


def _chunk_text(text: str, chunk_size: int = 256, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _load_and_chunk_knowledge_base() -> list[dict]:
    """Load docs, chunk them, and return with source tracking."""
    chunks = []
    for path in sorted(KB_DIR.glob("*.txt")):
        text = path.read_text().strip()
        doc_chunks = _chunk_text(text)
        for i, chunk in enumerate(doc_chunks):
            chunks.append({
                "source": path.name,
                "chunk_id": i,
                "text": chunk,
                "full_text": text,  # keep full doc for context
            })
    return chunks


_KB_CHUNKS = _load_and_chunk_knowledge_base()

# Initialize embeddings model (if available) or fall back to TF-IDF
if USE_SEMANTIC_EMBEDDINGS:
    _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    _KB_EMBEDDINGS = None
    _KB_EMBEDDING_TEXTS = None
    if _KB_CHUNKS:
        _KB_EMBEDDING_TEXTS = [c["text"] for c in _KB_CHUNKS]
        _KB_EMBEDDINGS = _EMBEDDING_MODEL.encode(_KB_EMBEDDING_TEXTS)
else:
    _VECTORIZER = TfidfVectorizer(stop_words="english")
    _KB_EMBEDDINGS = None
    _KB_EMBEDDING_TEXTS = None
    if _KB_CHUNKS:
        _KB_EMBEDDINGS = _VECTORIZER.fit_transform([c["text"] for c in _KB_CHUNKS])
        _KB_EMBEDDING_TEXTS = [c["text"] for c in _KB_CHUNKS]


# ---------------------------------------------------------------------------
# TOOL — an action the agent calls with arguments. Real external call
# (no key needed): yfinance pulls live data from Yahoo Finance.
# ---------------------------------------------------------------------------
@mcp.tool()
def get_stock_price(ticker: str) -> dict:
    """Fetch the latest closing price for a stock ticker."""
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if data.empty:
            return {"ticker": ticker, "error": f"No price data for {ticker}"}
        return {"ticker": ticker, "price": float(data["Close"].iloc[-1])}
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ---------------------------------------------------------------------------
# TOOL — RAG retrieval. Semantic search with embeddings or TF-IDF fallback.
# Returns the top-k most relevant chunks from the local policy knowledge base.
# This is the "R" in RAG; the agent that calls it (compliance_node in graph.py)
# does the "G" by feeding the retrieved text into an LLM prompt as grounding.
# ---------------------------------------------------------------------------
@mcp.tool()
def retrieve_policy_context(query: str, top_k: int = 2) -> list[dict]:
    """Retrieve the most relevant internal policy excerpts for a query.

    Uses semantic embeddings (sentence-transformers) for retrieval, or TF-IDF
    as fallback. Returns top-k chunks with similarity scores.
    """
    if not _KB_CHUNKS or _KB_EMBEDDINGS is None:
        return []

    import numpy as np

    if USE_SEMANTIC_EMBEDDINGS:
        # Semantic retrieval: embed query and compute cosine similarity
        query_embedding = _EMBEDDING_MODEL.encode([query])
        if query_embedding.ndim > 1:
            query_embedding = query_embedding[0]
        # Use sklearn for robust cosine similarity computation
        scores = cosine_similarity([query_embedding], _KB_EMBEDDINGS)[0].tolist()
    else:
        # TF-IDF fallback
        query_vec = _VECTORIZER.transform([query])
        scores = cosine_similarity(query_vec, _KB_EMBEDDINGS)[0].tolist()

    # Rank chunks by score and deduplicate by source document
    ranked = sorted(
        zip(_KB_CHUNKS, scores),
        key=lambda pair: pair[1],
        reverse=True
    )

    # Return top-k, preferring one chunk per document for diversity
    results = []
    seen_sources = set()
    for chunk, score in ranked:
        if chunk["source"] not in seen_sources or len(results) < top_k:
            results.append({
                "source": chunk["source"],
                "text": chunk["text"],
                "score": round(float(score), 3),
            })
            seen_sources.add(chunk["source"])
            if len(results) >= top_k:
                break

    return results


# ---------------------------------------------------------------------------
# RESOURCE 1 — company profile. Real Alpha Vantage call if a key is set,
# otherwise mock data.
# ---------------------------------------------------------------------------
@mcp.resource("stock://{ticker}/profile")
async def company_profile(ticker: str) -> dict:
    """Company overview: sector, market cap, description."""
    if MOCK_MODE:
        return {
            "ticker": ticker,
            "name": f"{ticker} Inc. (mock)",
            "sector": "Technology",
            "market_cap": "1000000000",
            "description": "Mock profile — set ALPHA_VANTAGE_API_KEY for live data.",
        }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params={
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": ALPHA_VANTAGE_KEY,
        })
        data = resp.json()
    if not data or "Name" not in data:
        return {"ticker": ticker, "error": "No profile data returned (bad symbol or rate-limited)"}
    return {
        "ticker": ticker,
        "name": data.get("Name"),
        "sector": data.get("Sector"),
        "market_cap": data.get("MarketCapitalization"),
        "description": data.get("Description"),
    }


# ---------------------------------------------------------------------------
# RESOURCE 2 — recent news + sentiment. Same real/mock split as above.
# ---------------------------------------------------------------------------
@mcp.resource("stock://{ticker}/news")
async def company_news(ticker: str) -> list[dict]:
    """Recent news headlines and sentiment for a ticker."""
    if MOCK_MODE:
        # Set ticker to "BADNEWS" to preview the negative-sentiment / human-review
        # branch of the conditional edge without needing a live API key.
        if ticker.upper() == "BADNEWS":
            return [
                {"title": "BADNEWS Inc. misses earnings, shares tumble (mock)", "sentiment": "Bearish"},
                {"title": "Regulators open probe into BADNEWS Inc. (mock)", "sentiment": "Bearish"},
            ]
        return [
            {"title": f"{ticker} beats quarterly estimates (mock)", "sentiment": "Bullish"},
            {"title": f"{ticker} announces new product line (mock)", "sentiment": "Somewhat-Bullish"},
        ]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params={
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "limit": 5,
            "apikey": ALPHA_VANTAGE_KEY,
        })
        data = resp.json()
    feed = data.get("feed", [])
    if not feed:
        return [{"title": "No recent news found", "sentiment": "Neutral"}]
    return [
        {"title": item["title"], "sentiment": item["overall_sentiment_label"]}
        for item in feed
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")
