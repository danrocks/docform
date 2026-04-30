import time
from fastapi import HTTPException, status

# TODO: Replace with Redis for multi-process/production deployments
_attempts: dict[str, tuple[int, float]] = {}

WINDOW_SECONDS = 900  # 15 minutes
MAX_FAILURES = 5


def check_rate_limit(key: str) -> None:
    entry = _attempts.get(key)
    if entry is None:
        return
    count, first_failure = entry
    if time.time() - first_failure > WINDOW_SECONDS:
        del _attempts[key]
        return
    if count >= MAX_FAILURES:
        retry_after = int(WINDOW_SECONDS - (time.time() - first_failure)) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def record_failure(key: str) -> None:
    entry = _attempts.get(key)
    now = time.time()
    if entry is None or now - entry[1] > WINDOW_SECONDS:
        _attempts[key] = (1, now)
    else:
        _attempts[key] = (entry[0] + 1, entry[1])


def reset(key: str) -> None:
    _attempts.pop(key, None)
