import re

from config import settings


def validate_password(password: str) -> str:
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters"
        )
    return password


def validate_username(username: str) -> str:
    if len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be between 3 and 50 characters")
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        raise ValueError(
            "Username may only contain letters, digits, hyphens, and underscores"
        )
    return username
