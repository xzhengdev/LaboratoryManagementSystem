import json
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.models import Campus, GlobalAssetBudget, Laboratory, User
from app.services.db_router_service import campus_db_session, summary_db_session

DEFAULT_PASSWORD = "123456"

CAMPUSES = [
    {"id": 5, "campus_name": "Haidian Campus", "address": "59 Zhongguancun Street, Haidian, Beijing",
     "description": "Main campus: CS, EE, Automation labs", "status": "active"},
    {"id": 6, "campus_name": "Fengtai Campus", "address": "Huaxiang, Fengtai, Beijing",
     "description": "Branch: Biomed, Environmental Science, Materials", "status": "active"},
    {"id": 7, "campus_name": "Hainan Campus", "address": "Li'an, Lingshui, Hainan",
     "description": "International: Marine Science, Tropical Agriculture", "status": "active"},
]

LABS = [
    {"id": 501, "campus_id": 5, "lab_name": "Computer Network Lab", "location": "Haidian Bldg A 302", "capacity": 40,
     "open_time": "08:00", "close_time": "22:00", "status": "available", "description": "Cisco routing & switching"},
    {"id": 502, "campus_id": 5, "lab_name": "AI Lab", "location": "Haidian Bldg B 101", "capacity": 30,
     "open_time": "08:30", "close_time": "21:30", "status": "available", "description": "GPU server cluster"},
    {"id": 503, "campus_id": 5, "lab_name": "Software Engineering Lab", "location": "Haidian Bldg C 205", "capacity": 50,
     "open_time": "08:00", "close_time": "22:00", "status": "available", "description": "Dev & test environment"},
    {"id": 601, "campus_id": 6, "lab_name": "Biomedical Lab", "location": "Fengtai Lab Bldg 201", "capacity": 25,
     "open_time": "08:00", "close_time": "20:00", "status": "available", "description": "Cell culture & PCR"},
    {"id": 602, "campus_id": 6, "lab_name": "Environmental Monitoring Lab", "location": "Fengtai Lab Bldg 305", "capacity": 20,
     "open_time": "08:30", "close_time": "21:00", "status": "available", "description": "Water/air/soil testing"},
    {"id": 701, "campus_id": 7, "lab_name": "Marine Science Lab", "location": "Hainan Ocean Bldg 101", "capacity": 35,
     "open_time": "08:00", "close_time": "20:00", "status": "available", "description": "Marine ecology & resources"},
    {"id": 702, "campus_id": 7, "lab_name": "Tropical Agriculture Lab", "location": "Hainan Agri Bldg 202", "capacity": 30,
     "open_time": "08:00", "close_time": "20:00", "status": "available", "description": "Tropical crop breeding"},
]

USERS = [
    {"id": 1, "username": "admin", "real_name": "System Admin", "role": "system_admin", "campus_id": None,
     "phone": "13800000001", "email": "admin@lab.edu.cn"},
    {"id": 101, "username": "teacher1", "real_name": "HD Teacher 01", "role": "teacher", "campus_id": 5,
     "phone": "13800010001", "email": "hd_teacher01@lab.edu.cn"},
    {"id": 102, "username": "student1", "real_name": "HD Student 01", "role": "student", "campus_id": 5,
     "phone": "13800020001", "email": "hd_student01@lab.edu.cn"},
    {"id": 103, "username": "hd_labadmin_01", "real_name": "HD Lab Admin", "role": "lab_admin", "campus_id": 5,
     "phone": "13800030001", "email": "hd_labadmin@lab.edu.cn"},
    {"id": 104, "username": "hd_student_02", "real_name": "HD Student 02", "role": "student", "campus_id": 5,
     "phone": "13800020002", "email": "hd_student02@lab.edu.cn"},
    {"id": 105, "username": "hd_teacher_02", "real_name": "HD Teacher 02", "role": "teacher", "campus_id": 5,
     "phone": "13800010002", "email": "hd_teacher02@lab.edu.cn"},
    {"id": 201, "username": "ft_teacher_01", "real_name": "FT Teacher 01", "role": "teacher", "campus_id": 6,
     "phone": "13800011001", "email": "ft_teacher01@lab.edu.cn"},
    {"id": 202, "username": "ft_student_01", "real_name": "FT Student 01", "role": "student", "campus_id": 6,
     "phone": "13800021001", "email": "ft_student01@lab.edu.cn"},
    {"id": 203, "username": "ft_labadmin_01", "real_name": "FT Lab Admin", "role": "lab_admin", "campus_id": 6,
     "phone": "13800031001", "email": "ft_labadmin@lab.edu.cn"},
    {"id": 204, "username": "ft_student_02", "real_name": "FT Student 02", "role": "student", "campus_id": 6,
     "phone": "13800021002", "email": "ft_student02@lab.edu.cn"},
    {"id": 301, "username": "hn_teacher_01", "real_name": "HN Teacher 01", "role": "teacher", "campus_id": 7,
     "phone": "13800012001", "email": "hn_teacher01@lab.edu.cn"},
    {"id": 302, "username": "hn_student_01", "real_name": "HN Student 01", "role": "student", "campus_id": 7,
     "phone": "13800022001", "email": "hn_student01@lab.edu.cn"},
    {"id": 303, "username": "hn_labadmin_01", "real_name": "HN Lab Admin", "role": "lab_admin", "campus_id": 7,
     "phone": "13800032001", "email": "hn_labadmin@lab.edu.cn"},
    {"id": 304, "username": "hn_student_02", "real_name": "HN Student 02", "role": "student", "campus_id": 7,
     "phone": "13800022002", "email": "hn_student02@lab.edu.cn"},
]


def _write_user(session, u):
    row = session.get(User, u["id"])
    if not row:
        row = User(id=u["id"])
        session.add(row)
    row.username = u["username"]
    if not row.password_hash:
        row.set_password(DEFAULT_PASSWORD)
    row.real_name = u["real_name"]
    row.phone = u.get("phone") or ""
    row.email = u.get("email") or ""
    row.role = u["role"]
    row.campus_id = u.get("campus_id")
    row.status = "active"


def _write_campus(session, c):
    row = session.get(Campus, c["id"])
    if not row:
        row = Campus(id=c["id"])
        session.add(row)
    row.campus_name = c["campus_name"]
    row.address = c.get("address") or ""
    row.description = c.get("description") or ""
    row.status = c.get("status") or "active"


def _write_lab(session, lab):
    row = session.get(Laboratory, lab["id"])
    if not row:
        row = Laboratory(id=lab["id"])
        session.add(row)
    row.campus_id = lab["campus_id"]
    row.lab_name = lab["lab_name"]
    row.location = lab.get("location") or ""
    row.capacity = lab.get("capacity") or 30
    row.open_time = lab.get("open_time") or "08:00"
    row.close_time = lab.get("close_time") or "22:00"
    row.status = lab.get("status") or "available"
    row.description = lab.get("description") or ""


def main():
    app = create_app()
    with app.app_context():
        campus_map_raw = app.config.get("CAMPUS_DB_URI_MAP", "")
        try:
            campus_map = json.loads(str(campus_map_raw))
            campus_ids = sorted(int(k) for k in campus_map.keys())
        except Exception:
            raise RuntimeError("CAMPUS_DB_URI_MAP config invalid")

        if not campus_ids:
            raise RuntimeError("CAMPUS_DB_URI_MAP not configured")

        summary_uri = str(app.config.get("SUMMARY_DB_URL") or "").strip()

        # Step 1: Write all data to summary DB (used for auth & global queries)
        if summary_uri:
            with summary_db_session() as session:
                for c in CAMPUSES:
                    _write_campus(session, c)
                session.flush()
                for lab in LABS:
                    _write_lab(session, lab)
                session.flush()
                for u in USERS:
                    _write_user(session, u)
                session.flush()
                budget = session.query(GlobalAssetBudget).first()
                if not budget:
                    budget = GlobalAssetBudget(
                        total_amount=200000, locked_amount=0, used_amount=0,
                        remark="seed global budget",
                    )
                    session.add(budget)
                elif float(budget.total_amount or 0) <= 0:
                    budget.total_amount = 200000
                session.commit()
                print(f"[OK] Summary DB: campuses={len(CAMPUSES)} labs={len(LABS)} users={len(USERS)} budget_total=200000")
        else:
            print("[WARN] SUMMARY_DB_URL not configured, skip summary DB")

        # Step 2: Clone campus-specific data to each campus DB
        for campus_id in campus_ids:
            campus_labs = [lab for lab in LABS if lab["campus_id"] == campus_id]
            campus_users = [
                u for u in USERS
                if u["role"] == "system_admin" or u["campus_id"] == campus_id
            ]
            campus_info = next((c for c in CAMPUSES if c["id"] == campus_id), None)

            with campus_db_session(campus_id) as session:
                try:
                    if campus_info:
                        _write_campus(session, campus_info)
                    session.flush()
                    for lab in campus_labs:
                        _write_lab(session, lab)
                    session.flush()
                    for u in campus_users:
                        _write_user(session, u)
                    session.commit()
                    print(f"[OK] Campus {campus_id}: campus=1 labs={len(campus_labs)} users={len(campus_users)}")
                except Exception:
                    session.rollback()
                    raise

        print("[DONE] Seed data complete")


if __name__ == "__main__":
    main()
