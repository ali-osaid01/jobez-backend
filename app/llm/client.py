"""Gemini LLM client wrapper with retry logic.

Currently stubbed — returns placeholder responses.
Set GEMINI_API_KEY in .env to enable real AI calls.
"""

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings

logger = structlog.get_logger()

_client = None


def get_gemini_client():
    global _client
    if _client is None:
        settings = get_settings()
        if settings.GEMINI_API_KEY:
            from google import genai
            _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            logger.warning("gemini_not_configured", msg="GEMINI_API_KEY not set, using stubs")
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: logger.warning(
        "llm_retry", attempt=retry_state.attempt_number
    ),
)
async def generate(prompt: str, *, model: str | None = None) -> str:
    """Generate text from Gemini. Falls back to stub if not configured."""
    client = get_gemini_client()
    if client is None:
        logger.info("llm_stub_response", prompt_length=len(prompt))
        return '{"score": 75, "reasoning": "Stub response — configure GEMINI_API_KEY for real AI."}'

    settings = get_settings()
    response = await client.aio.models.generate_content(
        model=model or settings.GEMINI_MODEL,
        contents=prompt,
    )
    return response.text
