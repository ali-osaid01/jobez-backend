"""Structured output schemas for LLM responses."""

from pydantic import BaseModel


class MatchScoreResult(BaseModel):
    score: float
    reasoning: str


class InterviewQuestionSet(BaseModel):
    questions: list[dict]


class InterviewEvaluation(BaseModel):
    overallScore: float
    technicalScore: float
    communicationScore: float
    problemSolvingScore: float
    cultureFitScore: float
    strengths: list[str]
    improvements: list[str]
    summary: str


class ResumeSummary(BaseModel):
    skills: list[str]
    experience_years: int
    summary: str
