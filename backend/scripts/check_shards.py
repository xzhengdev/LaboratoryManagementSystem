import json
import os
import sys

from sqlalchemy import create_engine, inspect, text

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    # Allow running `python scripts/check_shards.py` directly.
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app

REQUIRED_TABLES = [
    "campuses",
    "users",
    "laboratories",
    "reservations",
    "asset_budgets",
    "asset_purchase_requests",
    "asset_items",
    "file_objects",
    "lab_daily_reports",
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


def check_one_db(label, uri):
    engine = create_engine(uri, pool_pre_ping=True)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    missing = [name for name in REQUIRED_TABLES if name not in table_names]
    print(f"[{label}] tables={len(table_names)}, missing={len(missing)}")
    if missing:
        print(f"[{label}] missing tables: {', '.join(missing)}")
        return False

    with engine.connect() as conn:
        reservation_count = count_rows(conn, "reservations")
        asset_req_count = count_rows(conn, "asset_purchase_requests")
        report_count = count_rows(conn, "lab_daily_reports")
    print(
        f"[{label}] reservations={reservation_count}, asset_requests={asset_req_count}, daily_reports={report_count}"
    )
    return True


def main():
    app = create_app()
    with app.app_context():
        campus_map = parse_campus_db_map(app.config.get("CAMPUS_DB_URI_MAP", ""))
        summary_uri = str(app.config.get("SUMMARY_DB_URL") or "").strip()

        if not campus_map:
            raise RuntimeError("未配置 CAMPUS_DB_URI_MAP")

        passed = True
        for campus_id in sorted(campus_map.keys()):
            ok = check_one_db(f"campus-{campus_id}", campus_map[campus_id])
            passed = passed and ok

        if summary_uri:
            ok = check_one_db("summary", summary_uri)
            passed = passed and ok

        if not passed:
            raise RuntimeError("分库自检未通过，请先执行 bootstrap_shards.py")

        print("[DONE] 分库自检通过")


if __name__ == "__main__":
    main()
