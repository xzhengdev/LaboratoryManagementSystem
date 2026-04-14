import os
import sys
from datetime import date, time, timedelta


CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    # 允许直接 python scripts/seed.py 运行，而不依赖外部设置 PYTHONPATH。
    sys.path.insert(0, BACKEND_ROOT)


from app import create_app
from app.extensions import db
from app.models import Campus, Equipment, Laboratory, Reservation, User


def add_user(username, password, real_name, role, campus_id=None):
    # 幂等地创建测试用户：
    # 如果已存在同名账号，则直接返回现有用户。
    user = User.query.filter_by(username=username).first()
    if user:
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


def seed_data():
    # 初始化数据库和演示数据。
    app = create_app()
    with app.app_context():
        db.create_all()

        # 如果已有两条校区数据，说明种子数据已经初始化过，直接返回。
        if Campus.query.count() >= 2:
            return

        # 1. 创建校区
        campus_a = Campus(
            campus_name="主校区",
            address="南京市江宁区示范路 1 号",
            description="承担综合实验教学与科研协作",
            status="active",
        )
        campus_b = Campus(
            campus_name="创新校区",
            address="南京市浦口区创新大道 88 号",
            description="面向跨校区联合实验与项目孵化",
            status="active",
        )
        db.session.add_all([campus_a, campus_b])
        db.session.flush()

        # 2. 创建实验室
        labs = [
            Laboratory(
                campus_id=campus_a.id,
                lab_name="A101 电子设计实验室",
                location="主楼 A101",
                capacity=32,
                open_time=time(8, 0),
                close_time=time(21, 0),
                description="适用于单片机、嵌入式实验",
                status="active",
            ),
            Laboratory(
                campus_id=campus_a.id,
                lab_name="A203 物联网实验室",
                location="主楼 A203",
                capacity=28,
                open_time=time(8, 30),
                close_time=time(20, 30),
                description="支持传感器与物联网网关实验",
                status="active",
            ),
            Laboratory(
                campus_id=campus_b.id,
                lab_name="B305 AI 联合实验室",
                location="创新楼 B305",
                capacity=40,
                open_time=time(9, 0),
                close_time=time(22, 0),
                description="跨校区 AI 训练与演示环境",
                status="active",
            ),
            Laboratory(
                campus_id=campus_b.id,
                lab_name="B402 网络安全实验室",
                location="创新楼 B402",
                capacity=24,
                open_time=time(8, 0),
                close_time=time(21, 30),
                description="适合网络攻防与安全测试演示",
                status="active",
            ),
        ]
        db.session.add_all(labs)
        db.session.flush()

        # 3. 创建设备
        db.session.add_all(
            [
                Equipment(lab_id=labs[0].id, equipment_name="示波器", quantity=12, status="active"),
                Equipment(lab_id=labs[0].id, equipment_name="单片机开发板", quantity=30, status="active"),
                Equipment(lab_id=labs[1].id, equipment_name="IoT 网关", quantity=8, status="active"),
                Equipment(lab_id=labs[2].id, equipment_name="GPU 工作站", quantity=10, status="active"),
                Equipment(lab_id=labs[3].id, equipment_name="安全靶机", quantity=15, status="active"),
            ]
        )

        # 4. 创建四类角色账号
        student = add_user("student1", "123456", "张同学", "student", campus_a.id)
        teacher = add_user("teacher1", "123456", "李老师", "teacher", campus_a.id)
        add_user("labadmin1", "123456", "实验室管理员", "lab_admin", campus_a.id)
        add_user("admin1", "123456", "系统管理员", "system_admin")
        db.session.flush()

        # 5. 创建两条演示预约数据
        db.session.add_all(
            [
                Reservation(
                    user_id=student.id,
                    campus_id=campus_a.id,
                    lab_id=labs[0].id,
                    reservation_date=date.today() + timedelta(days=1),
                    start_time=time(9, 0),
                    end_time=time(11, 0),
                    purpose="嵌入式课程实验",
                    participant_count=12,
                    status="pending",
                    need_approval=True,
                ),
                Reservation(
                    user_id=teacher.id,
                    campus_id=campus_a.id,
                    lab_id=labs[1].id,
                    reservation_date=date.today() + timedelta(days=2),
                    start_time=time(14, 0),
                    end_time=time(16, 0),
                    purpose="物联网项目答辩演示",
                    participant_count=20,
                    status="approved",
                    need_approval=True,
                ),
            ]
        )
        db.session.commit()


if __name__ == "__main__":
    # 允许直接执行本文件完成演示数据初始化。
    seed_data()
