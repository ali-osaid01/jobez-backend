"""Background tasks for AI scoring.

Stub implementation — replace with real agent calls when LLM is configured.
"""

import uuid

import structlog

logger = structlog.get_logger()


async def compute_match_scores(db_session_factory, user_id: uuid.UUID) -> None:
    """Compute AI match scores for a user against active jobs.

    Called as a FastAPI BackgroundTask after profile update or application.
    """
    logger.info("match_scoring_started", user_id=str(user_id))

    # Stub: In production, this would:
    # 1. Load user profile from DB
    # 2. Load active jobs
    # 3. Call job_match_agent.batch_score()
    # 4. Store scores in DB

    logger.info("match_scoring_completed", user_id=str(user_id), msg="stub — no real scoring")
