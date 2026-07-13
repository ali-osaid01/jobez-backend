"""Agent for generating interview questions and evaluating responses."""

import json
import re

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

        # Strip markdown code fences if the model wraps the JSON.
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
        """Safe fallback if OpenAI is unavailable or returns unparseable output."""
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
            parsed = json.loads(stripped)
            if isinstance(parsed, dict) and parsed.get("overallScore") is not None:
                return parsed
        except Exception:
            logger.warning("evaluation_failed", raw=raw[:200])

        return self._fallback_evaluation(job_title, questions, responses)

    def _fallback_evaluation(self, job_title: str, questions: list[dict], responses: list[dict]) -> dict:
        answered = [item for item in responses if str(item.get("response", "")).strip()]
        response_text = " ".join(str(item.get("response", "")) for item in answered)
        word_count = len(re.findall(r"\w+", response_text))
        response_count = len(answered)
        coverage = 0 if not questions else min(100, round((response_count / max(1, len(questions))) * 100))
        depth = min(100, 20 + (word_count * 2))
        overall = round((coverage * 0.5) + (depth * 0.5), 2)

        strengths = [
            "Answered the interview questions directly",
            "Provided evidence of engagement with the role",
        ]
        improvements = [
            "Add more detail and concrete examples",
            "Tie answers more closely to the job requirements",
        ]

        if response_count == 0:
            summary = f"No usable responses were captured for the {job_title} interview."
        else:
            summary = (
                f"The candidate answered {response_count} question(s) for the {job_title} role. "
                f"The responses show partial coverage, but the answer depth can be improved with more specific examples."
            )

        technical = min(100, round(overall))
        communication = min(100, round(30 + word_count * 1.2))
        problem_solving = min(100, round(25 + word_count * 1.1))
        culture_fit = min(100, round(40 + response_count * 8))

        return {
            "overallScore": overall,
            "technicalScore": technical,
            "communicationScore": communication,
            "problemSolvingScore": problem_solving,
            "cultureFitScore": culture_fit,
            "strengths": strengths,
            "improvements": improvements,
            "summary": summary,
        }


interview_agent = InterviewAgent()
