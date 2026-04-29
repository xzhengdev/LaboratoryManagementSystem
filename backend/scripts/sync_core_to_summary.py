import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.models import Campus, Equipment, Laboratory, User
from app.services.db_router_service import campus_db_session, get_routed_campus_ids, summary_db_session


def _upsert_campus(session, src):
    row = session.query(Campus).get(src.id)
    if not row:
        row = Campus(id=src.id)
        session.add(row)
    row.campus_name = src.campus_name
    row.address = src.address
    row.description = src.description
    row.cover_url = src.cover_url
    row.status = src.status


def _upsert_lab(session, src):
    row = session.query(Laboratory).get(src.id)
    if not row:
        row = Laboratory(id=src.id)
        session.add(row)
    row.campus_id = src.campus_id
    row.lab_name = src.lab_name
    row.location = src.location
    row.capacity = src.capacity
    row.open_time = src.open_time
    row.close_time = src.close_time
    row.status = src.status
    row.description = src.description
    row.photos = src.photos


def _upsert_equipment(session, src):
    row = session.query(Equipment).get(src.id)
    if not row:
        row = Equipment(id=src.id)
        session.add(row)
    row.lab_id = src.lab_id
    row.equipment_name = src.equipment_name
    row.quantity = src.quantity
    row.status = src.status
    row.description = src.description


def _upsert_user(session, src):
    row = session.query(User).get(src.id)
    if not row:
        row = session.query(User).filter_by(username=src.username).first()
    if not row:
        row = User(id=src.id)
        session.add(row)
    row.username = src.username
    row.password_hash = src.password_hash
    row.real_name = src.real_name
    row.phone = src.phone
    row.email = src.email
    row.avatar_url = src.avatar_url
    row.role = src.role
    row.campus_id = src.campus_id
    row.status = src.status


def main():
    app = create_app()
    with app.app_context():
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            raise RuntimeError("未配置 CAMPUS_DB_URI_MAP，无法同步")

        with summary_db_session() as summary:
            total_campuses = 0
            total_labs = 0
            total_equipment = 0
            total_users = 0

            for campus_id in campus_ids:
                with campus_db_session(campus_id) as shard:
                    campus = shard.query(Campus).get(campus_id)
                    if campus:
                        _upsert_campus(summary, campus)
                        total_campuses += 1

                    labs = shard.query(Laboratory).all()
                    for lab in labs:
                        _upsert_lab(summary, lab)
                    total_labs += len(labs)

                    eqs = shard.query(Equipment).all()
                    for eq in eqs:
                        _upsert_equipment(summary, eq)
                    total_equipment += len(eqs)

                    users = shard.query(User).all()
                    for user in users:
                        _upsert_user(summary, user)
                    total_users += len(users)

            summary.commit()
            print(
                f"[OK] summary同步完成 campuses={total_campuses} labs={total_labs} "
                f"equipment={total_equipment} users={total_users}"
            )


if __name__ == "__main__":
    main()

