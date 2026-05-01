import json
import os
import sys
from typing import Dict, List

from sqlalchemy import create_engine

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import *  # noqa: F401,F403

# 校区库: 14 张业务表 (不含已废弃的 asset_budgets)
CAMPUS_TABLE_NAMES = [
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

# 中心汇总库: 14 张业务表 + 2 张汇总专属表 (共 16 张)
# 汇总库保存全量数据用于认证、用户管理和跨校区聚合查询
SUMMARY_TABLE_NAMES = [
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


def parse_campus_db_map(raw: str) -> Dict[int, str]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception as exc:
        raise RuntimeError("CAMPUS_DB_URI_MAP is not valid JSON") from exc

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


def ensure_schema(uri: str, table_names: List[str]):
    engine = create_engine(uri, pool_pre_ping=True)
    tables = [db.metadata.tables[name] for name in table_names if name in db.metadata.tables]
    db.metadata.create_all(bind=engine, tables=tables)


def main():
    app = create_app()
    with app.app_context():
        enabled = bool(app.config.get("ENABLE_CAMPUS_DB_ROUTING", False))
        campus_map = parse_campus_db_map(app.config.get("CAMPUS_DB_URI_MAP", ""))
        summary_uri = str(app.config.get("SUMMARY_DB_URL") or "").strip()

        if not enabled:
            print("[WARN] ENABLE_CAMPUS_DB_ROUTING=0, single-db mode")

        if not campus_map:
            raise RuntimeError("CAMPUS_DB_URI_MAP not configured, cannot init campus DBs")

        print(f"[INFO] Found {len(campus_map)} campus DB configs")
        for campus_id in sorted(campus_map.keys()):
            print(f"[INFO] Init campus {campus_id} schema ({len(CAMPUS_TABLE_NAMES)} tables)...")
            ensure_schema(campus_map[campus_id], CAMPUS_TABLE_NAMES)
            print(f"[OK] Campus {campus_id} done")

        if summary_uri:
            print(f"[INFO] Init summary DB schema ({len(SUMMARY_TABLE_NAMES)} tables)...")
            ensure_schema(summary_uri, SUMMARY_TABLE_NAMES)
            print("[OK] Summary DB done")
        else:
            print("[WARN] SUMMARY_DB_URL not configured, skip summary DB")

        print("[DONE] Bootstrap complete")


if __name__ == "__main__":
    main()
