"""Agent for scoring candidate-job fit.

Currently returns stub scores. Wire up LLM client for real scoring.
"""

import structlog

from app.llm.client import generate
from app.llm.schemas import MatchScoreResult
from app.prompts.job_match import build_match_prompt

logger = structlog.get_logger()


class JobMatchAgent:
    async def score(self, candidate_skills: list[str], candidate_bio: str, job: dict) -> float:
        prompt = build_match_prompt(candidate_skills, candidate_bio, job)
        raw = await generate(prompt)
        try:
            result = MatchScoreResult.model_validate_json(raw)
            logger.info("match_score_computed", job_id=job.get("id"), score=result.score)
            return result.score
        except Exception:
            logger.warning("match_score_parse_failed", raw=raw[:200])
            return 0.0

    async def batch_score(self, candidate_skills: list[str], candidate_bio: str, jobs: list[dict]) -> list[tuple[str, float]]:
        import asyncio

        tasks = [self.score(candidate_skills, candidate_bio, job) for job in jobs]
        scores = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for job, score in zip(jobs, scores):
            if isinstance(score, Exception):
                logger.error("match_score_failed", job_id=job.get("id"), error=str(score))
                results.append((job["id"], 0.0))
            else:
                results.append((job["id"], score))
        return results


job_match_agent = JobMatchAgent()
