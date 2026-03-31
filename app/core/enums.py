from enum import Enum


class UserRole(str, Enum):
    JOB_SEEKER = "job-seeker"
    EMPLOYER = "employer"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview-scheduled"
    REJECTED = "rejected"
    HIRED = "hired"


class InterviewStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InterviewType(str, Enum):
    AI = "ai"
    HUMAN = "human"


class JobType(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"


class LocationType(str, Enum):
    REMOTE = "Remote"
    ON_SITE = "On-site"
    HYBRID = "Hybrid"


class ExperienceLevel(str, Enum):
    ENTRY = "Entry"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"


class JobStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
