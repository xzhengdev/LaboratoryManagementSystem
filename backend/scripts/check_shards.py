import json
import os
import sys

from sqlalchemy import create_engine, inspect, text

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app

# 校区库应有表：用户/实验室/预约/资产/日报/文件/幂等/审批/日志/通知/预算流水
CAMPUS_TABLES = [
    "campuses",
    "users",
    "laboratories",
    "equipment",
    "reservations",
    "approvals",
    "operation_logs",
    "idempotency_records",
    "file_objects",
    "asset_purchase_requests",
    "asset_budget_ledgers",
    "asset_items",
    "notification_messages",
    "lab_daily_reports",
]

# 中心汇总库应有表：14 张业务表 + 2 张汇总专属表 (共 16 张，不含 asset_budgets)
SUMMARY_TABLES = [
    "campuses",
    "users",
    "laboratories",
    "equipment",
    "reservations",
    "approvals",
    "operation_logs",
    "idempotency_records",
    "file_objects",
    "asset_purchase_requests",
    "asset_budget_ledgers",
    "asset_items",
    "notification_messages",
    "lab_daily_reports",
    "campus_summary_snapshots",
    "global_asset_budgets",
]


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


def count_rows(conn, table_name):
    sql = text(f"SELECT COUNT(*) FROM {table_name}")
    return int(conn.execute(sql).scalar() or 0)


def check_one_db(label, uri, required_tables):
    engine = create_engine(uri, pool_pre_ping=True)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    missing = [name for name in required_tables if name not in table_names]

    print(f"[{label}] 总表数={len(table_names)}, 缺失={len(missing)}")
    if missing:
        print(f"[{label}] 缺失表: {', '.join(missing)}")
        return False

    with engine.connect() as conn:
        reservation_count = count_rows(conn, "reservations") if "reservations" in table_names else None
        asset_req_count = count_rows(conn, "asset_purchase_requests") if "asset_purchase_requests" in table_names else None
        report_count = count_rows(conn, "lab_daily_reports") if "lab_daily_reports" in table_names else None

    parts = []
    if reservation_count is not None:
        parts.append(f"预约={reservation_count}")
    if asset_req_count is not None:
        parts.append(f"资产申报={asset_req_count}")
    if report_count is not None:
        parts.append(f"日报={report_count}")
    print(f"[{label}] " + ", ".join(parts))
    return True


def main():
    app = create_app()
    with app.app_context():
        campus_map = parse_campus_db_map(app.config.get("CAMPUS_DB_URI_MAP", ""))
        summary_uri = str(app.config.get("SUMMARY_DB_URL") or "").strip()

        if not campus_map:
            raise RuntimeError("未配置 CAMPUS_DB_URI_MAP")

        passed = True

        # 校区库校验
        print("=" * 50)
        print("[检查] 校区数据库 (应含 14 张业务表)")
        print("=" * 50)
        for campus_id in sorted(campus_map.keys()):
            ok = check_one_db(f"校区-{campus_id}", campus_map[campus_id], CAMPUS_TABLES)
            passed = passed and ok

        # 中心汇总库校验
        if summary_uri:
            print()
            print("=" * 50)
            print("[检查] 中心汇总库 (应含 16 张表: 14 业务 + 2 汇总)")
            print("=" * 50)
            ok = check_one_db("中心汇总库", summary_uri, SUMMARY_TABLES)
            passed = passed and ok
        else:
            print("[WARN] 未配置 SUMMARY_DB_URL，跳过中心汇总库检查")

        if not passed:
            raise RuntimeError("分库自检未通过，请先执行 python scripts/bootstrap_shards.py")

        print()
        print("[DONE] 分库自检全部通过")


if __name__ == "__main__":
    main()
