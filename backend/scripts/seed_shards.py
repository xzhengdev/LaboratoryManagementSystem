import json
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import AssetBudget, Campus, Laboratory, User
from app.services.db_router_service import campus_db_session


def parse_campus_db_map(raw: str):
    text = str(raw or "").strip()
    if not text:
        return {}
    data = json.loads(text)
    result = {}
    for key, value in (data or {}).items():
        try:
            campus_id = int(key)
        except Exception:
            continue
        uri = str(value or "").strip()
        if uri:
            result[campus_id] = uri
    return result


def clone_or_update_campus(session, source_campus):
    row = session.query(Campus).get(source_campus.id)
    if not row:
        row = Campus(id=source_campus.id)
        session.add(row)
    row.campus_name = source_campus.campus_name
    row.address = source_campus.address
    row.description = source_campus.description
    row.cover_url = source_campus.cover_url
    row.status = source_campus.status


def clone_or_update_laboratory(session, source_lab):
    row = session.query(Laboratory).get(source_lab.id)
    if not row:
        row = Laboratory(id=source_lab.id)
        session.add(row)
    row.campus_id = source_lab.campus_id
    row.lab_name = source_lab.lab_name
    row.location = source_lab.location
    row.capacity = source_lab.capacity
    row.open_time = source_lab.open_time
    row.close_time = source_lab.close_time
    row.status = source_lab.status
    row.description = source_lab.description
    row.photos = source_lab.photos


def clone_or_update_user(session, source_user):
    row = session.query(User).get(source_user.id)
    if not row:
        row = User(id=source_user.id)
        session.add(row)
    row.username = source_user.username
    row.password_hash = source_user.password_hash
    row.real_name = source_user.real_name
    row.phone = source_user.phone
    row.email = source_user.email
    row.avatar_url = source_user.avatar_url
    row.role = source_user.role
    row.campus_id = source_user.campus_id
    row.status = source_user.status


def ensure_budget(session, campus_id, total_amount=200000):
    budget = session.query(AssetBudget).filter_by(campus_id=campus_id).first()
    if not budget:
        budget = AssetBudget(
            campus_id=campus_id,
            total_amount=total_amount,
            locked_amount=0,
            used_amount=0,
            remark="seed 初始化预算",
        )
        session.add(budget)
    elif float(budget.total_amount or 0) <= 0:
        budget.total_amount = total_amount


def main():
    app = create_app()
    with app.app_context():
        campus_map = parse_campus_db_map(app.config.get("CAMPUS_DB_URI_MAP", ""))
        if not campus_map:
            raise RuntimeError("未配置 CAMPUS_DB_URI_MAP")

        source_campuses = {row.id: row for row in db.session.query(Campus).all()}
        source_labs = db.session.query(Laboratory).all()
        source_users = db.session.query(User).all()

        if not source_campuses:
            raise RuntimeError("默认库没有 campus 数据，请先执行 python scripts/seed.py")

        for campus_id in sorted(campus_map.keys()):
            if campus_id not in source_campuses:
                print(f"[WARN] 默认库中未找到 campus_id={campus_id}，跳过")
                continue

            campus_source = source_campuses[campus_id]
            campus_labs = [lab for lab in source_labs if lab.campus_id == campus_id]
            campus_users = [
                user
                for user in source_users
                if user.role == "system_admin" or user.campus_id == campus_id
            ]

            with campus_db_session(campus_id) as session:
                try:
                    clone_or_update_campus(session, campus_source)
                    for lab in campus_labs:
                        clone_or_update_laboratory(session, lab)
                    for user in campus_users:
                        clone_or_update_user(session, user)
                    ensure_budget(session, campus_id)
                    session.commit()
                    print(
                        f"[OK] 校区{campus_id} 已同步: campuses=1 labs={len(campus_labs)} users={len(campus_users)}"
                    )
                except Exception:
                    session.rollback()
                    raise

        print("[DONE] 分库种子数据同步完成")


if __name__ == "__main__":
    main()
