from pydantic import BaseModel

from app.core.enums import UserRole


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    phone: str
    role: UserRole
    onboardingComplete: bool
    createdAt: str
    updatedAt: str

    model_config = {"from_attributes": True}
