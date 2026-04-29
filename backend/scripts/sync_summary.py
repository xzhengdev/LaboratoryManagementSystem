import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.services.summary_sync_service import sync_campus_summary_snapshots


def main():
    app = create_app()
    with app.app_context():
        result = sync_campus_summary_snapshots()
        snapshot_date = result.get("snapshot_date")
        rows = result.get("rows") or []
        totals = result.get("totals") or {}
        print(f"[OK] 汇总同步完成: snapshot_date={snapshot_date}, campus_count={len(rows)}")
        print(
            "[TOTAL] reservations={reservation_count}, asset_requests={asset_request_count}, "
            "asset_items={asset_item_count}, daily_reports={daily_report_count}".format(
                reservation_count=totals.get("reservation_count", 0),
                asset_request_count=totals.get("asset_request_count", 0),
                asset_item_count=totals.get("asset_item_count", 0),
                daily_report_count=totals.get("daily_report_count", 0),
            )
        )


if __name__ == "__main__":
    main()
