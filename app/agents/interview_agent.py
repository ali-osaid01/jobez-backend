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
            {"id": "q1",  "question": f"Walk me through your most complex technical project relevant to {job_title}.", "type": "technical",   "category": "Experience",      "expectedDuration": 150},
            {"id": "q2",  "question": "Explain how you would design a scalable system for this role's core use case.",  "type": "technical",   "category": "System Design",   "expectedDuration": 180},
            {"id": "q3",  "question": "Describe a performance bottleneck you identified and how you resolved it.",       "type": "technical",   "category": "Optimization",    "expectedDuration": 150},
            {"id": "q4",  "question": "How do you ensure code quality and maintainability in a fast-moving team?",      "type": "technical",   "category": "Code Quality",    "expectedDuration": 120},
            {"id": "q5",  "question": "What is your approach to debugging an issue you have never seen before?",        "type": "technical",   "category": "Problem Solving", "expectedDuration": 120},
            {"id": "q6",  "question": "Describe a technical decision you made that you later regretted and why.",       "type": "technical",   "category": "Reflection",      "expectedDuration": 150},
            {"id": "q7",  "question": "Tell me about a time you had to push back on a product requirement.",            "type": "behavioral",  "category": "Communication",   "expectedDuration": 120},
            {"id": "q8",  "question": "Describe a situation where you had to learn something new under tight deadline.", "type": "behavioral",  "category": "Learning",        "expectedDuration": 120},
            {"id": "q9",  "question": f"You joined a {job_title} team and found the codebase in poor shape. What do you do first?", "type": "situational", "category": "Prioritization", "expectedDuration": 150},
            {"id": "q10", "question": "A critical bug hits production on a Friday evening. Walk me through your response.", "type": "situational", "category": "Incident Response", "expectedDuration": 150},
        ]

    async def evaluate_responses(self, job_title: str, questions: list[dict], responses: list[dict]) -> dict:
        prompt = build_evaluation_prompt(job_title, questions, responses)
        raw = await generate(prompt)
        try:
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
