"""ChromaDB HTTP client — lazy singleton.

In Docker: CHROMA_HOST=chromadb, CHROMA_PORT=8000 (set via docker-compose env).
Local dev: defaults to localhost:8001 (mapped port from docker-compose).
"""

import chromadb
import structlog

from app.config import get_settings

logger = structlog.get_logger()

_client: chromadb.HttpClient | None = None


def get_chroma_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
        )
        logger.info("chromadb_connected", host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return _client
