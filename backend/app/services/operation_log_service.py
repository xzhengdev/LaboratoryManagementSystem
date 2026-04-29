from datetime import datetime, time

from sqlalchemy import or_

from app.extensions import db
from app.models import OperationLog, User
from app.services.db_router_service import campus_db_session, get_routed_campus_ids
from app.utils.exceptions import AppError


def _parse_date(value, field_name):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as error:
        raise AppError(f"{field_name} must use YYYY-MM-DD format", 400, 40081) from error


def _parse_limit(value):
    if value in (None, ""):
        return 100
    try:
        limit = int(value)
    except (TypeError, ValueError) as error:
        raise AppError("limit must be an integer", 400, 40082) from error
    if limit <= 0:
        raise AppError("limit must be greater than 0", 400, 40083)
    return min(limit, 300)


def _build_base_query(session, current_user, filters):
    query = session.query(OperationLog).join(User, OperationLog.user_id == User.id)
    if current_user.role == "lab_admin":
        query = query.filter(User.campus_id == current_user.campus_id)

    module = str(filters.get("module") or "").strip()
    if module:
        query = query.filter(OperationLog.module == module)

    action = str(filters.get("action") or "").strip()
    if action:
        query = query.filter(OperationLog.action == action)

    user_id = filters.get("user_id")
    if user_id not in (None, ""):
        try:
            query = query.filter(OperationLog.user_id == int(user_id))
        except (TypeError, ValueError) as error:
            raise AppError("user_id must be an integer", 400, 40084) from error

    keyword = str(filters.get("keyword") or "").strip()
    if keyword:
        like_text = f"%{keyword}%"
        query = query.filter(
            or_(
                OperationLog.module.ilike(like_text),
                OperationLog.action.ilike(like_text),
                OperationLog.detail.ilike(like_text),
                User.username.ilike(like_text),
                User.real_name.ilike(like_text),
            )
        )

    start_date = _parse_date(filters.get("start_date"), "start_date")
    end_date = _parse_date(filters.get("end_date"), "end_date")
    if start_date and end_date and start_date > end_date:
        raise AppError("start_date must be earlier than or equal to end_date", 400, 40085)

    if start_date:
        query = query.filter(
            OperationLog.created_at >= datetime.combine(start_date, time.min)
        )

    if end_date:
        query = query.filter(
            OperationLog.created_at <= datetime.combine(end_date, time.max)
        )
    return query


def _format_items(items):
    return [
        item.to_dict(
            {
                "username": item.user.username if item.user else None,
                "real_name": item.user.real_name if item.user else None,
                "role": item.user.role if item.user else None,
                "campus_id": item.user.campus_id if item.user else None,
                "campus_name": item.user.campus.campus_name
                if item.user and item.user.campus
                else None,
            }
        )
        for item in items
    ]


def list_operation_logs(current_user, filters):
    limit = _parse_limit(filters.get("limit"))

    # 开启分库后日志落在各校区库，这里需要按校区聚合查询
    campus_ids = get_routed_campus_ids()
    if campus_ids:
        target_ids = campus_ids
        if current_user.role == "lab_admin":
            target_ids = [current_user.campus_id]

        merged = []
        for campus_id in target_ids:
            with campus_db_session(campus_id) as session:
                query = _build_base_query(session, current_user, filters)
                items = (
                    query.order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
                    .limit(limit)
                    .all()
                )
                merged.extend(_format_items(items))

        merged.sort(
            key=lambda row: (
                str(row.get("created_at") or ""),
                int(row.get("id") or 0),
            ),
            reverse=True,
        )
        return merged[:limit]

    # 单库回退
    query = _build_base_query(db.session, current_user, filters)
    items = (
        query.order_by(OperationLog.created_at.desc(), OperationLog.id.desc())
        .limit(limit)
        .all()
    )
    return _format_items(items)
