import io

import httpx

from app.config import get_settings
from app.core.exceptions import LLMException


class OpenAIVoiceServiceError(Exception):
    pass


class OpenAIVoiceService:
    base_url = "https://api.openai.com/v1"

    def _headers(self) -> dict[str, str]:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise LLMException("OPENAI_API_KEY is not configured")
        return {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    async def text_to_speech(self, text: str) -> bytes:
        settings = get_settings()
        payload = {
            "model": settings.OPENAI_TTS_MODEL,
            "input": text,
            "voice": settings.OPENAI_TTS_VOICE,
            "response_format": "mp3",
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/audio/speech",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json=payload,
                )
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as exc:
            raise LLMException(f"OpenAI text-to-speech failed: {exc}") from exc

    async def transcribe_audio(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> str:
        settings = get_settings()
        file_tuple = (filename, io.BytesIO(content), content_type or "audio/webm")

        data = {"model": settings.OPENAI_STT_MODEL}
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=self._headers(),
                    files={"file": file_tuple},
                    data=data,
                )
            response.raise_for_status()
            payload = response.json()
            text = payload.get("text", "")
            if not text:
                raise LLMException("OpenAI transcription returned empty text")
            return text
        except (httpx.HTTPError, ValueError) as exc:
            raise LLMException(f"OpenAI transcription failed: {exc}") from exc


openai_voice_service = OpenAIVoiceService()
