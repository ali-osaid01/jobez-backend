import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.interview_agent import interview_agent
from app.core.enums import ApplicationStatus, InterviewStatus, InterviewType
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job
from app.models.profile import Profile
from app.models.user import User
from app.schemas.interview import HumanInterviewCompleteRequest, InterviewCreate, InterviewResponsesRequest, InterviewUpdate
from app.services.notification_service import notification_service

# Maps profile.experience → the difficulty level of questions to generate
_EXPERIENCE_TO_DIFFICULTY: dict[str | None, str] = {
    "0-1":  "medium",
    "1-3":  "hard",
    "3-5":  "hard",
    "5-10": "extra hard",
    "10+":  "extra hard",
}


class InterviewService:
    async def create(self, db: AsyncSession, employer: User, data: InterviewCreate) -> Interview:
        job_id = uuid.UUID(data.jobId)
        applicant_id = uuid.UUID(data.applicantId)

        # Verify employer owns the job + get company from profile
        stmt = (
            select(Job, Profile.company)
            .join(Profile, Profile.user_id == Job.employer_id)
            .where(Job.id == job_id, Job.employer_id == employer.id)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if not row:
            raise NotFoundException("Job")
        job, company = row

        # Get the application
        stmt = select(Application).where(Application.job_id == job_id, Application.applicant_id == applicant_id)
        result = await db.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            raise NotFoundException("Application")

        interview = Interview(
            id=uuid.uuid4(),
            job_id=job_id,
            application_id=application.id,
            applicant_id=applicant_id,
            job_title=job.title,
            company=company or "",
            applicant_name=application.applicant_name,
            scheduled_date=data.scheduledDate,
            scheduled_time=data.scheduledTime,
            duration=data.duration,
            status=InterviewStatus.SCHEDULED,
            type=data.type,
            meeting_link=data.meetingLink,
            notes=data.notes,
        )
        db.add(interview)

        # Update application status
        application.status = ApplicationStatus.INTERVIEW_SCHEDULED
        await notification_service.create(
            db,
            recipient_id=application.applicant_id,
            title="Interview scheduled",
            message=f"{company or 'The employer'} scheduled a {data.type.value} interview for {job.title}.",
            type="interview",
            data={
                "applicationId": str(application.id),
                "interviewId": str(interview.id),
                "jobId": str(job.id),
                "jobTitle": job.title,
                "status": ApplicationStatus.INTERVIEW_SCHEDULED.value,
            },
        )
        await notification_service.create(
            db,
            recipient_id=employer.id,
            title="Interview scheduled",
            message=f"You scheduled a {data.type.value} interview with {application.applicant_name} for {job.title}.",
            type="interview",
            data={
                "applicationId": str(application.id),
                "interviewId": str(interview.id),
                "jobId": str(job.id),
                "jobTitle": job.title,
                "applicantId": str(application.applicant_id),
                "status": ApplicationStatus.INTERVIEW_SCHEDULED.value,
            },
        )

        await db.flush()
        return interview

    async def get_by_id(self, db: AsyncSession, interview_id: uuid.UUID) -> Interview:
        stmt = select(Interview).where(Interview.id == interview_id)
        result = await db.execute(stmt)
        interview = result.scalar_one_or_none()
        if not interview:
            raise NotFoundException("Interview")
        return interview

    async def list_interviews(
        self,
        db: AsyncSession,
        user: User,
        *,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        interview_type: str | None = None,
    ) -> tuple[list[Interview], int]:
        stmt = select(Interview)

        if user.role.value == "job-seeker":
            stmt = stmt.where(Interview.applicant_id == user.id)
        else:
            stmt = stmt.join(Job).where(Job.employer_id == user.id)

        if status:
            stmt = stmt.where(Interview.status == InterviewStatus(status))
        if interview_type:
            stmt = stmt.where(Interview.type == interview_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Interview.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_status_counts(self, db: AsyncSession, user: User, *, interview_type: str | None = None) -> dict:
        stmt = select(Interview.status, func.count().label("cnt"))

        if user.role.value == "job-seeker":
            stmt = stmt.where(Interview.applicant_id == user.id)
        else:
            stmt = stmt.join(Job).where(Job.employer_id == user.id)

        if interview_type:
            stmt = stmt.where(Interview.type == interview_type)

        stmt = stmt.group_by(Interview.status)
        result = await db.execute(stmt)
        rows = result.all()
        counts = {row.status: row.cnt for row in rows}
        total = sum(counts.values())
        return {
            "total": total,
            "scheduled": counts.get(InterviewStatus.SCHEDULED, 0),
            "inProgress": counts.get(InterviewStatus.IN_PROGRESS, 0),
            "completed": counts.get(InterviewStatus.COMPLETED, 0),
            "cancelled": counts.get(InterviewStatus.CANCELLED, 0),
        }

    async def update(
        self, db: AsyncSession, interview_id: uuid.UUID, employer_id: uuid.UUID, data: InterviewUpdate
    ) -> Interview:
        interview = await self.get_by_id(db, interview_id)

        # Verify ownership through job
        stmt = select(Job).where(Job.id == interview.job_id, Job.employer_id == employer_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise ForbiddenException("You can only update your own interviews")

        update_data = data.model_dump(exclude_unset=True)
        field_mapping = {
            "scheduledDate": "scheduled_date",
            "scheduledTime": "scheduled_time",
            "meetingLink": "meeting_link",
        }
        for key, value in update_data.items():
            db_field = field_mapping.get(key, key)
            if hasattr(interview, db_field):
                setattr(interview, db_field, value)

        await db.flush()
        return interview

    async def start_ai_interview(self, db: AsyncSession, interview_id: uuid.UUID, user_id: uuid.UUID) -> Interview:
        interview = await self.get_by_id(db, interview_id)
        if interview.applicant_id != user_id:
            raise ForbiddenException("You can only start your own interviews")

        if InterviewStatus(interview.status) == InterviewStatus.COMPLETED:
            return interview

        # Idempotent — if questions already generated, just resume
        if interview.questions:
            interview.status = InterviewStatus.IN_PROGRESS
            await db.flush()
            return interview

        # Fetch candidate profile for personalization
        profile_stmt = select(Profile).where(Profile.user_id == user_id)
        profile = (await db.execute(profile_stmt)).scalar_one_or_none()

        # Fetch the job for context
        job_stmt = select(Job).where(Job.id == interview.job_id)
        job = (await db.execute(job_stmt)).scalar_one_or_none()

        # Derive question difficulty from candidate's experience level
        experience = profile.experience if profile else None
        difficulty = _EXPERIENCE_TO_DIFFICULTY.get(experience, "medium")

        candidate_profile = {
            "title": profile.title if profile else None,
            "experience": experience,
            "skills": profile.skills if profile else [],
            "certifications": profile.certifications if profile else [],
            "education": profile.education if profile else [],
            "bio": profile.bio if profile else None,
            "work_experience": profile.work_experience if profile else [],
        }
        job_dict = {
            "title": job.title if job else interview.job_title,
            "description": job.description if job else "",
            "requirements": job.requirements if job else [],
            "responsibilities": job.responsibilities if job else [],
            "experienceLevel": job.experience_level.value if job and hasattr(job.experience_level, "value") else job.experience_level if job else None,
        }

        interview.questions = await interview_agent.generate_questions(
            candidate_profile=candidate_profile,
            job=job_dict,
            difficulty=difficulty,
        )
        interview.status = InterviewStatus.IN_PROGRESS

        await db.flush()
        return interview

    async def submit_responses(
        self, db: AsyncSession, interview_id: uuid.UUID, user_id: uuid.UUID, data: InterviewResponsesRequest
    ) -> None:
        interview = await self.get_by_id(db, interview_id)
        if interview.applicant_id != user_id:
            raise ForbiddenException("You can only submit responses for your own interviews")

        interview.responses = [r.model_dump() for r in data.responses]
        interview.status = InterviewStatus.COMPLETED

        questions = interview.questions or []
        responses = interview.responses or []
        evaluation = await interview_agent.evaluate_responses(interview.job_title, questions, responses)

        interview.ai_score = float(evaluation.get("overallScore", 0))
        interview.ai_summary = evaluation.get("summary", "")
        interview.evaluation = evaluation
        job = (await db.execute(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
        if job:
            await notification_service.create(
                db,
                recipient_id=job.employer_id,
                title="AI interview completed",
                message=f"{interview.applicant_name or 'A candidate'} completed the AI interview for {interview.job_title}.",
                type="interview",
                data={
                    "interviewId": str(interview.id),
                    "applicationId": str(interview.application_id),
                    "jobId": str(interview.job_id),
                    "score": interview.ai_score,
                },
            )

        await db.flush()

    async def security_fail(self, db: AsyncSession, interview_id: uuid.UUID, user_id: uuid.UUID, reason: str) -> None:
        interview = await self.get_by_id(db, interview_id)
        if interview.applicant_id != user_id:
            raise ForbiddenException("You can only fail your own interview")
        if InterviewType(interview.type) != InterviewType.AI:
            raise ForbiddenException("Security failure only applies to AI interviews")

        summary = reason or "Interview failed due to security violation."
        interview.status = InterviewStatus.COMPLETED
        interview.ai_score = 0
        interview.ai_summary = summary
        interview.evaluation = {
            "overallScore": 0,
            "technicalScore": 0,
            "communicationScore": 0,
            "problemSolvingScore": 0,
            "cultureFitScore": 0,
            "strengths": [],
            "improvements": ["The interview was closed because the candidate left the secure interview screen."],
            "summary": summary,
            "securityFailed": True,
        }
        job = (await db.execute(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
        if job:
            await notification_service.create(
                db,
                recipient_id=job.employer_id,
                title="AI interview closed",
                message=f"{interview.applicant_name or 'A candidate'}'s AI interview for {interview.job_title} was closed for a security violation.",
                type="interview",
                data={
                    "interviewId": str(interview.id),
                    "applicationId": str(interview.application_id),
                    "jobId": str(interview.job_id),
                    "securityFailed": True,
                },
            )
        await db.flush()

    async def complete_human_interview(
        self,
        db: AsyncSession,
        interview_id: uuid.UUID,
        employer_id: uuid.UUID,
        data: HumanInterviewCompleteRequest,
    ) -> Interview:
        interview = await self.get_by_id(db, interview_id)
        stmt = select(Job).where(Job.id == interview.job_id, Job.employer_id == employer_id)
        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            raise ForbiddenException("You can only complete your own interviews")
        if InterviewType(interview.type) != InterviewType.HUMAN:
            raise ForbiddenException("Only human interviews can be completed manually")

        interview.status = InterviewStatus.COMPLETED
        interview.ai_score = float(data.score)
        interview.ai_summary = data.comments
        interview.evaluation = {
            "overallScore": float(data.score),
            "technicalScore": float(data.score),
            "communicationScore": float(data.score),
            "problemSolvingScore": float(data.score),
            "cultureFitScore": float(data.score),
            "strengths": [],
            "improvements": [],
            "summary": data.comments,
            "humanComments": data.comments,
            "evaluationSource": "human",
        }
        await db.flush()
        await db.refresh(interview)
        return interview

    def _transcript_items(self, interview: Interview) -> list[dict]:
        questions_by_id = {str(q.get("id")): q for q in (interview.questions or [])}
        items: list[dict] = []
        for response in interview.responses or []:
            question = questions_by_id.get(str(response.get("questionId"))) or {}
            items.append(
                {
                    "questionId": str(response.get("questionId", "")),
                    "question": question.get("question", "Question text unavailable"),
                    "type": question.get("type"),
                    "category": question.get("category"),
                    "response": response.get("response", ""),
                    "duration": int(response.get("duration") or 0),
                    "timestamp": response.get("timestamp", ""),
                }
            )
        return items

    async def get_results(self, db: AsyncSession, interview_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        interview = await self.get_by_id(db, interview_id)

        # Allow access for the applicant or the employer who owns the job
        if interview.applicant_id != user_id:
            stmt = select(Job).where(Job.id == interview.job_id, Job.employer_id == user_id)
            result = await db.execute(stmt)
            if not result.scalar_one_or_none():
                raise ForbiddenException("You don't have access to these results")

        if InterviewStatus(interview.status) != InterviewStatus.COMPLETED:
            raise NotFoundException("Interview results not yet available")

        evaluation = interview.evaluation or {}
        return {
            "interviewId": str(interview.id),
            "overallScore": evaluation.get("overallScore", 0),
            "technicalScore": evaluation.get("technicalScore", 0),
            "communicationScore": evaluation.get("communicationScore", 0),
            "problemSolvingScore": evaluation.get("problemSolvingScore", 0),
            "cultureFitScore": evaluation.get("cultureFitScore", 0),
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", []),
            "summary": evaluation.get("summary", ""),
            "responses": self._transcript_items(interview),
        }


interview_service = InterviewService()
