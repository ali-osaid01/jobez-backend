"""Candidate/job match gating helpers."""

import re
from typing import Any

from app.models.job import Job
from app.models.profile import Profile

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

    skill_matches = 0
    for skill in _profile_skills(profile):
        skill_words = _words(skill)
        if not skill_words:
            continue
        if skill in job_text or skill_words.issubset(job_words):
            skill_matches += 1

    return skill_matches >= 2
