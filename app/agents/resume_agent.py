"""Agent for parsing resumes using Gemini vision/OCR.

Sends the raw file bytes to Gemini which can read PDFs, DOCs, etc.
"""

import json

import structlog
from google.genai import types

from app.config import get_settings
from app.llm.client import get_gemini_client
from app.prompts.resume_parse import build_resume_parse_prompt

logger = structlog.get_logger()

MIME_MAP = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class ResumeAgent:
    async def parse_resume(self, file_bytes: bytes, file_ext: str) -> dict:
        """Parse resume using Gemini vision. Returns structured data dict."""
        settings = get_settings()
        client = get_gemini_client()

        if client is None:
            logger.warning("gemini_not_configured", msg="Returning stub data")
            return self._stub_response()

        mime_type = MIME_MAP.get(file_ext, "application/pdf")
        prompt = build_resume_parse_prompt()

        try:
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                            types.Part.from_text(text=prompt),
                        ],
                    )
                ],
            )

            raw = response.text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

            result = json.loads(raw)
            logger.info("resume_parsed_successfully", fields=list(result.keys()))
            return result

        except json.JSONDecodeError as e:
            logger.error("resume_parse_json_error", error=str(e), raw=raw[:300])
            return self._stub_response()
        except Exception as e:
            logger.error("resume_parse_failed", error=str(e))
            return self._stub_response()

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
