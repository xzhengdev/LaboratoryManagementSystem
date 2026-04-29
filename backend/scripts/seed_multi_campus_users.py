import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import User
from scripts.seed_shards import main as sync_shards_main


DEFAULT_PASSWORD = "123456"


USER_PRESETS = [
    # campus 5
    {"username": "hd_student_01", "real_name": "海淀学生01", "role": "student", "campus_id": 5},
    {"username": "hd_student_02", "real_name": "海淀学生02", "role": "student", "campus_id": 5},
    {"username": "hd_teacher_01", "real_name": "海淀教师01", "role": "teacher", "campus_id": 5},
    {"username": "hd_labadmin_01", "real_name": "海淀实验室管理员", "role": "lab_admin", "campus_id": 5},
    # campus 6
    {"username": "ft_student_01", "real_name": "丰台学生01", "role": "student", "campus_id": 6},
    {"username": "ft_student_02", "real_name": "丰台学生02", "role": "student", "campus_id": 6},
    {"username": "ft_teacher_01", "real_name": "丰台教师01", "role": "teacher", "campus_id": 6},
    {"username": "ft_labadmin_01", "real_name": "丰台实验室管理员", "role": "lab_admin", "campus_id": 6},
    # campus 7
    {"username": "hn_student_01", "real_name": "海南学生01", "role": "student", "campus_id": 7},
    {"username": "hn_student_02", "real_name": "海南学生02", "role": "student", "campus_id": 7},
    {"username": "hn_teacher_01", "real_name": "海南教师01", "role": "teacher", "campus_id": 7},
    {"username": "hn_labadmin_01", "real_name": "海南实验室管理员", "role": "lab_admin", "campus_id": 7},
]


def upsert_user(row):
    username = row["username"]
    item = User.query.filter_by(username=username).first()
    if not item:
        item = User(username=username)
        db.session.add(item)
    item.real_name = row["real_name"]
    item.role = row["role"]
    item.campus_id = row["campus_id"]
    item.status = "active"
    item.phone = item.phone or "13800000000"
    item.email = item.email or f"{username}@example.com"
    item.set_password(DEFAULT_PASSWORD)
    return item


def main():
    app = create_app()
    with app.app_context():
        for row in USER_PRESETS:
            upsert_user(row)
        db.session.commit()
        print(f"[OK] 默认库用户已写入/更新: {len(USER_PRESETS)}")

    # 复用现有分库同步脚本：把默认库中的校区用户和 system_admin 同步到分库
    sync_shards_main()
    print("[DONE] 多校区用户种子完成")


if __name__ == "__main__":
    main()

