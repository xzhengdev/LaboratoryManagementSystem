import argparse
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.models import AssetBudgetLedger, AssetItem, AssetPurchaseRequest, Laboratory, User
from app.services.db_router_service import campus_db_session, get_routed_campus_ids, summary_db_session
from app.services.summary_sync_service import sync_campus_summary_snapshots


def _parse_args():
    parser = argparse.ArgumentParser(description="Rebalance asset demo counts")
    parser.add_argument("--target-assets", type=int, default=100, help="target asset_items count")
    parser.add_argument("--target-unstocked", type=int, default=100, help="target request count not stocked in")
    parser.add_argument("--seed", type=int, default=20260502, help="random seed")
    return parser.parse_args()


def _campus_ids():
    routed = get_routed_campus_ids()
    return routed if routed else [0]


def _load_teachers(campus_id):
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
    return _query(User.query.session)


def _load_labs(campus_id):
    with campus_db_session(campus_id) as session:
        return session.query(Laboratory).all()


def _all_rows():
    assets = []
    requests = []
    for campus_id in _campus_ids():
        with campus_db_session(campus_id) as session:
            for row in session.query(AssetItem).all():
                assets.append(
                    {
                        "campus_id": campus_id,
                        "id": int(row.id),
                        "request_id": int(row.request_id) if row.request_id else None,
                        "created_at": row.created_at or datetime.min,
                    }
                )
            for row in session.query(AssetPurchaseRequest).all():
                requests.append(
                    {
                        "campus_id": campus_id,
                        "id": int(row.id),
                        "status": str(row.status or ""),
                        "reason": str(row.reason or ""),
                        "created_at": row.created_at or datetime.min,
                    }
                )
    return assets, requests


def _group_delete_assets(asset_rows):
    buckets = defaultdict(list)
    for row in asset_rows:
        buckets[int(row["campus_id"])].append(int(row["id"]))
    deleted = 0
    for campus_id, ids in buckets.items():
        with campus_db_session(campus_id) as session:
            for asset_id in ids:
                item = session.query(AssetItem).get(asset_id)
                if item:
                    session.delete(item)
                    deleted += 1
            session.commit()
    return deleted


def _group_delete_requests(req_rows):
    buckets = defaultdict(list)
    for row in req_rows:
        buckets[int(row["campus_id"])].append(int(row["id"]))
    deleted = 0
    for campus_id, ids in buckets.items():
        with campus_db_session(campus_id) as session:
            for request_id in ids:
                session.query(AssetBudgetLedger).filter_by(request_id=request_id).delete(synchronize_session=False)
                item = session.query(AssetPurchaseRequest).get(request_id)
                if item:
                    session.delete(item)
                    deleted += 1
            session.commit()
    return deleted


def _request_no(campus_id, seq):
    return f"AR{campus_id:03d}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{seq:04d}"


def _insert_unstocked_requests(deficit, seed):
    random.seed(seed + 1)
    campuses = []
    for campus_id in _campus_ids():
        labs = _load_labs(campus_id)
        teachers = _load_teachers(campus_id)
        if labs and teachers:
            campuses.append((campus_id, labs, teachers))
    if not campuses:
        raise RuntimeError("没有可用校区/实验室/教师，无法补齐未入库申报")

    inserted = 0
    seq = 1
    for i in range(deficit):
        campus_id, labs, teachers = campuses[i % len(campuses)]
        lab = random.choice(labs)
        teacher_id = random.choice(teachers)
        quantity = random.randint(1, 3)
        unit_price = Decimal(str(random.choice([1299, 2499, 3999, 6999]))).quantize(Decimal("0.01"))
        amount = (unit_price * Decimal(quantity)).quantize(Decimal("0.01"))
        created_at = datetime.utcnow()
        with campus_db_session(campus_id) as session:
            row = AssetPurchaseRequest(
                request_no=_request_no(campus_id, seq),
                campus_id=campus_id,
                lab_id=lab.id,
                requester_id=teacher_id,
                asset_name=random.choice(["交换机", "服务器", "示波器", "路由器"]),
                category=random.choice(["网络设备", "计算设备", "测量仪器"]),
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
                reason=f"演示补齐未入库申报 #{seq}",
                status="pending",
            )
            row.created_at = created_at
            row.updated_at = created_at
            session.add(row)
            session.commit()
        inserted += 1
        seq += 1
    return inserted


def _print_counts(tag):
    assets, requests = _all_rows()
    stocked_keys = {(int(a["campus_id"]), int(a["request_id"])) for a in assets if a.get("request_id")}
    unstocked = [r for r in requests if (int(r["campus_id"]), int(r["id"])) not in stocked_keys]
    print(f"[{tag}] requests={len(requests)} assets={len(assets)} unstocked_requests={len(unstocked)}")
    return len(requests), len(assets), len(unstocked)


def main():
    args = _parse_args()
    random.seed(args.seed)

    app = create_app()
    with app.app_context():
        _print_counts("BEFORE")
        assets, requests = _all_rows()

        # 1) shrink assets to target by deleting oldest first
        if len(assets) > args.target_assets:
            ordered_assets = sorted(assets, key=lambda x: (x["created_at"], x["id"]))
            to_delete_assets = ordered_assets[: len(assets) - args.target_assets]
            deleted_assets = _group_delete_assets(to_delete_assets)
            print(f"[STEP] deleted_assets={deleted_assets}")
        elif len(assets) < args.target_assets:
            print("[STEP] current assets less than target, skip shrink")

        # 2) recompute unstocked and fit to target
        assets, requests = _all_rows()
        stocked_keys = {(int(a["campus_id"]), int(a["request_id"])) for a in assets if a.get("request_id")}
        unstocked = [r for r in requests if (int(r["campus_id"]), int(r["id"])) not in stocked_keys]

        if len(unstocked) > args.target_unstocked:
            preferred = [r for r in unstocked if "批量导入测试资产" in str(r.get("reason") or "")]
            fallback = [r for r in unstocked if r not in preferred]
            ordered = sorted(preferred, key=lambda x: (x["created_at"], x["id"])) + sorted(
                fallback, key=lambda x: (x["created_at"], x["id"])
            )
            to_delete_req = ordered[: len(unstocked) - args.target_unstocked]
            deleted_req = _group_delete_requests(to_delete_req)
            print(f"[STEP] deleted_unstocked_requests={deleted_req}")
        elif len(unstocked) < args.target_unstocked:
            deficit = args.target_unstocked - len(unstocked)
            inserted_req = _insert_unstocked_requests(deficit, args.seed)
            print(f"[STEP] inserted_unstocked_requests={inserted_req}")

        final_counts = _print_counts("AFTER")
        sync_campus_summary_snapshots()
        print(
            f"[DONE] target_assets={args.target_assets} target_unstocked={args.target_unstocked} "
            f"final_assets={final_counts[1]} final_unstocked={final_counts[2]}"
        )


if __name__ == "__main__":
    main()
