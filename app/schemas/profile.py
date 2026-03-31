from pydantic import BaseModel

from app.core.enums import UserRole


class EducationItem(BaseModel):
    degree: str
    institution: str
    year: str


class WorkExperienceItem(BaseModel):
    title: str
    company: str
    duration: str


class ProfileResponse(BaseModel):
    id: str
    userId: str
    name: str
    email: str
    phone: str
    role: UserRole
    onboardingComplete: bool

    # Job seeker
    title: str | None = None
    location: str | None = None
    experience: str | None = None
    preferredRole: str | None = None
    expectedSalary: str | None = None
    skills: list[str] | None = None
    education: list[EducationItem] | None = None
    workExperience: list[WorkExperienceItem] | None = None
    certifications: list[str] | None = None
    resumeUrl: str | None = None
    bio: str | None = None

    # Employer
    company: str | None = None
    companySize: str | None = None
    industry: str | None = None
    website: str | None = None
    description: str | None = None
    founded: str | None = None

    createdAt: str
    updatedAt: str

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    # Job seeker fields
    title: str | None = None
    location: str | None = None
    experience: str | None = None
    preferredRole: str | None = None
    expectedSalary: str | None = None
    skills: list[str] | None = None
    education: list[EducationItem] | None = None
    workExperience: list[WorkExperienceItem] | None = None
    certifications: list[str] | None = None
    resumeUrl: str | None = None
    bio: str | None = None

    # Employer fields
    company: str | None = None
    companySize: str | None = None
    industry: str | None = None
    website: str | None = None
    description: str | None = None
    founded: str | None = None

    # Onboarding
    onboardingComplete: bool | None = None


class ResumeExtractResponse(BaseModel):
    title: str | None = None
    experience: str | None = None
    preferredRole: str | None = None
    location: str | None = None
    expectedSalary: str | None = None
    skills: list[str] | None = None
    bio: str | None = None
    education: list[EducationItem] | None = None
    workExperience: list[WorkExperienceItem] | None = None
    certifications: list[str] | None = None
    resumeUrl: str | None = None
