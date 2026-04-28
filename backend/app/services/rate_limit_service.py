import time
from collections import defaultdict

from flask import current_app

import app.extensions as app_extensions
from app.utils.exceptions import AppError

_local_counter = defaultdict(int)
_local_expire = {}


def _is_enabled():
    return bool(current_app.config.get("ENABLE_RATE_LIMIT", False))


def _window_bucket(window_seconds):
    now = int(time.time())
    return now - (now % window_seconds)


def _build_key(action, user_id, window_seconds):
    bucket = _window_bucket(window_seconds)
    return f"rate_limit:{action}:{user_id}:{bucket}"


def _check_with_redis(key, limit, window_seconds):
    client = app_extensions.redis_client
    if client is None:
        return None
    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, window_seconds)
        return count <= limit
    except Exception:
        return None


def _check_with_local(key, limit, window_seconds):
    now = int(time.time())
    expire_at = _local_expire.get(key)
    if expire_at is not None and expire_at <= now:
        _local_counter.pop(key, None)
        _local_expire.pop(key, None)

    _local_counter[key] += 1
    if key not in _local_expire:
        _local_expire[key] = now + window_seconds
    return _local_counter[key] <= limit


def enforce_user_rate_limit(action, user_id, limit_per_window, window_seconds, error_code):
    """
    用户限流校验。
    在启用限流后优先用 Redis，失败时降级为进程内计数。
    """
    if not _is_enabled():
        return
    if not user_id:
        return
    try:
        limit = int(limit_per_window)
        window = int(window_seconds)
    except Exception:
        return
    if limit <= 0 or window <= 0:
        return

    key = _build_key(action, user_id, window)

    allowed = _check_with_redis(key, limit, window)
    if allowed is None:
        allowed = _check_with_local(key, limit, window)
    if allowed:
        return

    raise AppError("请求过于频繁，请稍后再试", 429, error_code)


def enforce_create_reservation_rate_limit(user_id):
    enforce_user_rate_limit(
        action="create_reservation",
        user_id=user_id,
        limit_per_window=current_app.config.get(
            "RATE_LIMIT_CREATE_RESERVATION_PER_MIN", 30
        ),
        window_seconds=60,
        error_code=42911,
    )


def enforce_approve_reservation_rate_limit(user_id):
    enforce_user_rate_limit(
        action="approve_reservation",
        user_id=user_id,
        limit_per_window=current_app.config.get(
            "RATE_LIMIT_APPROVE_RESERVATION_PER_MIN", 60
        ),
        window_seconds=60,
        error_code=42912,
    )

