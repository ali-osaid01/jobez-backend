from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    AuthUserResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _user_response(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        phone=user.phone,
        role=user.role,
        onboardingComplete=user.onboarding_complete,
    )


@router.post("/signup", status_code=201, response_model=SuccessResponse[AuthResponse])
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)):
    user, token, refresh_token = await auth_service.signup(db, payload)
    return SuccessResponse(
        data=AuthResponse(
            user=_user_response(user),
            token=token,
            refreshToken=refresh_token,
        )
    )


@router.post("/login", response_model=SuccessResponse[AuthResponse])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, token, refresh_token = await auth_service.login(db, payload.email, payload.password)
    return SuccessResponse(
        data=AuthResponse(
            user=_user_response(user),
            token=token,
            refreshToken=refresh_token,
        )
    )


@router.post("/refresh", response_model=SuccessResponse[RefreshResponse])
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    user, new_token = await auth_service.refresh(db, payload.refreshToken)
    return SuccessResponse(
        data=RefreshResponse(
            token=new_token,
            user=_user_response(user),
        )
    )


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.logout(db, user)
    return {"message": "Logged out"}
