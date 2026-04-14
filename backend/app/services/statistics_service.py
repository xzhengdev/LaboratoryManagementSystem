from sqlalchemy import case, func

from app.models import Campus, Laboratory, Reservation


def get_overview():
    # 返回控制台顶部的总览统计。
    return {
        "campus_count": Campus.query.count(),
        "lab_count": Laboratory.query.count(),
        "reservation_count": Reservation.query.count(),
        "approved_count": Reservation.query.filter_by(status="approved").count(),
        "pending_count": Reservation.query.filter_by(status="pending").count(),
    }


def get_campus_statistics():
    # 统计每个校区的实验室数量与预约数量。
    rows = (
        Campus.query.outerjoin(Laboratory, Laboratory.campus_id == Campus.id)
        .outerjoin(Reservation, Reservation.campus_id == Campus.id)
        .with_entities(
            Campus.id,
            Campus.campus_name,
            func.count(func.distinct(Laboratory.id)).label("lab_count"),
            func.count(Reservation.id).label("reservation_count"),
        )
        .group_by(Campus.id, Campus.campus_name)
        .all()
    )
    return [
        {
            "campus_id": row.id,
            "campus_name": row.campus_name,
            "lab_count": row.lab_count,
            "reservation_count": row.reservation_count,
        }
        for row in rows
    ]


def get_lab_usage():
    # 统计实验室使用情况，重点关注预约总数与已通过数量。
    rows = (
        Laboratory.query.outerjoin(Reservation, Reservation.lab_id == Laboratory.id)
        .with_entities(
            Laboratory.id,
            Laboratory.lab_name,
            Laboratory.campus_id,
            func.count(Reservation.id).label("reservation_count"),
            func.sum(case((Reservation.status == "approved", 1), else_=0)).label(
                "approved_count"
            ),
        )
        .group_by(Laboratory.id, Laboratory.lab_name, Laboratory.campus_id)
        .all()
    )
    return [
        {
            "lab_id": row.id,
            "lab_name": row.lab_name,
            "campus_id": row.campus_id,
            "reservation_count": int(row.reservation_count or 0),
            "approved_count": int(row.approved_count or 0),
        }
        for row in rows
    ]
