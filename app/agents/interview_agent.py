"""Agent for generating interview questions and evaluating responses."""

import json

import structlog

from app.llm.client import generate
from app.prompts.interview_evaluation import build_evaluation_prompt
from app.prompts.interview_question import build_question_prompt

logger = structlog.get_logger()


class InterviewAgent:
    async def generate_questions(
        self,
        candidate_profile: dict,
        job: dict,
        difficulty: str,
    ) -> list[dict]:
        """Generate 10 interview questions personalized to the candidate and job.

        Args:
            candidate_profile: dict with keys: title, experience, skills, bio, work_experience
            job: dict with keys: title, description, requirements
            difficulty: "medium" | "hard" | "extra hard"
        """
        prompt = build_question_prompt(candidate_profile, job, difficulty)
        raw = await generate(prompt)

        # Strip markdown code fences if Gemini wraps the JSON
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()

        try:
            questions = json.loads(stripped)
            if isinstance(questions, list) and questions:
                logger.info(
                    "questions_generated",
                    count=len(questions),
                    difficulty=difficulty,
                    job_title=job.get("title"),
                )
                return questions
        except Exception:
            logger.warning("question_generation_parse_failed", raw=raw[:300])

        return self._fallback_questions(job.get("title", "the position"), difficulty)

    def _fallback_questions(self, job_title: str, difficulty: str) -> list[dict]:
        """Safe fallback if Gemini is unavailable or returns unparseable output."""
        return [
            {"id": "q1", "question": f"Walk me through your most relevant technical project for a {job_title} role.", "type": "technical", "category": "Experience", "expectedDuration": 150},
            {"id": "q2", "question": "How would you approach the main technical challenge in this job, and why?", "type": "technical", "category": "System Design", "expectedDuration": 150},
            {"id": "q3", "question": "Describe a bug, bottleneck, or failure you solved in production and the trade-offs you made.", "type": "technical", "category": "Problem Solving", "expectedDuration": 150},
            {"id": "q4", "question": "Tell me about a time you had to influence a team decision or push back on a requirement.", "type": "behavioral", "category": "Communication", "expectedDuration": 120},
            {"id": "q5", "question": f"If you joined this {job_title} team and found the codebase or process messy, what would you do in your first week?", "type": "situational", "category": "Prioritization", "expectedDuration": 150},
        ]

    async def evaluate_responses(self, job_title: str, questions: list[dict], responses: list[dict]) -> dict:
        prompt = build_evaluation_prompt(job_title, questions, responses)
        raw = await generate(prompt)
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()
        try:
            return json.loads(stripped)
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
