from fastapi import APIRouter

from app.api.v1 import applications, auth, dashboard, health, interviews, jobs, profile

v1_router = APIRouter()

v1_router.include_router(health.router)
v1_router.include_router(auth.router)
v1_router.include_router(profile.router)
v1_router.include_router(jobs.router)
v1_router.include_router(applications.router)
v1_router.include_router(interviews.router)
v1_router.include_router(dashboard.router)
