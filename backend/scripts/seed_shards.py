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
    {"id": 5, "campus_name": "中央民族大学海淀校区", "address": "北京市海淀区中关村南大街27号",
     "description": "主校区：计算机科学、电子工程、自动化等理工科实验室", "status": "active"},
    {"id": 6, "campus_name": "中央民族大学丰台校区", "address": "北京市丰台区花乡",
     "description": "分校区：生物医学、环境科学、材料科学等实验室", "status": "active"},
    {"id": 7, "campus_name": "中央民族大学海南校区", "address": "海南省陵水黎族自治县黎安镇",
     "description": "国际校区：海洋科学、热带农业、生态保护等实验室", "status": "active"},
]

LABS = [
    # 海淀校区 — 7个实验室
    {"id": 501, "campus_id": 5, "lab_name": "计算机网络实验室", "location": "理工楼A座302",
     "capacity": 40, "open_time": "08:00", "close_time": "22:00", "status": "available",
     "description": "思科路由交换、网络协议分析与仿真实验"},
    {"id": 502, "campus_id": 5, "lab_name": "人工智能实验室", "location": "理工楼B座101",
     "capacity": 30, "open_time": "08:30", "close_time": "21:30", "status": "available",
     "description": "GPU服务器集群，深度学习与大模型训练平台"},
    {"id": 503, "campus_id": 5, "lab_name": "软件工程实验室", "location": "理工楼C座205",
     "capacity": 50, "open_time": "08:00", "close_time": "22:00", "status": "available",
     "description": "软件开发、测试与持续集成实验环境"},
    {"id": 504, "campus_id": 5, "lab_name": "电子电路实验室", "location": "理工楼A座105",
     "capacity": 35, "open_time": "08:00", "close_time": "21:00", "status": "available",
     "description": "模拟电路、数字电路与嵌入式系统实验"},
    {"id": 505, "campus_id": 5, "lab_name": "自动化控制实验室", "location": "理工楼B座208",
     "capacity": 30, "open_time": "08:00", "close_time": "21:00", "status": "available",
     "description": "PLC控制、机器人技术与自动化系统实验"},
    {"id": 506, "campus_id": 5, "lab_name": "大数据与云计算实验室", "location": "理工楼C座310",
     "capacity": 35, "open_time": "08:30", "close_time": "22:00", "status": "available",
     "description": "Hadoop/Spark集群，分布式计算与数据挖掘平台"},
    {"id": 507, "campus_id": 5, "lab_name": "信息安全实验室", "location": "理工楼A座401",
     "capacity": 25, "open_time": "08:00", "close_time": "22:00", "status": "available",
     "description": "网络安全攻防、密码学与信息隐藏实验"},
    # 丰台校区 — 6个实验室
    {"id": 601, "campus_id": 6, "lab_name": "生物医学实验室", "location": "实验楼A座201",
     "capacity": 25, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "细胞培养、PCR扩增与蛋白质分析实验"},
    {"id": 602, "campus_id": 6, "lab_name": "环境监测实验室", "location": "实验楼B座305",
     "capacity": 20, "open_time": "08:30", "close_time": "21:00", "status": "available",
     "description": "水质、大气、土壤污染物检测与分析"},
    {"id": 603, "campus_id": 6, "lab_name": "材料科学实验室", "location": "实验楼A座102",
     "capacity": 20, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "纳米材料制备、表征与性能测试平台"},
    {"id": 604, "campus_id": 6, "lab_name": "细胞培养实验室", "location": "实验楼B座108",
     "capacity": 15, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "无菌细胞培养、显微观察与细胞分析"},
    {"id": 605, "campus_id": 6, "lab_name": "分子生物学实验室", "location": "实验楼A座310",
     "capacity": 20, "open_time": "08:30", "close_time": "21:00", "status": "available",
     "description": "基因克隆、电泳分离与分子杂交实验"},
    {"id": 606, "campus_id": 6, "lab_name": "化学分析实验室", "location": "实验楼B座202",
     "capacity": 25, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "色谱分析、光谱分析与电化学测试"},
    # 海南校区 — 6个实验室
    {"id": 701, "campus_id": 7, "lab_name": "海洋科学实验室", "location": "海洋楼A座101",
     "capacity": 35, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "海洋生态环境监测与资源评估"},
    {"id": 702, "campus_id": 7, "lab_name": "热带农业实验室", "location": "农业楼B座202",
     "capacity": 30, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "热带作物栽培、育种与病虫害防治研究"},
    {"id": 703, "campus_id": 7, "lab_name": "海洋生态实验室", "location": "海洋楼A座205",
     "capacity": 25, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "珊瑚礁生态、海洋生物多样性研究"},
    {"id": 704, "campus_id": 7, "lab_name": "热带作物育种实验室", "location": "农业楼B座308",
     "capacity": 20, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "分子标记辅助育种与种子资源创新"},
    {"id": 705, "campus_id": 7, "lab_name": "海洋资源开发实验室", "location": "海洋楼A座310",
     "capacity": 25, "open_time": "08:30", "close_time": "21:00", "status": "available",
     "description": "海洋药物、海洋功能食品开发与研究"},
    {"id": 706, "campus_id": 7, "lab_name": "生态保护实验室", "location": "农业楼B座105",
     "capacity": 30, "open_time": "08:00", "close_time": "20:00", "status": "available",
     "description": "热带雨林生态、湿地保护与生物多样性"},
]

USERS = [
    {"id": 1, "username": "20150001", "real_name": "系统管理员", "role": "system_admin", "campus_id": None,
     "phone": "13800000001", "email": "admin@muc.edu.cn"},
    # 海淀校区
    {"id": 101, "username": "20210001", "real_name": "张明远", "role": "teacher", "campus_id": 5,
     "phone": "13800010001", "email": "zhangmingyuan@muc.edu.cn"},
    {"id": 102, "username": "22140166", "real_name": "李华", "role": "student", "campus_id": 5,
     "phone": "13800020001", "email": "lihua@muc.edu.cn"},
    {"id": 103, "username": "20180001", "real_name": "王建民", "role": "lab_admin", "campus_id": 5,
     "phone": "13800030001", "email": "wangjianmin@muc.edu.cn"},
    {"id": 104, "username": "22140167", "real_name": "刘思雨", "role": "student", "campus_id": 5,
     "phone": "13800020002", "email": "liusiyu@muc.edu.cn"},
    {"id": 105, "username": "20210002", "real_name": "陈晓燕", "role": "teacher", "campus_id": 5,
     "phone": "13800010002", "email": "chenxiaoyan@muc.edu.cn"},
    # 丰台校区
    {"id": 201, "username": "20210011", "real_name": "赵国栋", "role": "teacher", "campus_id": 6,
     "phone": "13800011001", "email": "zhaoguodong@muc.edu.cn"},
    {"id": 202, "username": "22140201", "real_name": "周文杰", "role": "student", "campus_id": 6,
     "phone": "13800021001", "email": "zhouwenjie@muc.edu.cn"},
    {"id": 203, "username": "20180011", "real_name": "孙立新", "role": "lab_admin", "campus_id": 6,
     "phone": "13800031001", "email": "sunlixin@muc.edu.cn"},
    {"id": 204, "username": "22140202", "real_name": "吴雨桐", "role": "student", "campus_id": 6,
     "phone": "13800021002", "email": "wuyutong@muc.edu.cn"},
    # 海南校区
    {"id": 301, "username": "20210021", "real_name": "杨海涛", "role": "teacher", "campus_id": 7,
     "phone": "13800012001", "email": "yanghaitao@muc.edu.cn"},
    {"id": 302, "username": "22140301", "real_name": "黄思颖", "role": "student", "campus_id": 7,
     "phone": "13800022001", "email": "huangsiying@muc.edu.cn"},
    {"id": 303, "username": "20180021", "real_name": "林志强", "role": "lab_admin", "campus_id": 7,
     "phone": "13800032001", "email": "linzhiqiang@muc.edu.cn"},
    {"id": 304, "username": "22140302", "real_name": "马晓彤", "role": "student", "campus_id": 7,
     "phone": "13800022002", "email": "maxiaotong@muc.edu.cn"},
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

        # Step 1: Write auth/global data to summary DB (users, campuses, global budget only)
        if summary_uri:
            with summary_db_session() as session:
                for c in CAMPUSES:
                    _write_campus(session, c)
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
                print(f"[OK] Summary DB: campuses={len(CAMPUSES)} users={len(USERS)} budget_total=200000")
        else:
            print("[WARN] SUMMARY_DB_URL not configured, skip summary DB")

        # Step 2: Clone campus-specific data to each campus DB (labs only, users stay in summary)
        for campus_id in campus_ids:
            campus_labs = [lab for lab in LABS if lab["campus_id"] == campus_id]
            campus_info = next((c for c in CAMPUSES if c["id"] == campus_id), None)

            with campus_db_session(campus_id) as session:
                try:
                    if campus_info:
                        _write_campus(session, campus_info)
                    session.flush()
                    for lab in campus_labs:
                        _write_lab(session, lab)
                    session.commit()
                    print(f"[OK] Campus {campus_id}: campus=1 labs={len(campus_labs)}")
                except Exception:
                    session.rollback()
                    raise

        print("[DONE] Seed data complete")


if __name__ == "__main__":
    main()
