"""Password and JWT helpers; secrets never enter GraphQL responses or logs."""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings

PASSWORD_HASHER = PasswordHash.recommended()
TOKEN_TTL_HOURS = 24


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return PASSWORD_HASHER.verify(password, password_hash)


def create_access_token(user_id: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    return jwt.encode({"sub": user_id, "exp": expires_at}, settings.jwt_secret, algorithm="HS256")


def decode_access_token(value: str) -> str | None:
    try:
        payload = jwt.decode(value, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
