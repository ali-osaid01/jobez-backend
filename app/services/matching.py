"""Candidate/job match scoring and explanation helpers."""

import re
from dataclasses import dataclass
from math import sqrt
from typing import Any

from app.models.job import Job
from app.models.profile import Profile
from app.vectordb.embeddings import build_job_text, build_profile_text, embed_text

MIN_APPLY_MATCH_SCORE = 65.0
AUTO_INTERVIEW_MATCH_SCORE = 75.0


@dataclass(frozen=True)
class MatchResult:
    score: float
    reasons: list[str]
    role_overlap: list[str]
    skill_matches: list[str]

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "be",
    "for",
    "in",
    "is",
    "job",
    "of",
    "on",
    "or",
    "role",
    "the",
    "to",
    "with",
}


def _words(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        word
        for word in re.findall(r"[a-z0-9]+", value.lower().replace("-", " "))
        if len(word) > 2 and word not in _STOPWORDS
    }


def _cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if not left or not right or len(left) != len(right):
        return None
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return None
    return numerator / (left_norm * right_norm)


def _join_json_strings(items: list[Any] | None, *keys: str) -> str:
    values: list[str] = []
    for item in items or []:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict):
            values.extend(str(item.get(key) or "") for key in keys)
    return " ".join(values)


def _job_text(job: Job) -> str:
    return " ".join(
        part
        for part in [
            job.title,
            job.description,
            _join_json_strings(job.requirements),
            _join_json_strings(job.responsibilities),
            _join_json_strings(job.benefits),
        ]
        if part
    ).lower()


def _profile_role_text(profile: Profile) -> str:
    return " ".join(
        part
        for part in [
            profile.title,
            profile.preferred_role,
            _join_json_strings(profile.work_experience, "title"),
        ]
        if part
    )


def _profile_skills(profile: Profile) -> list[str]:
    return [
        item.strip().lower()
        for item in [*(profile.skills or []), *(profile.certifications or [])]
        if isinstance(item, str) and item.strip()
    ]


def _matched_skills(profile: Profile, job_text: str, job_words: set[str]) -> list[str]:
    matches: list[str] = []
    for skill in _profile_skills(profile):
        skill_words = _words(skill)
        if not skill_words:
            continue
        if skill in job_text or skill_words.issubset(job_words):
            matches.append(skill)
    return matches


def _heuristic_score(profile: Profile | None, job: Job) -> float:
    if not profile:
        return 0.0

    job_text = _job_text(job)
    job_words = _words(job_text)
    if not job_words:
        return 0.0

    profile_text = build_profile_text(profile)
    profile_words = _words(profile_text)
    role_overlap = _words(_profile_role_text(profile)) & job_words
    matched_skills = _matched_skills(profile, job_text, job_words)
    shared_words = profile_words & job_words

    role_points = min(25.0, len(role_overlap) * 8.0)
    skill_points = min(45.0, len(matched_skills) * 15.0)
    lexical_points = min(30.0, (len(shared_words) / max(1, len(job_words))) * 150.0)
    return round(min(100.0, role_points + skill_points + lexical_points), 2)


def explain_candidate_job_match(
    profile: Profile | None,
    job: Job,
    *,
    embedding_score: float | None = None,
) -> MatchResult:
    if not profile:
        return MatchResult(
            score=0.0,
            reasons=["Complete your candidate profile to calculate job relevance."],
            role_overlap=[],
            skill_matches=[],
        )

    job_text = _job_text(job)
    job_words = _words(job_text)
    role_overlap = sorted(_words(_profile_role_text(profile)) & job_words)
    skill_matches = _matched_skills(profile, job_text, job_words)
    heuristic_score = _heuristic_score(profile, job)

    if embedding_score is None:
        score = heuristic_score
    else:
        # Use semantic similarity as the base but keep lexical/domain overlap involved,
        # so broad resumes cannot pass solely because embeddings are loosely related.
        score = round((embedding_score * 0.65) + (heuristic_score * 0.35), 2)

    if not role_overlap and len(skill_matches) < 2:
        score = min(score, 59.0)

    reasons: list[str] = []
    if role_overlap:
        reasons.append(f"Role keywords overlap: {', '.join(role_overlap[:4])}.")
    if skill_matches:
        reasons.append(f"Matched skills/certifications: {', '.join(skill_matches[:5])}.")
    if embedding_score is not None:
        reasons.append(f"Profile and job description semantic similarity is {round(embedding_score, 2)}%.")
    if not reasons:
        reasons.append("Low role and skills overlap with your current profile.")

    return MatchResult(
        score=round(max(0.0, min(100.0, score)), 2),
        reasons=reasons[:4],
        role_overlap=role_overlap,
        skill_matches=skill_matches,
    )


async def score_candidate_job_match(profile: Profile | None, job: Job) -> MatchResult:
    if not profile:
        return explain_candidate_job_match(None, job)

    embedding_score: float | None = None
    try:
        profile_vec, job_vec = await embed_text(build_profile_text(profile)), await embed_text(build_job_text(job))
        similarity = _cosine_similarity(profile_vec, job_vec)
        if similarity is not None:
            embedding_score = round(max(0.0, similarity) * 100.0, 2)
    except Exception:
        embedding_score = None

    return explain_candidate_job_match(profile, job, embedding_score=embedding_score)


def candidate_job_gate(profile: Profile | None, job: Job) -> bool:
    """Return true when the candidate has meaningful role or skill overlap with the job."""
    if not profile:
        return False

    job_text = _job_text(job)
    job_words = _words(job_text)
    if not job_words:
        return False

    role_overlap = _words(_profile_role_text(profile)) & job_words
    if role_overlap:
        return True

    return len(_matched_skills(profile, job_text, job_words)) >= 2
