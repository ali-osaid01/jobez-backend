"""Embedding utilities for semantic job recommendation.

- embed_text: calls Gemini text-embedding-004, returns list[float]
- build_job_text: builds embeddable text document from a Job
- build_profile_text: builds embeddable text document from a Profile
"""

import structlog

from app.llm.client import get_gemini_client

logger = structlog.get_logger()


async def embed_text(text: str) -> list[float]:
    """Embed text via Gemini text-embedding-004. Returns [] if Gemini is not configured."""
    client = get_gemini_client()
    if client is None:
        logger.warning("embed_text_skipped", reason="GEMINI_API_KEY not set")
        return []
    result = await client.aio.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )
    return result.embeddings[0].values


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
