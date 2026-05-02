import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import AssetItem, AssetPurchaseRequest, Laboratory, User
from app.services.asset_service import META_FLAG
from app.services.db_router_service import campus_db_session, get_routed_campus_ids, summary_db_session
from app.services.summary_sync_service import sync_campus_summary_snapshots


CATEGORY_POOL = [
    "网络设备",
    "计算设备",
    "实验耗材",
    "测量仪器",
    "存储设备",
    "显示设备",
]

ASSET_NAME_POOL = [
    "交换机",
    "路由器",
    "服务器",
    "图形工作站",
    "示波器",
    "多功能电源",
    "固态存储阵列",
    "高精度传感器",
]

SPEC_POOL = [
    "H3C S5120V3",
    "Cisco C9300",
    "Dell R760",
    "Lenovo P620",
    "Rigol DS1104",
    "Keysight E36313A",
    "Synology SA3400",
]

MANUFACTURER_POOL = ["H3C", "Cisco", "Dell", "Lenovo", "Rigol", "Keysight", "Synology", "华为"]
LOCATION_POOL = ["理工楼305", "理工楼402", "综合楼B-211", "实验中心501", "创新楼8层", "机房A区"]
STATUS_POOL = ["in_use", "spare", "repair"]
STATUS_WEIGHTS = [0.72, 0.2, 0.08]


def _parse_args():
    parser = argparse.ArgumentParser(description="Seed asset purchase requests and stocked assets")
    parser.add_argument("--requests", type=int, default=200, help="how many request rows to insert")
    parser.add_argument("--assets", type=int, default=200, help="how many asset rows to insert")
    parser.add_argument("--seed", type=int, default=20260502, help="random seed")
    return parser.parse_args()


def _split_count(total, parts):
    if parts <= 0:
        return []
    base = total // parts
    remain = total % parts
    counts = [base] * parts
    for i in range(remain):
        counts[i] += 1
    return counts


def _campus_ids():
    routed = get_routed_campus_ids()
    return routed if routed else [0]


def _load_user_ids(campus_id, roles):
    def _query(session):
        rows = (
            session.query(User)
            .filter(
                User.status == "active",
                User.role.in_(roles),
                ((User.campus_id == campus_id) | (User.role == "system_admin")),
            )
            .all()
        )
        return [int(row.id) for row in rows]

    try:
        with summary_db_session() as session:
            values = _query(session)
            if values:
                return values
    except Exception:
        pass

    values = _query(db.session)
    return values


def _load_teacher_ids(campus_id):
    def _query(session):
        rows = (
            session.query(User)
            .filter(User.status == "active", User.role == "teacher", User.campus_id == campus_id)
            .all()
        )
        return [int(row.id) for row in rows]

    try:
        with summary_db_session() as session:
            values = _query(session)
            if values:
                return values
    except Exception:
        pass

    return _query(db.session)


def _load_labs(campus_id):
    with campus_db_session(campus_id) as session:
        return session.query(Laboratory).all()


def _build_request_no(campus_id, seq):
    # Example: AR00520260502141023560012
    return f"AR{int(campus_id):03d}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{int(seq):04d}"


def _build_asset_code(campus_id, seq):
    # Example: AS00520260502141023990021
    return f"AS{int(campus_id):03d}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{int(seq):04d}"


def _random_amount():
    quantity = random.randint(1, 4)
    unit_price = Decimal(str(random.choice([799, 1299, 2499, 3999, 6999, 9999, 14999]))).quantize(Decimal("0.01"))
    amount = (unit_price * Decimal(quantity)).quantize(Decimal("0.01"))
    return quantity, unit_price, amount


def _build_asset_description():
    spec = random.choice(SPEC_POOL)
    manufacturer = random.choice(MANUFACTURER_POOL)
    storage_location = random.choice(LOCATION_POOL)
    payload = {
        "spec_model": spec,
        "manufacturer": manufacturer,
        "storage_location": storage_location,
    }
    return f"批量导入测试资产\n{META_FLAG}{json.dumps(payload, ensure_ascii=False)}"


def _insert_for_campus(campus_id, req_count, asset_count, start_seq):
    labs = _load_labs(campus_id)
    if not labs:
        return 0, 0, start_seq

    requester_ids = _load_teacher_ids(campus_id)
    if not requester_ids:
        raise RuntimeError(f"campus={campus_id} 未找到教师账号，无法生成资产申报")

    reviewer_ids = _load_user_ids(campus_id, ["lab_admin", "system_admin"])
    if not reviewer_ids:
        raise RuntimeError(f"campus={campus_id} 未找到管理员账号，无法生成审批记录")

    inserted_req = 0
    inserted_assets = 0
    seq = start_seq

    with campus_db_session(campus_id) as session:
        for i in range(req_count):
            lab = random.choice(labs)
            requester_id = random.choice(requester_ids)
            reviewer_id = random.choice(reviewer_ids)
            quantity, unit_price, amount = _random_amount()
            category = random.choice(CATEGORY_POOL)
            asset_name = random.choice(ASSET_NAME_POOL)
            created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

            should_stock = inserted_assets < asset_count
            status = "approved" if should_stock else random.choice(["pending", "approved", "rejected"])

            seq += 1
            req_row = AssetPurchaseRequest(
                request_no=_build_request_no(campus_id, seq),
                campus_id=campus_id,
                lab_id=lab.id,
                requester_id=requester_id,
                asset_name=asset_name,
                category=category,
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
                reason=f"教学科研补充采购（批量导入 #{seq}）",
                status=status,
                reviewer_id=reviewer_id if status in {"approved", "rejected"} else None,
                review_remark=("批量导入：审核通过" if status == "approved" else "批量导入：审核驳回" if status == "rejected" else ""),
                reviewed_at=(created_at + timedelta(hours=random.randint(1, 6))) if status in {"approved", "rejected"} else None,
            )
            req_row.created_at = created_at
            req_row.updated_at = created_at
            session.add(req_row)
            session.flush()
            inserted_req += 1

            if should_stock:
                seq += 1
                asset_row = AssetItem(
                    asset_code=_build_asset_code(campus_id, seq),
                    campus_id=campus_id,
                    lab_id=lab.id,
                    request_id=req_row.id,
                    asset_name=req_row.asset_name,
                    category=req_row.category,
                    price=req_row.amount,
                    status=random.choices(STATUS_POOL, weights=STATUS_WEIGHTS, k=1)[0],
                    description=_build_asset_description(),
                )
                asset_row.created_at = created_at + timedelta(hours=random.randint(1, 12))
                asset_row.updated_at = asset_row.created_at
                session.add(asset_row)
                inserted_assets += 1

        session.commit()

    return inserted_req, inserted_assets, seq


def main():
    args = _parse_args()
    if args.requests <= 0 or args.assets <= 0:
        raise ValueError("--requests 和 --assets 必须大于 0")

    random.seed(args.seed)
    app = create_app()
    with app.app_context():
        campus_ids = _campus_ids()
        valid_campus_ids = [cid for cid in campus_ids if _load_labs(cid)]
        if not valid_campus_ids:
            raise RuntimeError("未找到可用校区实验室，无法插入资产数据")

        req_dist = _split_count(args.requests, len(valid_campus_ids))
        asset_dist = _split_count(args.assets, len(valid_campus_ids))
        total_req = 0
        total_assets = 0
        seq = 0

        for idx, campus_id in enumerate(valid_campus_ids):
            req_count = req_dist[idx]
            asset_count = asset_dist[idx]
            inserted_req, inserted_assets, seq = _insert_for_campus(campus_id, req_count, asset_count, seq)
            total_req += inserted_req
            total_assets += inserted_assets
            print(
                f"[OK] campus={campus_id} inserted_requests={inserted_req} inserted_assets={inserted_assets}"
            )

        summary = sync_campus_summary_snapshots()
        totals = summary.get("totals") or {}
        print(f"[DONE] requests={total_req} assets={total_assets}")
        print(
            "[TOTAL] asset_requests={asset_request_count}, asset_items={asset_item_count}, daily_reports={daily_report_count}".format(
                asset_request_count=totals.get("asset_request_count", 0),
                asset_item_count=totals.get("asset_item_count", 0),
                daily_report_count=totals.get("daily_report_count", 0),
            )
        )


if __name__ == "__main__":
    main()
