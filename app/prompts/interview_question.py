_DIFFICULTY_DESCRIPTIONS = {
    "medium": (
        "MEDIUM difficulty — questions should test solid understanding of core concepts, "
        "common patterns, and practical application. Avoid trivial questions but do not assume "
        "deep architectural expertise."
    ),
    "hard": (
        "HARD difficulty — questions should probe deep understanding, edge cases, performance "
        "trade-offs, and real-world problem solving. Expect the candidate to justify design "
        "decisions and handle follow-up scenarios."
    ),
    "extra hard": (
        "EXTRA HARD difficulty — questions should be at senior/expert level. Expect system design "
        "trade-offs, distributed systems concerns, subtle bugs, scalability bottlenecks, and "
        "questions that expose the boundary between good and exceptional engineers. Do not ask "
        "anything a mid-level engineer could answer confidently."
    ),
}


def build_question_prompt(candidate_profile: dict, job: dict, difficulty: str) -> str:
    skills = ", ".join(candidate_profile.get("skills") or []) or "not specified"
    work_exp = "; ".join(
        f"{w.get('title', '')} at {w.get('company', '')} ({w.get('duration', '')})"
        for w in (candidate_profile.get("work_experience") or [])
        if w.get("title") or w.get("company")
    ) or "not specified"
    requirements = ", ".join(job.get("requirements") or []) or "not specified"
    responsibilities = ", ".join(job.get("responsibilities") or []) or "not specified"
    difficulty_desc = _DIFFICULTY_DESCRIPTIONS.get(difficulty, _DIFFICULTY_DESCRIPTIONS["medium"])

    certifications = ", ".join(candidate_profile.get("certifications") or []) or "not specified"
    education = "; ".join(
        f"{e.get('degree', '')} from {e.get('institution', '')} ({e.get('year', '')})"
        for e in (candidate_profile.get("education") or [])
        if e.get("degree") or e.get("institution")
    ) or "not specified"

    return f"""You are a senior technical interviewer conducting an AI interview. Generate exactly 5 interview questions.

DIFFICULTY LEVEL: {difficulty.upper()}
{difficulty_desc}

CANDIDATE PROFILE:
- Current title: {candidate_profile.get("title") or "not specified"}
- Years of experience: {candidate_profile.get("experience") or "not specified"}
- Skills: {skills}
- Certifications: {certifications}
- Education: {education}
- Bio: {candidate_profile.get("bio") or "not specified"}
- Work history: {work_exp}

JOB THEY APPLIED FOR:
- Title: {job.get("title") or "not specified"}
- Seniority: {job.get("experienceLevel") or "not specified"}
- Description: {job.get("description") or "not specified"}
- Requirements: {requirements}
- Responsibilities: {responsibilities}

INSTRUCTIONS:
- Generate exactly 5 questions in this mix: 3 role-specific/domain questions, 1 behavioral, 1 situational
- Role-specific/domain questions must directly relate to the job title, requirements, responsibilities, and overlapping candidate skills
- Behavioral questions should reference realistic scenarios from their work history
- Situational questions should be grounded in the specific job context
- All questions must match the {difficulty.upper()} difficulty level described above
- Do NOT ask about tools, frameworks, programming concepts, or technologies unless they appear in the job description, requirements, responsibilities, or candidate profile
- For non-software jobs, ask domain-specific questions for that job, not software engineering questions
- Do NOT ask generic or beginner questions
- Questions should feel specific to this candidate, not copy-paste generic interview prep

Return ONLY a valid JSON array. No markdown, no explanation. Each item must have:
- "id": string (q1, q2, ... q5)
- "question": the full question text
- "type": one of "technical", "behavioral", "situational"
- "category": short label (e.g. "System Design", "Problem Solving", "Teamwork")
- "expectedDuration": integer seconds the candidate should take to answer (90-180)
"""
