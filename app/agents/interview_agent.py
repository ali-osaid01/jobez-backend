"""Agent for generating interview questions and evaluating responses.

Currently returns stub data. Wire up LLM client for real AI interviews.
"""

import structlog

from app.llm.client import generate
from app.prompts.interview_evaluation import build_evaluation_prompt
from app.prompts.interview_question import build_question_prompt

logger = structlog.get_logger()


class InterviewAgent:
    async def generate_questions(self, job_title: str, job_description: str, required_skills: list[str]) -> list[dict]:
        prompt = build_question_prompt(job_title, job_description, required_skills)
        raw = await generate(prompt)
        try:
            import json
            questions = json.loads(raw)
            return questions if isinstance(questions, list) else []
        except Exception:
            logger.warning("question_generation_failed", raw=raw[:200])
            return []

    async def evaluate_responses(self, job_title: str, questions: list[dict], responses: list[dict]) -> dict:
        prompt = build_evaluation_prompt(job_title, questions, responses)
        raw = await generate(prompt)
        try:
            import json
            return json.loads(raw)
        except Exception:
            logger.warning("evaluation_failed", raw=raw[:200])
            return {
                "overallScore": 0,
                "technicalScore": 0,
                "communicationScore": 0,
                "problemSolvingScore": 0,
                "cultureFitScore": 0,
                "strengths": [],
                "improvements": [],
                "summary": "Evaluation failed",
            }


interview_agent = InterviewAgent()
