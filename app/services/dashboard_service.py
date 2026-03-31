import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ApplicationStatus, InterviewStatus, JobStatus
from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User


class DashboardService:
    async def get_job_seeker_stats(self, db: AsyncSession, user: User) -> dict:
        user_id = user.id

        # Total applications
        total_apps = (
            await db.execute(
                select(func.count()).where(Application.applicant_id == user_id)
            )
        ).scalar_one()

        # Scheduled interviews
        scheduled = (
            await db.execute(
                select(func.count()).where(
                    Interview.applicant_id == user_id,
                    Interview.status == InterviewStatus.SCHEDULED.value,
                )
            )
        ).scalar_one()

        # Recent applications (last 5)
        recent_apps_result = await db.execute(
            select(Application)
            .where(Application.applicant_id == user_id)
            .order_by(Application.created_at.desc())
            .limit(5)
        )
        recent_apps = list(recent_apps_result.scalars().all())

        # Upcoming interviews
        upcoming_result = await db.execute(
            select(Interview)
            .where(
                Interview.applicant_id == user_id,
                Interview.status == InterviewStatus.SCHEDULED.value,
            )
            .order_by(Interview.scheduled_date.asc())
            .limit(5)
        )
        upcoming = list(upcoming_result.scalars().all())

        # Recommended jobs (stub: newest active jobs)
        recommended_result = await db.execute(
            select(Job)
            .where(Job.status == JobStatus.ACTIVE.value)
            .order_by(Job.created_at.desc())
            .limit(5)
        )
        recommended = list(recommended_result.scalars().all())

        return {
            "totalApplications": total_apps,
            "scheduledInterviews": scheduled,
            "profileViews": 0,  # Stub
            "recentApplications": recent_apps,
            "upcomingInterviews": upcoming,
            "recommendedJobs": recommended,
        }

    async def get_employer_stats(self, db: AsyncSession, user: User) -> dict:
        employer_id = user.id

        # Active jobs
        active_jobs = (
            await db.execute(
                select(func.count()).where(
                    Job.employer_id == employer_id, Job.status == JobStatus.ACTIVE.value
                )
            )
        ).scalar_one()

        # Total applicants (across all jobs)
        total_applicants = (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .join(Job)
                .where(Job.employer_id == employer_id)
            )
        ).scalar_one()

        # Shortlisted
        shortlisted = (
            await db.execute(
                select(func.count())
                .select_from(Application)
                .join(Job)
                .where(
                    Job.employer_id == employer_id,
                    Application.status == ApplicationStatus.SHORTLISTED.value,
                )
            )
        ).scalar_one()

        # Pipeline counts
        pipeline_statuses = {}
        for status in ApplicationStatus:
            count = (
                await db.execute(
                    select(func.count())
                    .select_from(Application)
                    .join(Job)
                    .where(
                        Job.employer_id == employer_id,
                        Application.status == status.value,
                    )
                )
            ).scalar_one()
            pipeline_statuses[status.value] = count

        # AI interview done count
        ai_done = (
            await db.execute(
                select(func.count())
                .select_from(Interview)
                .join(Job)
                .where(
                    Job.employer_id == employer_id,
                    Interview.status == InterviewStatus.COMPLETED.value,
                )
            )
        ).scalar_one()

        # Active job postings
        active_postings_result = await db.execute(
            select(Job)
            .where(Job.employer_id == employer_id, Job.status == JobStatus.ACTIVE.value)
            .order_by(Job.created_at.desc())
            .limit(5)
        )
        active_postings = list(active_postings_result.scalars().all())

        # Recent applicants
        recent_result = await db.execute(
            select(Application)
            .join(Job)
            .where(Job.employer_id == employer_id)
            .order_by(Application.created_at.desc())
            .limit(5)
        )
        recent_applicants = list(recent_result.scalars().all())

        return {
            "activeJobs": active_jobs,
            "totalApplicants": total_applicants,
            "shortlisted": shortlisted,
            "contacted": 0,  # Stub
            "pipeline": {
                "applied": total_applicants,
                "aiInterviewDone": ai_done,
                "shortlisted": shortlisted,
                "contacted": 0,
                "offerSent": 0,
                "hired": pipeline_statuses.get(ApplicationStatus.HIRED.value, 0),
            },
            "activeJobPostings": active_postings,
            "recentApplicants": recent_applicants,
        }


dashboard_service = DashboardService()
