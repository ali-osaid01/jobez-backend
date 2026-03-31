# Import all models here so Alembic can discover them
from app.models.user import User  # noqa: F401
from app.models.profile import Profile  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.bookmark import Bookmark  # noqa: F401
from app.models.application import Application  # noqa: F401
from app.models.interview import Interview  # noqa: F401
