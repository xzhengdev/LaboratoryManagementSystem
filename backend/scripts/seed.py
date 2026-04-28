import os
import sys
from datetime import date, time, timedelta


CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    # Allow running `python scripts/seed.py` directly.
    sys.path.insert(0, BACKEND_ROOT)


from app import create_app
from app.extensions import db
from app.models import (
    Approval,
    Campus,
    Equipment,
    IdempotencyRecord,
    Laboratory,
    Reservation,
    User,
)


LEGACY_CAMPUS_NAMES = {
    "主校区",
    "创新校区",
    "中央民族大学（海淀）",
    "中央民族大学（丰台）",
    "中央民族大学（海南）",
}
LEGACY_LAB_NAMES = {
    "A101 电子设计实验室",
    "A203 物联网实验室",
    "B305 AI 联合实验室",
    "B402 网络安全实验室",
    "海淀校区 A305 智能制造实验室",
    "丰台校区 B305 AI联合实验室",
    "丰台校区 B402 网络安全实验室",
    "丰台校区 B208 数据可视化实验室",
    "海南校区 C201 生物信息实验室",
    "海南校区 C305 新能源材料实验室",
}


CAMPUS_DEFINITIONS = [
    {
        "campus_name": "海淀校区",
        "address": "北京市海淀区中关村南大街27号",
        "description": "校本部，聚焦基础学科与重点科研平台。",
        "status": "active",
    },
    {
        "campus_name": "丰台校区",
        "address": "北京市丰台区魏各庄路27号",
        "description": "新校区，建设有多类虚拟仿真实验教学空间。",
        "status": "active",
    },
    {
        "campus_name": "海南校区",
        "address": "海南省陵水黎安国际教育创新试验区",
        "description": "海南国际学院所在地，建设校企合作与创新创业实验空间。",
        "status": "active",
    },
]


LAB_DEFINITIONS = [
    {
        "campus": "海淀校区",
        "lab_name": "民族语言智能分析与安全治理教育部重点实验室",
        "location": "理工楼",
        "capacity": 60,
        "open_time": time(8, 0),
        "close_time": time(22, 0),
        "description": "聚焦民族语言智能处理与网络安全治理。",
        "status": "active",
        "equipment": [
            ("GPU 服务器", 8),
            ("多模态语料采集终端", 20),
            ("网络安全实验工作站", 24),
        ],
    },
    {
        "campus": "海淀校区",
        "lab_name": "民族医药教育部重点实验室",
        "location": "药学院二层至四层",
        "capacity": 45,
        "open_time": time(8, 30),
        "close_time": time(21, 0),
        "description": "围绕民族医药理论挖掘、民族药研发与资源可持续利用。",
        "status": "active",
        "equipment": [
            ("液相色谱仪", 6),
            ("气相色谱质谱联用仪", 4),
            ("细胞培养工作站", 10),
        ],
    },
    {
        "campus": "海淀校区",
        "lab_name": "化学实验教学中心",
        "location": "理工楼10层",
        "capacity": 50,
        "open_time": time(8, 0),
        "close_time": time(20, 30),
        "description": "国家级实验教学示范中心建设单位，承担化学基础与专业实验教学。",
        "status": "active",
        "equipment": [
            ("通风橱", 30),
            ("分光光度计", 20),
            ("化学实验台", 50),
        ],
    },
    {
        "campus": "丰台校区",
        "lab_name": "共享基础虚拟仿真实验室",
        "location": "少数民族艺术教育楼",
        "capacity": 80,
        "open_time": time(9, 0),
        "close_time": time(22, 0),
        "description": "支持桌面VR、PICO与LED曲面屏协同教学。",
        "status": "active",
        "equipment": [
            ("PICO VR 头显", 40),
            ("桌面 VR 工作站", 30),
            ("LED 曲面屏系统", 1),
        ],
    },
    {
        "campus": "丰台校区",
        "lab_name": "沉浸式虚拟仿真实验室",
        "location": "少数民族艺术教育楼",
        "capacity": 60,
        "open_time": time(9, 0),
        "close_time": time(22, 0),
        "description": "支持动捕实训、CAVE沉浸式教学与3D场景演示。",
        "status": "active",
        "equipment": [
            ("动捕系统", 2),
            ("CAVE 投影系统", 1),
            ("3D 教学显示系统", 2),
        ],
    },
    {
        "campus": "丰台校区",
        "lab_name": "专业研创虚拟仿真实验中心",
        "location": "少数民族艺术教育楼",
        "capacity": 70,
        "open_time": time(9, 0),
        "close_time": time(22, 0),
        "description": "面向多学科虚拟研创与多人协同开发。",
        "status": "active",
        "equipment": [
            ("MR 头戴设备", 20),
            ("触控教学大屏", 4),
            ("图形开发工作站", 40),
        ],
    },
    {
        "campus": "海南校区",
        "lab_name": "校企合作实验室",
        "location": "海南国际学院专享区二期",
        "capacity": 50,
        "open_time": time(9, 0),
        "close_time": time(21, 30),
        "description": "用于中外合作办学场景下的产教协同实验教学。",
        "status": "active",
        "equipment": [
            ("协同开发终端", 30),
            ("企业实训服务器", 6),
            ("混合教学录播设备", 2),
        ],
    },
    {
        "campus": "海南校区",
        "lab_name": "创新创业实验室/展厅",
        "location": "海南国际学院专享区二期",
        "capacity": 90,
        "open_time": time(9, 0),
        "close_time": time(21, 30),
        "description": "用于创新创业实践、项目展示与路演训练。",
        "status": "active",
        "equipment": [
            ("路演演示屏", 3),
            ("移动实验终端", 40),
            ("创客工具套件", 25),
        ],
    },
    {
        "campus": "海南校区",
        "lab_name": "大数据学院研究室",
        "location": "海南国际学院专享区二期",
        "capacity": 45,
        "open_time": time(9, 0),
        "close_time": time(21, 30),
        "description": "支撑大数据方向教学科研与联合课题实践。",
        "status": "active",
        "equipment": [
            ("数据分析服务器", 8),
            ("高性能工作站", 24),
            ("存储阵列", 2),
        ],
    },
]


DEMO_RESERVATIONS = [
    {
        "username": "student1",
        "lab_name": "化学实验教学中心",
        "offset_days": 1,
        "start": time(9, 0),
        "end": time(11, 0),
        "purpose": "化学课程实验",
        "participant_count": 16,
        "status": "pending",
    },
    {
        "username": "teacher1",
        "lab_name": "共享基础虚拟仿真实验室",
        "offset_days": 2,
        "start": time(14, 0),
        "end": time(16, 0),
        "purpose": "虚拟仿真教学演练",
        "participant_count": 30,
        "status": "approved",
    },
]


def add_or_update_user(username, password, real_name, role, campus_id=None):
    """Create or update a demo account."""
    user = User.query.filter_by(username=username).first()
    if user:
        user.real_name = real_name
        user.role = role
        user.campus_id = campus_id
        user.status = "active"
        user.phone = user.phone or "13800000000"
        user.email = user.email or f"{username}@example.com"
        user.set_password(password)
        return user

    user = User(
        username=username,
        real_name=real_name,
        role=role,
        campus_id=campus_id,
        status="active",
        phone="13800000000",
        email=f"{username}@example.com",
    )
    user.set_password(password)
    db.session.add(user)
    return user


def upsert_campus(item):
    campus = Campus.query.filter_by(campus_name=item["campus_name"]).first()
    if not campus:
        campus = Campus(**item)
        db.session.add(campus)
    else:
        campus.address = item["address"]
        campus.description = item["description"]
        campus.status = item["status"]
    return campus


def clear_legacy_demo_data():
    """Remove old two-campus demo data (主校区/创新校区) and legacy labs."""
    legacy_campuses = Campus.query.filter(Campus.campus_name.in_(LEGACY_CAMPUS_NAMES)).all()
    legacy_campus_ids = [item.id for item in legacy_campuses]

    legacy_labs = Laboratory.query.filter(Laboratory.lab_name.in_(LEGACY_LAB_NAMES)).all()
    legacy_lab_ids = [item.id for item in legacy_labs]

    if legacy_campus_ids:
        reservation_ids = [
            item.id
            for item in Reservation.query.filter(Reservation.campus_id.in_(legacy_campus_ids)).all()
        ]
        if reservation_ids:
            Approval.query.filter(Approval.reservation_id.in_(reservation_ids)).delete(
                synchronize_session=False
            )

        more_legacy_lab_ids = [
            item.id
            for item in Laboratory.query.filter(Laboratory.campus_id.in_(legacy_campus_ids)).all()
        ]
        legacy_lab_ids = list(set(legacy_lab_ids + more_legacy_lab_ids))

        User.query.filter(User.campus_id.in_(legacy_campus_ids)).update(
            {User.campus_id: None}, synchronize_session=False
        )
        Reservation.query.filter(Reservation.campus_id.in_(legacy_campus_ids)).delete(
            synchronize_session=False
        )

    if legacy_lab_ids:
        Equipment.query.filter(Equipment.lab_id.in_(legacy_lab_ids)).delete(synchronize_session=False)
        Reservation.query.filter(Reservation.lab_id.in_(legacy_lab_ids)).delete(synchronize_session=False)
        Laboratory.query.filter(Laboratory.id.in_(legacy_lab_ids)).delete(synchronize_session=False)

    if legacy_campus_ids:
        Campus.query.filter(Campus.id.in_(legacy_campus_ids)).delete(synchronize_session=False)



def seed_data():
    app = create_app()
    with app.app_context():
        db.create_all()

        clear_legacy_demo_data()

        campus_by_name = {}
        for item in CAMPUS_DEFINITIONS:
            campus = upsert_campus(item)
            campus_by_name[campus.campus_name] = campus
        db.session.flush()

        managed_lab_names = {item["lab_name"] for item in LAB_DEFINITIONS}
        all_managed_names = managed_lab_names.union(LEGACY_LAB_NAMES)

        existing_managed_labs = {
            lab.lab_name: lab
            for lab in Laboratory.query.filter(Laboratory.lab_name.in_(all_managed_names)).all()
        }

        seeded_labs = {}
        for item in LAB_DEFINITIONS:
            campus = campus_by_name[item["campus"]]
            lab = existing_managed_labs.get(item["lab_name"])
            if not lab:
                lab = Laboratory(lab_name=item["lab_name"])
                db.session.add(lab)

            lab.campus_id = campus.id
            lab.location = item["location"]
            lab.capacity = item["capacity"]
            lab.open_time = item["open_time"]
            lab.close_time = item["close_time"]
            lab.description = item["description"]
            lab.status = item["status"]
            seeded_labs[lab.lab_name] = lab

        db.session.flush()

        for lab_name in managed_lab_names:
            lab = seeded_labs[lab_name]
            Equipment.query.filter_by(lab_id=lab.id).delete(synchronize_session=False)

        equipment_rows = []
        for item in LAB_DEFINITIONS:
            lab = seeded_labs[item["lab_name"]]
            for eq_name, qty in item["equipment"]:
                equipment_rows.append(
                    Equipment(
                        lab_id=lab.id,
                        equipment_name=eq_name,
                        quantity=qty,
                        status="active",
                    )
                )
        db.session.add_all(equipment_rows)

        haidian_id = campus_by_name["海淀校区"].id
        student = add_or_update_user("student1", "123456", "张同学", "student", haidian_id)
        teacher = add_or_update_user("teacher1", "123456", "李老师", "teacher", haidian_id)
        add_or_update_user("labadmin1", "123456", "实验室管理员", "lab_admin", haidian_id)
        add_or_update_user("admin1", "123456", "系统管理员", "system_admin")
        db.session.flush()

        demo_lab_ids = [seeded_labs[item["lab_name"]].id for item in DEMO_RESERVATIONS]
        demo_user_ids = [student.id, teacher.id]
        stale_demo_reservation_ids = [
            item.id
            for item in Reservation.query.filter(Reservation.user_id.in_(demo_user_ids))
            .filter(Reservation.lab_id.in_(demo_lab_ids))
            .all()
        ]
        if stale_demo_reservation_ids:
            Approval.query.filter(Approval.reservation_id.in_(stale_demo_reservation_ids)).delete(
                synchronize_session=False
            )
            Reservation.query.filter(Reservation.id.in_(stale_demo_reservation_ids)).delete(
                synchronize_session=False
            )

        rows = []
        for item in DEMO_RESERVATIONS:
            lab = seeded_labs[item["lab_name"]]
            user = student if item["username"] == "student1" else teacher
            rows.append(
                Reservation(
                    user_id=user.id,
                    campus_id=lab.campus_id,
                    lab_id=lab.id,
                    reservation_date=date.today() + timedelta(days=item["offset_days"]),
                    start_time=item["start"],
                    end_time=item["end"],
                    purpose=item["purpose"],
                    participant_count=item["participant_count"],
                    status=item["status"],
                    need_approval=True,
                )
            )
        db.session.add_all(rows)
        IdempotencyRecord.query.delete(synchronize_session=False)

        db.session.commit()


if __name__ == "__main__":
    seed_data()
