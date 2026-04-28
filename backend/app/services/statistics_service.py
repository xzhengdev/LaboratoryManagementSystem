"""
统计服务模块
在单库模式下走默认查询，在分库模式下按校区库聚合统计。
"""

from sqlalchemy import case, func

from app.models import Campus, Laboratory, Reservation
from app.services.cache_service import get_cached_statistics, set_cached_statistics
from app.services.db_router_service import campus_db_session, get_routed_campus_ids


def _is_sharded_mode():
    return bool(get_routed_campus_ids())


def _campus_ids_for_scope(campus_id=None):
    if campus_id is not None:
        return [int(campus_id)]
    campus_ids = get_routed_campus_ids()
    return campus_ids or [0]


def _overview_in_one_campus(session):
    reservation_query = session.query(Reservation)
    laboratory_query = session.query(Laboratory)
    return {
        "lab_count": laboratory_query.count(),
        "reservation_count": reservation_query.count(),
        "approved_count": reservation_query.filter(Reservation.status == "approved").count(),
        "pending_count": reservation_query.filter(Reservation.status == "pending").count(),
    }


def get_overview(campus_id=None):
    cached = get_cached_statistics("overview", campus_id)
    if isinstance(cached, dict):
        return cached

    if not _is_sharded_mode():
        reservation_query = Reservation.query
        laboratory_query = Laboratory.query
        if campus_id is not None:
            reservation_query = reservation_query.filter(Reservation.campus_id == int(campus_id))
            laboratory_query = laboratory_query.filter(Laboratory.campus_id == int(campus_id))
        result = {
            "campus_count": 1 if campus_id is not None else Campus.query.count(),
            "lab_count": laboratory_query.count(),
            "reservation_count": reservation_query.count(),
            "approved_count": reservation_query.filter(Reservation.status == "approved").count(),
            "pending_count": reservation_query.filter(Reservation.status == "pending").count(),
        }
        set_cached_statistics("overview", campus_id, result)
        return result

    totals = {
        "campus_count": 0,
        "lab_count": 0,
        "reservation_count": 0,
        "approved_count": 0,
        "pending_count": 0,
    }
    for cid in _campus_ids_for_scope(campus_id):
        with campus_db_session(cid) as session:
            part = _overview_in_one_campus(session)
        totals["campus_count"] += 1
        totals["lab_count"] += int(part["lab_count"])
        totals["reservation_count"] += int(part["reservation_count"])
        totals["approved_count"] += int(part["approved_count"])
        totals["pending_count"] += int(part["pending_count"])

    set_cached_statistics("overview", campus_id, totals)
    return totals


def _campus_name_from_session(session, campus_id):
    row = session.query(Campus).filter(Campus.id == int(campus_id)).first()
    if row:
        return row.campus_name
    return f"校区{campus_id}"


def get_campus_statistics(campus_id=None):
    cached = get_cached_statistics("campus", campus_id)
    if isinstance(cached, list):
        return cached

    if not _is_sharded_mode():
        query = (
            Campus.query
            .outerjoin(Laboratory, Laboratory.campus_id == Campus.id)
            .outerjoin(Reservation, Reservation.campus_id == Campus.id)
            .with_entities(
                Campus.id,
                Campus.campus_name,
                func.count(func.distinct(Laboratory.id)).label("lab_count"),
                func.count(func.distinct(Reservation.id)).label("reservation_count"),
            )
        )
        if campus_id is not None:
            query = query.filter(Campus.id == campus_id)
        rows = query.group_by(Campus.id, Campus.campus_name).all()
        result = [
            {
                "campus_id": row.id,
                "campus_name": row.campus_name,
                "lab_count": int(row.lab_count or 0),
                "reservation_count": int(row.reservation_count or 0),
            }
            for row in rows
        ]
        set_cached_statistics("campus", campus_id, result)
        return result

    result = []
    for cid in _campus_ids_for_scope(campus_id):
        with campus_db_session(cid) as session:
            result.append(
                {
                    "campus_id": cid,
                    "campus_name": _campus_name_from_session(session, cid),
                    "lab_count": int(session.query(Laboratory).count()),
                    "reservation_count": int(session.query(Reservation).count()),
                }
            )

    set_cached_statistics("campus", campus_id, result)
    return result


def _lab_usage_in_session(session, campus_id):
    rows = (
        session.query(
            Laboratory.id,
            Laboratory.lab_name,
            Laboratory.campus_id,
            func.count(Reservation.id).label("reservation_count"),
            func.sum(case((Reservation.status == "approved", 1), else_=0)).label("approved_count"),
        )
        .outerjoin(Reservation, Reservation.lab_id == Laboratory.id)
        .group_by(Laboratory.id, Laboratory.lab_name, Laboratory.campus_id)
        .all()
    )
    return [
        {
            "lab_id": row.id,
            "lab_name": row.lab_name,
            "campus_id": row.campus_id if row.campus_id is not None else campus_id,
            "reservation_count": int(row.reservation_count or 0),
            "approved_count": int(row.approved_count or 0),
        }
        for row in rows
    ]


def get_lab_usage(campus_id=None):
    cached = get_cached_statistics("lab_usage", campus_id)
    if isinstance(cached, list):
        return cached

    if not _is_sharded_mode():
        query = (
            Laboratory.query
            .outerjoin(Reservation, Reservation.lab_id == Laboratory.id)
            .with_entities(
                Laboratory.id,
                Laboratory.lab_name,
                Laboratory.campus_id,
                func.count(Reservation.id).label("reservation_count"),
                func.sum(case((Reservation.status == "approved", 1), else_=0)).label("approved_count"),
            )
        )
        if campus_id is not None:
            query = query.filter(Laboratory.campus_id == campus_id)
        rows = query.group_by(Laboratory.id, Laboratory.lab_name, Laboratory.campus_id).all()
        result = [
            {
                "lab_id": row.id,
                "lab_name": row.lab_name,
                "campus_id": row.campus_id,
                "reservation_count": int(row.reservation_count or 0),
                "approved_count": int(row.approved_count or 0),
            }
            for row in rows
        ]
        set_cached_statistics("lab_usage", campus_id, result)
        return result

    result = []
    for cid in _campus_ids_for_scope(campus_id):
        with campus_db_session(cid) as session:
            result.extend(_lab_usage_in_session(session, cid))

    set_cached_statistics("lab_usage", campus_id, result)
    return result
