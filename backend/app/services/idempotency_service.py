import hashlib
import json
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import IdempotencyRecord
from app.utils.exceptions import AppError


def normalize_idempotency_key(idempotency_key):
    return str(idempotency_key or "").strip()[:128]


def build_payload_signature(payload):
    canonical = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decode_response(record):
    if not record.response_payload:
        return None
    try:
        return json.loads(record.response_payload)
    except Exception:
        return None


def _consume_existing(record, request_hash):
    if record.request_hash != request_hash:
        raise AppError("同一幂等键对应的请求参数不一致，请更换 Idempotency-Key", 409, 40921)
    if record.status == "succeeded":
        cached = _decode_response(record)
        if cached is not None:
            return None, cached
        raise AppError("该请求已处理完成，请刷新后重试", 409, 40922)
    if record.status == "failed":
        raise AppError(
            record.error_message or "该请求之前已失败，请更换 Idempotency-Key 后重试",
            record.http_status or 409,
            40923,
        )
    raise AppError("请求正在处理中，请稍后重试", 409, 40924)


def claim_idempotency_record(current_user, endpoint, idempotency_key, request_hash):
    if not current_user or not endpoint or not idempotency_key:
        return None, None

    ttl_seconds = max(1, int(current_app.config.get("IDEMPOTENCY_TTL_SECONDS", 300)))
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=ttl_seconds)

    existing = IdempotencyRecord.query.filter_by(
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
    ).first()

    if existing and existing.expires_at <= now:
        db.session.delete(existing)
        db.session.commit()
        existing = None

    if existing:
        return _consume_existing(existing, request_hash)

    record = IdempotencyRecord(
        user_id=current_user.id,
        endpoint=endpoint,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status="processing",
        expires_at=expires_at,
        http_status=202,
    )
    db.session.add(record)
    try:
        db.session.commit()
        return record, None
    except IntegrityError:
        db.session.rollback()
        existing = IdempotencyRecord.query.filter_by(
            user_id=current_user.id,
            endpoint=endpoint,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return _consume_existing(existing, request_hash)
        raise AppError("幂等记录创建失败，请重试", 500, 50043)


def mark_idempotency_success(record_id, response_data):
    if not record_id:
        return
    try:
        record = IdempotencyRecord.query.get(record_id)
        if not record:
            return
        record.status = "succeeded"
        record.http_status = 200
        record.error_message = None
        record.response_payload = json.dumps(response_data, ensure_ascii=False)
        db.session.commit()
    except Exception:
        db.session.rollback()


def mark_idempotency_failed(record_id, error_message, http_status=400):
    if not record_id:
        return
    try:
        record = IdempotencyRecord.query.get(record_id)
        if not record:
            return
        record.status = "failed"
        record.http_status = int(http_status or 400)
        record.error_message = (error_message or "请求处理失败")[:255]
        db.session.commit()
    except Exception:
        db.session.rollback()
