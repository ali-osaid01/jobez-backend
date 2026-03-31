def build_match_prompt(candidate_skills: list[str], candidate_bio: str, job: dict) -> str:
    return f"""You are a job matching AI. Score how well this candidate matches the job posting.

CANDIDATE:
- Skills: {', '.join(candidate_skills)}
- Bio: {candidate_bio}

JOB POSTING:
- Title: {job['title']}
- Description: {job['description']}
- Required Skills: {', '.join(job.get('requirements', []))}
- Location: {job['location']}

Return a JSON object with:
- "score": a float between 0 and 100 representing the match quality
- "reasoning": a brief explanation of the score (2-3 sentences)
"""
