from pydantic import BaseModel, EmailStr, Field

from app.core.enums import UserRole


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    phone: str = Field(min_length=10)
    role: UserRole
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    credential: str
    role: UserRole | None = None


class RefreshRequest(BaseModel):
    refreshToken: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    newPassword: str = Field(min_length=6)


class AuthUserResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: str
    role: UserRole
    onboardingComplete: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: AuthUserResponse
    token: str
    refreshToken: str


class RefreshResponse(BaseModel):
    token: str
    user: AuthUserResponse
