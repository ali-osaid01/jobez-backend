import hashlib

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)


class TokenService:
    def create_tokens(self, user_id: str, role: str) -> tuple[str, str]:
        access_token = create_access_token(subject=user_id, role=role)
        refresh_token = create_refresh_token(subject=user_id)
        return access_token, refresh_token

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def verify_refresh(self, token: str) -> dict:
        return verify_refresh_token(token)


token_service = TokenService()
