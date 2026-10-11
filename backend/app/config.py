import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "SpecSure"
    VERSION: str = "2.0.0"
    
    # Database URL: asyncpg for PostgreSQL with pgvector, or aiosqlite for local fallback
    # Zero-config default = local SQLite file (demo anywhere, offline). docker-compose sets PostgreSQL + pgvector.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./specsure.db")
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC", 
        "postgresql://bharatstandards:password@localhost:5432/bharatstandards"
    )
    
    # Gemini API for extraction and natural language prose polish
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    
    # Embedding model settings (Multilingual)
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
    
    # Dense index over the Indian Standards corpus (scope clauses); "none" = BM25 only
    CORPUS_EMBEDDING_MODEL: str = os.getenv("CORPUS_EMBEDDING_MODEL", "BAAI/bge-m3")   # falls back to intfloat/multilingual-e5-small

    # Reranker model
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    
    # Server configuration
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Gemini model used only for optional language polish / extraction assist (never for decisions)
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Seed the demo tender + bid on first start (one-click judge demo)
    SEED_DEMO: bool = os.getenv("SEED_DEMO", "1") == "1"

    # Scraping configuration
    BIS_SCRAPE_DELAY_SECONDS: float = float(os.getenv("BIS_SCRAPE_DELAY_SECONDS", "2.0"))
    
    # Retrieval & Pipeline Parameters
    TOP_K_DENSE: int = int(os.getenv("TOP_K_DENSE", "50"))
    TOP_K_BM25: int = int(os.getenv("TOP_K_BM25", "50"))
    TOP_K_RERANK: int = int(os.getenv("TOP_K_RERANK", "10"))
    TOP_K_FINAL: int = int(os.getenv("TOP_K_FINAL", "5"))
    GRAPH_MAX_DEPTH: int = int(os.getenv("GRAPH_MAX_DEPTH", "2"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
