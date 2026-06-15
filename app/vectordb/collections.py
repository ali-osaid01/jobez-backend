"""Named collection accessors for ChromaDB.

Each collection is created on first access (get_or_create).
Import the getters — never construct Collection objects directly.
"""

import chromadb

from app.vectordb.client import get_chroma_client

# Collection name constants — reference these instead of raw strings.
JOBS_COLLECTION = "jobs"
RESUMES_COLLECTION = "resumes"


def get_jobs_collection() -> chromadb.Collection:
    """Job embeddings — used for semantic job search and candidate recommendations."""
    return get_chroma_client().get_or_create_collection(
        name=JOBS_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def get_resumes_collection() -> chromadb.Collection:
    """Resume/profile embeddings — used for candidate matching against job postings."""
    return get_chroma_client().get_or_create_collection(
        name=RESUMES_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
