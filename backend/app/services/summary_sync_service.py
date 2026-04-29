from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import case, func

from app.models import (
    AssetItem,
    AssetPurchaseRequest,
    CampusSummarySnapshot,
    GlobalAssetBudget,
    LabDailyReport,
    Reservation,
)
from app.services.db_router_service import (
    campus_db_session,
    get_routed_campus_ids,
    summary_db_session,
)
from app.utils.exceptions import AppError


def _safe_decimal(value):
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0.00")


def _campus_ids_for_sync(target_campus_ids=None):
    if target_campus_ids:
        normalized = []
        for item in target_campus_ids:
            try:
                cid = int(item)
            except Exception:
                continue
            if cid not in normalized:
                normalized.append(cid)
        if normalized:
            return normalized
    campus_ids = get_routed_campus_ids()
    return campus_ids or [0]


def _ensure_summary_table(session):
    bind = session.get_bind()
    CampusSummarySnapshot.__table__.create(bind=bind, checkfirst=True)


def _collect_one_campus_snapshot(campus_id):
    with campus_db_session(campus_id) as session:
        reservation_stats = (
            session.query(
                func.count(Reservation.id).label("total"),
                func.sum(case((Reservation.status == "pending", 1), else_=0)).label("pending"),
                func.sum(case((Reservation.status == "approved", 1), else_=0)).label("approved"),
                func.sum(case((Reservation.status == "rejected", 1), else_=0)).label("rejected"),
            )
            .one()
        )

        asset_request_stats = (
            session.query(
                func.count(AssetPurchaseRequest.id).label("total"),
                func.sum(case((AssetPurchaseRequest.status == "pending", 1), else_=0)).label("pending"),
                func.sum(case((AssetPurchaseRequest.status == "approved", 1), else_=0)).label("approved"),
                func.sum(case((AssetPurchaseRequest.status == "rejected", 1), else_=0)).label("rejected"),
            )
            .one()
        )

        daily_report_stats = (
            session.query(
                func.count(LabDailyReport.id).label("total"),
                func.sum(case((LabDailyReport.status == "pending", 1), else_=0)).label("pending"),
                func.sum(case((LabDailyReport.status == "approved", 1), else_=0)).label("approved"),
                func.sum(case((LabDailyReport.status == "rejected", 1), else_=0)).label("rejected"),
            )
            .one()
        )

        asset_item_count = int(session.query(AssetItem.id).count() or 0)
        total_amount = Decimal("0.00")
        locked_amount = Decimal("0.00")
        used_amount = Decimal("0.00")
        available_amount = Decimal("0.00")

        campus_name = f"校区{campus_id}"
        first_reservation = session.query(Reservation).first()
        if first_reservation and first_reservation.campus and first_reservation.campus.campus_name:
            campus_name = str(first_reservation.campus.campus_name)
        else:
            first_report = session.query(LabDailyReport).first()
            if first_report and first_report.campus and first_report.campus.campus_name:
                campus_name = str(first_report.campus.campus_name)

        return {
            "campus_id": int(campus_id),
            "campus_name": campus_name,
            "reservation_count": int(reservation_stats.total or 0),
            "reservation_pending_count": int(reservation_stats.pending or 0),
            "reservation_approved_count": int(reservation_stats.approved or 0),
            "reservation_rejected_count": int(reservation_stats.rejected or 0),
            "asset_request_count": int(asset_request_stats.total or 0),
            "asset_request_pending_count": int(asset_request_stats.pending or 0),
            "asset_request_approved_count": int(asset_request_stats.approved or 0),
            "asset_request_rejected_count": int(asset_request_stats.rejected or 0),
            "asset_item_count": asset_item_count,
            "asset_budget_total_amount": total_amount,
            "asset_budget_locked_amount": locked_amount,
            "asset_budget_used_amount": used_amount,
            "asset_budget_available_amount": available_amount,
            "daily_report_count": int(daily_report_stats.total or 0),
            "daily_report_pending_count": int(daily_report_stats.pending or 0),
            "daily_report_approved_count": int(daily_report_stats.approved or 0),
            "daily_report_rejected_count": int(daily_report_stats.rejected or 0),
        }


def _global_budget_totals():
    with summary_db_session() as session:
        bind = session.get_bind()
        GlobalAssetBudget.__table__.create(bind=bind, checkfirst=True)
        row = session.query(GlobalAssetBudget).first()
        if not row:
            return {
                "asset_budget_total_amount": 0.0,
                "asset_budget_locked_amount": 0.0,
                "asset_budget_used_amount": 0.0,
                "asset_budget_available_amount": 0.0,
            }
        total = float(row.total_amount or 0)
        locked = float(row.locked_amount or 0)
        used = float(row.used_amount or 0)
        return {
            "asset_budget_total_amount": total,
            "asset_budget_locked_amount": locked,
            "asset_budget_used_amount": used,
            "asset_budget_available_amount": total - locked - used,
        }


def sync_campus_summary_snapshots(snapshot_date=None, target_campus_ids=None):
    target_date = snapshot_date or datetime.now(timezone.utc).date()
    rows = []
    for campus_id in _campus_ids_for_sync(target_campus_ids):
        rows.append(_collect_one_campus_snapshot(campus_id))

    with summary_db_session() as session:
        _ensure_summary_table(session)
        for row in rows:
            item = (
                session.query(CampusSummarySnapshot)
                .filter_by(snapshot_date=target_date, campus_id=row["campus_id"])
                .first()
            )
            if not item:
                item = CampusSummarySnapshot(snapshot_date=target_date, campus_id=row["campus_id"])
                session.add(item)
            for key, value in row.items():
                setattr(item, key, value)
        session.commit()

    totals = {
        "snapshot_date": target_date.isoformat(),
        "campus_count": len(rows),
        "reservation_count": 0,
        "asset_request_count": 0,
        "asset_item_count": 0,
        "daily_report_count": 0,
        "asset_budget_total_amount": 0.0,
        "asset_budget_locked_amount": 0.0,
        "asset_budget_used_amount": 0.0,
        "asset_budget_available_amount": 0.0,
    }
    for row in rows:
        totals["reservation_count"] += int(row["reservation_count"])
        totals["asset_request_count"] += int(row["asset_request_count"])
        totals["asset_item_count"] += int(row["asset_item_count"])
        totals["daily_report_count"] += int(row["daily_report_count"])

    totals.update(_global_budget_totals())

    return {"snapshot_date": target_date.isoformat(), "rows": rows, "totals": totals}


def get_latest_campus_summary_rows(campus_id=None):
    with summary_db_session() as session:
        _ensure_summary_table(session)
        latest_date = session.query(func.max(CampusSummarySnapshot.snapshot_date)).scalar()
        if not latest_date:
            return {"snapshot_date": None, "rows": [], "totals": {}}

        query = session.query(CampusSummarySnapshot).filter_by(snapshot_date=latest_date)
        if campus_id is not None:
            query = query.filter_by(campus_id=int(campus_id))
        rows = [item.to_dict() for item in query.order_by(CampusSummarySnapshot.campus_id.asc()).all()]

    totals = {
        "snapshot_date": latest_date.isoformat(),
        "campus_count": len(rows),
        "reservation_count": sum(int(item.get("reservation_count") or 0) for item in rows),
        "asset_request_count": sum(int(item.get("asset_request_count") or 0) for item in rows),
        "asset_item_count": sum(int(item.get("asset_item_count") or 0) for item in rows),
        "daily_report_count": sum(int(item.get("daily_report_count") or 0) for item in rows),
        "asset_budget_total_amount": 0.0,
        "asset_budget_locked_amount": 0.0,
        "asset_budget_used_amount": 0.0,
        "asset_budget_available_amount": 0.0,
    }
    totals.update(_global_budget_totals())
    return {"snapshot_date": latest_date.isoformat(), "rows": rows, "totals": totals}


def sync_summary_for_system_admin(current_user):
    if current_user.role != "system_admin":
        raise AppError("只有系统管理员可以执行汇总同步", 403, 40381)
    return sync_campus_summary_snapshots()
