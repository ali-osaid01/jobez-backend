import asyncio
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileUpdateRequest
from app.vectordb.collections import get_resumes_collection
from app.vectordb.embeddings import build_profile_text, embed_text

logger = structlog.get_logger()


async def _index_profile(user_id: str, text: str) -> None:
    """Embed a user profile and upsert into ChromaDB. Runs as a background task."""
    try:
        vec = await embed_text(text)
        if not vec:
            return
        get_resumes_collection().upsert(ids=[user_id], embeddings=[vec], documents=[text])
        logger.info("profile_indexed", user_id=user_id)
    except Exception as exc:
        logger.error("profile_index_failed", user_id=user_id, error=str(exc))


class ProfileService:
    async def get_by_user_id(self, db: AsyncSession, user_id: uuid.UUID) -> Profile:
        stmt = select(Profile).where(Profile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundException("Profile")
        return profile

    async def update(
        self, db: AsyncSession, user: User, data: ProfileUpdateRequest
    ) -> Profile:
        profile = await self.get_by_user_id(db, user.id)

        update_data = data.model_dump(exclude_unset=True)

        # Map camelCase request fields to snake_case DB columns
        field_mapping = {
            "companySize": "company_size",
            "preferredRole": "preferred_role",
            "expectedSalary": "expected_salary",
            "workExperience": "work_experience",
            "resumeUrl": "resume",
        }

        for key, value in update_data.items():
            if key == "onboardingComplete":
                continue  # handled below on user model
            db_field = field_mapping.get(key, key)
            if hasattr(profile, db_field):
                setattr(profile, db_field, value)

        # Update user's onboarding_complete flag
        if data.onboardingComplete is not None:
            user.onboarding_complete = data.onboardingComplete

        await db.flush()
        await db.refresh(profile)

        # Trigger embedding when onboarding completes
        if data.onboardingComplete is True:
            asyncio.create_task(_index_profile(str(user.id), build_profile_text(profile)))

        return profile

    async def update_resume(self, db: AsyncSession, user_id: uuid.UUID, url: str, public_id: str) -> Profile:
        profile = await self.get_by_user_id(db, user_id)
        profile.resume = url
        profile.resume_public_id = public_id
        await db.flush()
        await db.refresh(profile)
        return profile


profile_service = ProfileService()
