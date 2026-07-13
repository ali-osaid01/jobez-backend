"""OpenAI LLM client wrapper with retry logic."""

import json

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger()

OPENAI_BASE_URL = "https://api.openai.com/v1"


def _headers() -> dict[str, str] | None:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        logger.warning("openai_not_configured", msg="OPENAI_API_KEY not set, using stubs")
        return None
    return {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }


def _extract_response_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    output_parts: list[str] = []
    for output in payload.get("output", []) or []:
        for content in output.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str):
                output_parts.append(text)
    return "\n".join(output_parts).strip()


def _stub_response(prompt: str) -> str:
    logger.info("llm_stub_response", prompt_length=len(prompt))
    if "interview evaluator" in prompt.lower():
        return json.dumps(
            {
                "overallScore": 75,
                "technicalScore": 75,
                "communicationScore": 75,
                "problemSolvingScore": 75,
                "cultureFitScore": 75,
                "strengths": ["Answered the questions directly"],
                "improvements": ["Add more concrete examples"],
                "summary": "Stub response — configure OPENAI_API_KEY for real AI evaluation.",
            }
        )
    return '{"score": 75, "reasoning": "Stub response — configure OPENAI_API_KEY for real AI."}'


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(
        "llm_retry", attempt=retry_state.attempt_number
    ),
)
async def generate(prompt: str, *, model: str | None = None) -> str:
    """Generate text from OpenAI. Falls back to a stub if OpenAI is not configured."""
    headers = _headers()
    if headers is None:
        return _stub_response(prompt)

    settings = get_settings()
    payload = {
        "model": model or settings.OPENAI_TEXT_MODEL,
        "input": prompt,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OPENAI_BASE_URL}/responses",
            headers=headers,
            json=payload,
        )
    response.raise_for_status()
    text = _extract_response_text(response.json())
    if not text:
        raise RuntimeError("OpenAI returned an empty response")
    return text
