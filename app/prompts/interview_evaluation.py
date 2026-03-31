def build_evaluation_prompt(job_title: str, questions: list[dict], responses: list[dict]) -> str:
    q_and_a = ""
    for q, r in zip(questions, responses):
        q_and_a += f"\nQ: {q['question']}\nA: {r['response']}\nDuration: {r['duration']}s\n"

    return f"""You are an AI interview evaluator. Evaluate the candidate's responses for the {job_title} position.

INTERVIEW TRANSCRIPT:
{q_and_a}

Evaluate and return a JSON object with:
- "overallScore": 0-100
- "technicalScore": 0-100
- "communicationScore": 0-100
- "problemSolvingScore": 0-100
- "cultureFitScore": 0-100
- "strengths": array of 3-5 strength points
- "improvements": array of 2-3 areas for improvement
- "summary": a 2-3 sentence overall assessment
"""
