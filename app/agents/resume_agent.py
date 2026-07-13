"""Agent for parsing PDF resumes using OpenAI."""

import base64
import json

import httpx
import structlog

from app.config import get_settings
from app.llm.client import _extract_response_text
from app.prompts.resume_parse import build_resume_parse_prompt

logger = structlog.get_logger()


class ResumeAgent:
    async def parse_resume(self, file_bytes: bytes, file_ext: str) -> dict:
        """Parse a PDF resume with OpenAI and return structured profile fields."""
        if file_ext.lower() != "pdf":
            logger.warning("resume_parse_rejected_non_pdf", file_ext=file_ext)
            return self._stub_response()

        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            logger.warning("openai_not_configured", msg="Returning stub resume data")
            return self._stub_response()

        prompt = build_resume_parse_prompt()
        encoded_pdf = base64.b64encode(file_bytes).decode("ascii")
        payload = {
            "model": settings.OPENAI_RESUME_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "filename": "resume.pdf",
                            "file_data": f"data:application/pdf;base64,{encoded_pdf}",
                        },
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            response.raise_for_status()
            raw = _extract_response_text(response.json())
            result = json.loads(self._strip_json_markdown(raw))
            logger.info("resume_parsed_successfully", fields=list(result.keys()))
            return result

        except json.JSONDecodeError as exc:
            logger.error("resume_parse_json_error", error=str(exc))
            return self._stub_response()
        except Exception as exc:
            logger.error("resume_parse_failed", error=str(exc))
            return self._stub_response()

    def _strip_json_markdown(self, raw: str) -> str:
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped[3:]
            if stripped.endswith("```"):
                stripped = stripped[:-3]
            stripped = stripped.strip()
        return stripped

    def _stub_response(self) -> dict:
        return {
            "title": None,
            "experience": None,
            "preferredRole": None,
            "location": None,
            "expectedSalary": None,
            "skills": [],
            "bio": None,
            "education": [],
            "workExperience": [],
            "certifications": [],
        }


resume_agent = ResumeAgent()
