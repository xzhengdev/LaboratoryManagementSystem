from datetime import datetime

from flask import current_app

from app.extensions import db
from app.models import FileObject, LabDailyReport, Laboratory, OperationLog, User
from app.services.db_router_service import campus_db_session, get_routed_campus_ids, summary_db_session
from app.services.event_bus_service import publish_async_event
from app.services.notification_service import create_notification
from app.utils.exceptions import AppError
from app.utils.validators import parse_date


def _write_log(session, user_id, action, detail):
    session.add(OperationLog(user_id=user_id, module="daily_report", action=action, detail=detail))


def _load_user_name_map(user_ids):
    ids = sorted({int(uid) for uid in (user_ids or []) if uid})
    if not ids:
        return {}

    def _query_names(session):
        rows = session.query(User).filter(User.id.in_(ids)).all()
        return {
            int(row.id): (str(row.real_name or "").strip() or str(row.username or "").strip() or f"用户#{row.id}")
            for row in rows
        }

    try:
        with summary_db_session() as session:
            name_map = _query_names(session)
            if name_map:
                return name_map
    except Exception:
        pass

    try:
        return _query_names(db.session)
    except Exception:
        return {}


def _bind_photo_file_ids(session, current_user, campus_id, report_id, file_ids):
    if not file_ids:
        return
    normalized = []
    for item in file_ids:
        try:
            value = int(item)
            if value > 0:
                normalized.append(value)
        except Exception:
            continue

    if not normalized:
        return

    photos = session.query(FileObject).filter(FileObject.id.in_(normalized)).all()
    photo_map = {row.id: row for row in photos}
    for file_id in normalized:
        photo = photo_map.get(file_id)
        if not photo:
            raise AppError(f"图片文件不存在: {file_id}", 404, 40411)
        if photo.campus_id != campus_id:
            raise AppError("图片与日报所属校区不一致", 400, 40091)
        if photo.created_by != current_user.id and current_user.role != "system_admin":
            raise AppError("不能绑定其他用户上传的图片", 403, 40351)
        if photo.biz_type not in {"daily_report_temp", "daily_report_photo"}:
            raise AppError("图片类型不合法，无法绑定到日报")
        photo.biz_type = "daily_report_photo"
        photo.biz_id = report_id


def _resolve_campus_for_report(current_user, lab_id):
    if not lab_id:
        raise AppError("lab_id 不能为空")

    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
    else:
        if not current_user.campus_id:
            raise AppError("当前用户未绑定校区", 400, 40092)
        campus_ids = [current_user.campus_id]

    for campus_id in campus_ids:
        with campus_db_session(campus_id) as session:
            lab = session.query(Laboratory).get(int(lab_id))
            if lab:
                return campus_id, lab

    with campus_db_session(0) as session:
        lab = session.query(Laboratory).get(int(lab_id))
        if lab:
            if current_user.role != "system_admin" and current_user.campus_id != lab.campus_id:
                raise AppError("只能提交本校区实验室日报", 403, 40353)
            return lab.campus_id, lab

    raise AppError("实验室不存在", 404, 40401)


def create_daily_report(current_user, payload):
    if current_user.role != "student":
        raise AppError("日报提交仅支持学生端", 403, 40352)

    lab_id = int(payload.get("lab_id") or 0)
    campus_id, lab = _resolve_campus_for_report(current_user, lab_id)

    report_date = parse_date(payload.get("report_date"), "report_date")
    content = str(payload.get("content") or "").strip()
    if not content:
        raise AppError("日报内容不能为空")

    file_ids = payload.get("photo_file_ids") or []
    if not isinstance(file_ids, list):
        raise AppError("photo_file_ids 必须是数组")

    with campus_db_session(campus_id) as session:
        try:
            item = LabDailyReport(
                campus_id=campus_id,
                lab_id=lab.id,
                reporter_id=current_user.id,
                report_date=report_date,
                content=content,
                status="pending",
            )
            session.add(item)
            session.flush()
            _bind_photo_file_ids(session, current_user, campus_id, item.id, file_ids)
            _write_log(session, current_user.id, "create", f"提交实验室日报#{item.id}")
            session.commit()
            result = item.to_dict()
            publish_async_event(
                "daily_report.created",
                {
                    "report_id": item.id,
                    "campus_id": item.campus_id,
                    "lab_id": item.lab_id,
                    "report_date": item.report_date.isoformat(),
                    "status": item.status,
                },
            )
            return result
        except Exception:
            session.rollback()
            raise


def _list_reports_in_one_campus(session, current_user, filters):
    query = session.query(LabDailyReport).order_by(LabDailyReport.created_at.desc())
    if current_user.role in {"student", "teacher"}:
        query = query.filter_by(reporter_id=current_user.id)

    if filters.get("lab_id"):
        query = query.filter_by(lab_id=int(filters["lab_id"]))
    if filters.get("status"):
        query = query.filter_by(status=str(filters["status"]).strip())
    if filters.get("report_date"):
        query = query.filter_by(report_date=parse_date(filters.get("report_date"), "report_date"))

    rows = [item.to_dict() for item in query.all()]
    user_ids = []
    for row in rows:
        if row.get("reporter_id"):
            user_ids.append(row.get("reporter_id"))
        if row.get("reviewer_id"):
            user_ids.append(row.get("reviewer_id"))
    user_name_map = _load_user_name_map(user_ids)
    for row in rows:
        reporter_id = row.get("reporter_id")
        reviewer_id = row.get("reviewer_id")
        row["reporter_name"] = user_name_map.get(int(reporter_id), "") if reporter_id else ""
        row["reviewer_name"] = user_name_map.get(int(reviewer_id), "") if reviewer_id else ""
    return rows


def list_daily_reports(current_user, filters):
    if filters.get("campus_id"):
        target_campus_id = int(filters["campus_id"])
        if current_user.role == "lab_admin" and target_campus_id != current_user.campus_id:
            raise AppError("只能查看本校区日报", 403, 40357)
        with campus_db_session(target_campus_id) as session:
            return _list_reports_in_one_campus(session, current_user, filters)

    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            with campus_db_session(0) as session:
                return _list_reports_in_one_campus(session, current_user, filters)
        rows = []
        for campus_id in campus_ids:
            with campus_db_session(campus_id) as session:
                rows.extend(_list_reports_in_one_campus(session, current_user, filters))
        rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return rows

    with campus_db_session(current_user.campus_id) as session:
        return _list_reports_in_one_campus(session, current_user, filters)


def review_daily_report(current_user, report_item, review_status, review_remark=""):
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审核日报", 403, 40354)

    with campus_db_session(report_item.campus_id) as session:
        item = session.query(LabDailyReport).get(int(report_item.id))
        if not item:
            raise AppError("日报不存在", 404, 40413)

        if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
            raise AppError("只能审核本校区日报", 403, 40355)
        if item.status != "pending":
            raise AppError("当前日报不在待审核状态")

        status = str(review_status or "").strip().lower()
        if status not in {"approved", "rejected"}:
            raise AppError("review_status 只能是 approved 或 rejected")

        try:
            item.status = status
            item.reviewer_id = current_user.id
            item.review_remark = str(review_remark or "")[:255]
            item.reviewed_at = datetime.utcnow()
            notify_title = "实验室日报审核结果"
            notify_content = (
                f"你在 {item.report_date.isoformat()} 提交的实验室日报已{ '通过' if status == 'approved' else '驳回' }。"
            )
            if item.review_remark:
                notify_content = f"{notify_content} 审核意见：{item.review_remark}"
            try:
                create_notification(
                    session,
                    campus_id=item.campus_id,
                    user_id=item.reporter_id,
                    title=notify_title,
                    content=notify_content,
                    level="success" if status == "approved" else "warning",
                    biz_type="daily_report_review",
                    biz_id=item.id,
                )
            except Exception as notify_error:
                current_app.logger.warning("create daily report notification failed: %s", notify_error)
            _write_log(session, current_user.id, "review", f"审核日报#{item.id}: {status}")
            session.commit()
            result = item.to_dict()
            publish_async_event(
                f"daily_report.{status}",
                {
                    "report_id": item.id,
                    "campus_id": item.campus_id,
                    "lab_id": item.lab_id,
                    "status": item.status,
                },
            )
            return result
        except Exception:
            session.rollback()
            raise
