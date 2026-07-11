import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.enums import UserRole
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.core.security import hash_password, verify_password
from app.models.profile import Profile
from app.models.user import User
from app.schemas.auth import GoogleLoginRequest, SignupRequest
from app.services.token_service import token_service


class AuthService:
    async def signup(self, db: AsyncSession, data: SignupRequest) -> tuple[User, str, str]:
        # Check for existing user
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictException("A user with this email already exists")

        # Create user
        user = User(
            id=uuid.uuid4(),
            email=data.email,
            name=data.name,
            phone=data.phone,
            hashed_password=hash_password(data.password),
            role=data.role,
            onboarding_complete=False,
        )
        db.add(user)
        await db.flush()

        # Create empty profile
        profile = Profile(
            id=uuid.uuid4(),
            user_id=user.id,
            name=data.name,
            email=data.email,
            phone=data.phone,
            role=data.role.value,
        )
        if data.role == UserRole.EMPLOYER:
            profile.company = data.name  # Default company name
        db.add(profile)

        # Generate tokens
        access_token, refresh_token = token_service.create_tokens(str(user.id), user.role.value)
        user.refresh_token_hash = token_service.hash_refresh_token(refresh_token)

        await db.flush()
        return user, access_token, refresh_token

    async def login(self, db: AsyncSession, email: str, password: str) -> tuple[User, str, str]:
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid credentials")
        if not user.is_active:
            raise UnauthorizedException("Account is deactivated")

        access_token, refresh_token = token_service.create_tokens(str(user.id), user.role.value)
        user.refresh_token_hash = token_service.hash_refresh_token(refresh_token)

        await db.flush()
        return user, access_token, refresh_token

    async def google_login(self, db: AsyncSession, data: GoogleLoginRequest) -> tuple[User, str, str]:
        google_profile = await self._verify_google_credential(data.credential)
        email = google_profile["email"]
        name = google_profile.get("name") or email.split("@", 1)[0]
        role = data.role or UserRole.JOB_SEEKER

        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            if not user.is_active:
                raise UnauthorizedException("Account is deactivated")
            if user.name != name:
                user.name = name
            profile_stmt = select(Profile).where(Profile.user_id == user.id)
            profile_result = await db.execute(profile_stmt)
            profile = profile_result.scalar_one_or_none()
            if profile:
                profile.name = name
            else:
                profile = Profile(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    name=name,
                    email=email,
                    phone=user.phone,
                    role=user.role.value,
                )
                if user.role == UserRole.EMPLOYER:
                    profile.company = name
                db.add(profile)
        else:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                phone="",
                hashed_password=hash_password(uuid.uuid4().hex),
                role=role,
                onboarding_complete=False,
            )
            db.add(user)
            await db.flush()

            profile = Profile(
                id=uuid.uuid4(),
                user_id=user.id,
                name=name,
                email=email,
                phone="",
                role=user.role.value,
            )
            if user.role == UserRole.EMPLOYER:
                profile.company = name
            db.add(profile)

        access_token, refresh_token = token_service.create_tokens(str(user.id), user.role.value)
        user.refresh_token_hash = token_service.hash_refresh_token(refresh_token)

        await db.flush()
        return user, access_token, refresh_token

    async def refresh(self, db: AsyncSession, refresh_token: str) -> tuple[User, str]:
        payload = token_service.verify_refresh(refresh_token)
        user_id = payload.get("sub")

        stmt = select(User).where(User.id == uuid.UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedException("Invalid refresh token")

        new_access_token = token_service.create_tokens(str(user.id), user.role.value)[0]
        return user, new_access_token

    async def logout(self, db: AsyncSession, user: User) -> None:
        user.refresh_token_hash = None
        await db.flush()

    async def _verify_google_credential(self, credential: str) -> dict:
        settings = get_settings()
        if not settings.GOOGLE_CLIENT_ID:
            raise UnauthorizedException("Google login is not configured")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": credential},
                )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UnauthorizedException("Invalid Google credential") from exc

        if payload.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise UnauthorizedException("Google credential audience mismatch")
        if str(payload.get("email_verified", "")).lower() != "true":
            raise UnauthorizedException("Google email is not verified")
        if not payload.get("email"):
            raise UnauthorizedException("Google account email missing")

        return payload


auth_service = AuthService()
