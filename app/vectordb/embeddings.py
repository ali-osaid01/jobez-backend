"""Embedding utilities for semantic job recommendation.

- embed_text: calls OpenAI embeddings, returns list[float]
- build_job_text: builds embeddable text document from a Job
- build_profile_text: builds embeddable text document from a Profile
"""

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


async def embed_text(text: str) -> list[float]:
    """Embed text via OpenAI. Returns [] if OpenAI is not configured or unavailable."""
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        logger.warning("embed_text_skipped", reason="OPENAI_API_KEY not set")
        return []

    payload = {
        "model": settings.OPENAI_EMBEDDING_MODEL,
        "input": text,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        response.raise_for_status()
        data = response.json().get("data", [])
        if not data:
            return []
        return data[0].get("embedding", []) or []
    except Exception as exc:
        logger.error("openai_embedding_failed", error=str(exc))
        return []


def build_job_text(job) -> str:
    """Build a rich text document from a Job for embedding."""
    exp_level = job.experience_level.value if hasattr(job.experience_level, "value") else job.experience_level
    loc_type = job.location_type.value if hasattr(job.location_type, "value") else job.location_type
    requirements = ", ".join(job.requirements or [])

    parts = [
        job.title,
        exp_level,
        loc_type,
        job.description,
        f"requirements: {requirements}" if requirements else None,
    ]
    return " | ".join(p for p in parts if p)


def build_profile_text(profile) -> str:
    """Build a rich text document from a Profile for embedding."""
    skills = ", ".join(profile.skills or [])
    work_exp = " ".join(
        f"{w.get('title', '')} at {w.get('company', '')}".strip(" at")
        for w in (profile.work_experience or [])
        if w.get("title") or w.get("company")
    )

    parts = [
        profile.title,
        profile.experience,
        profile.preferred_role,
        profile.bio,
        f"skills: {skills}" if skills else None,
        work_exp if work_exp.strip() else None,
    ]
    return " | ".join(p for p in parts if p)
