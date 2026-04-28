import time
from contextlib import contextmanager
from uuid import uuid4

from flask import current_app

import app.extensions as app_extensions
from app.utils.exceptions import AppError

_UNLOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
  return redis.call('del', KEYS[1])
else
  return 0
end
"""


def _lock_enabled():
    return bool(current_app.config.get("ENABLE_DISTRIBUTED_LOCK", False))


def _build_lock_key(lab_id, reservation_date):
    # 同实验室同一天串行化处理，避免并发预约/审批出现竞态。
    return f"lab:reservation:lock:{lab_id}:{reservation_date.isoformat()}"


@contextmanager
def distributed_named_lock(lock_key, conflict_message="当前请求较多，请稍后重试"):
    """
    通用分布式锁：
    - 开启分布式锁且 Redis 可用时：使用 Redis 锁
    - 其他情况：降级为空上下文（保持开发环境可运行）
    """
    if not _lock_enabled():
        yield
        return

    redis_client = app_extensions.redis_client
    if redis_client is None:
        raise AppError("分布式锁已启用但 Redis 不可用，请检查 REDIS_URL 配置", 500, 50041)

    token = uuid4().hex
    ttl_seconds = max(1, int(current_app.config.get("REDIS_LOCK_TTL_SECONDS", 15)))
    wait_timeout = float(current_app.config.get("REDIS_LOCK_WAIT_TIMEOUT_SECONDS", 3))
    retry_interval = float(
        current_app.config.get("REDIS_LOCK_RETRY_INTERVAL_SECONDS", 0.1)
    )

    deadline = time.time() + wait_timeout
    acquired = False
    while time.time() < deadline:
        try:
            acquired = bool(redis_client.set(lock_key, token, nx=True, ex=ttl_seconds))
            if acquired:
                break
        except Exception as exc:
            raise AppError(f"分布式锁获取失败: {exc}", 500, 50042)
        time.sleep(max(0.01, retry_interval))

    if not acquired:
        raise AppError(conflict_message, 409, 40911)

    try:
        yield
    finally:
        try:
            redis_client.eval(_UNLOCK_SCRIPT, 1, lock_key, token)
        except Exception:
            # 释放失败不抛出，避免覆盖主业务异常。
            pass


@contextmanager
def reservation_slot_lock(lab_id, reservation_date):
    """
    预约并发锁：同实验室同一天串行化处理，避免并发预约/审批出现竞态。
    """
    lock_key = _build_lock_key(lab_id, reservation_date)
    with distributed_named_lock(lock_key, "当前预约请求较多，请稍后重试"):
        yield


@contextmanager
def asset_budget_lock(campus_id):
    """
    资产预算锁：同一校区预算串行化处理，避免并发申报导致锁定额度超额。
    """
    lock_key = f"lab:asset_budget:lock:{campus_id}"
    with distributed_named_lock(lock_key, "当前资产申报较多，请稍后重试"):
        yield
