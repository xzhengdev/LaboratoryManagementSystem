from datetime import datetime

from flask import current_app

from app.models import NotificationMessage
from app.services.db_router_service import campus_db_session, get_routed_campus_ids
from app.utils.exceptions import AppError


def create_notification(
    session,
    *,
    campus_id,
    user_id,
    title,
    content,
    level="info",
    biz_type="general",
    biz_id=None,
):
    item = NotificationMessage(
        campus_id=int(campus_id),
        user_id=int(user_id),
        title=str(title or "").strip()[:100],
        content=str(content or "").strip()[:500],
        level=str(level or "info").strip()[:20] or "info",
        biz_type=str(biz_type or "general").strip()[:50] or "general",
        biz_id=int(biz_id) if biz_id else None,
        is_read=False,
    )
    session.add(item)
    return item


def _campus_candidates_for_user(current_user):
    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        return campus_ids or [0]
    return [current_user.campus_id or 0]


def _is_table_missing_error(error):
    text = str(error or "").lower()
    return "doesn't exist" in text or "no such table" in text


def list_notifications(current_user, filters):
    unread_only = str(filters.get("unread_only") or "").strip() in {"1", "true", "yes"}

    rows = []
    for campus_id in _campus_candidates_for_user(current_user):
        try:
            with campus_db_session(campus_id) as session:
                query = session.query(NotificationMessage).filter_by(user_id=current_user.id)
                if unread_only:
                    query = query.filter_by(is_read=False)
                for item in query.order_by(NotificationMessage.created_at.desc()).limit(200).all():
                    rows.append(item.to_dict())
        except Exception as error:
            if _is_table_missing_error(error):
                current_app.logger.warning("notification table missing in campus %s", campus_id)
                continue
            raise

    rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return rows


def get_unread_count(current_user):
    total = 0
    for campus_id in _campus_candidates_for_user(current_user):
        try:
            with campus_db_session(campus_id) as session:
                total += int(
                    session.query(NotificationMessage)
                    .filter_by(user_id=current_user.id, is_read=False)
                    .count()
                )
        except Exception as error:
            if _is_table_missing_error(error):
                current_app.logger.warning("notification table missing in campus %s", campus_id)
                continue
            raise
    return {"unread_count": total}


def mark_notification_read(current_user, notification_id):
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            item = session.query(NotificationMessage).get(int(notification_id))
            if not item:
                continue
            if item.user_id != current_user.id:
                raise AppError("不能操作其他用户通知", 403, 40371)
            if not item.is_read:
                item.is_read = True
                item.read_at = datetime.utcnow()
                session.commit()
            return item.to_dict()
    raise AppError("通知不存在", 404, 40431)


def mark_all_notifications_read(current_user):
    changed = 0
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            rows = (
                session.query(NotificationMessage)
                .filter_by(user_id=current_user.id, is_read=False)
                .all()
            )
            if not rows:
                continue
            now = datetime.utcnow()
            for item in rows:
                item.is_read = True
                item.read_at = now
                changed += 1
            session.commit()
    return {"marked_count": changed}
