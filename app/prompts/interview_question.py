def build_question_prompt(job_title: str, job_description: str, required_skills: list[str]) -> str:
    return f"""You are an AI interviewer. Generate 5 interview questions for the following position.

POSITION: {job_title}
DESCRIPTION: {job_description}
REQUIRED SKILLS: {', '.join(required_skills)}

Generate a mix of:
- 2 behavioral questions
- 2 technical questions
- 1 situational question

Return a JSON array where each item has:
- "id": a unique identifier (q1, q2, etc.)
- "question": the question text
- "type": "behavioral", "technical", or "situational"
- "category": a short category label
- "expectedDuration": expected answer duration in seconds (60-180)
"""
