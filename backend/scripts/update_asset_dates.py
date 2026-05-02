import os
import random
import sys
from datetime import datetime, timedelta

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import AssetItem, AssetPurchaseRequest
from app.services.db_router_service import campus_db_session, get_routed_campus_ids

app = create_app()

NOW = datetime(2026, 5, 2, 18, 0, 0)


def random_recent_date():
    """Random datetime within the last 30 days, weighted toward more recent."""
    days_ago = random.randint(0, 30)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    return NOW - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)


def update_campus(campus_id):
    with campus_db_session(campus_id) as session:
        requests = session.query(AssetPurchaseRequest).all()
        print(f"  Campus {campus_id}: found {len(requests)} purchase requests")

        updated = 0
        for req in requests:
            new_created = random_recent_date()
            req.created_at = new_created
            req.updated_at = new_created

            if req.status in ('approved', 'rejected') and req.reviewed_at:
                # reviewed 1-48 hours after creation
                offset = timedelta(hours=random.randint(1, 48))
                req.reviewed_at = min(new_created + offset, NOW)

            updated += 1

        session.commit()
        print(f"  Campus {campus_id}: updated {updated} requests")

        # Also update asset_items
        assets = session.query(AssetItem).all()
        print(f"  Campus {campus_id}: found {len(assets)} asset items")

        asset_updated = 0
        for item in assets:
            new_created = random_recent_date()
            item.created_at = new_created
            item.updated_at = new_created
            asset_updated += 1

        session.commit()
        print(f"  Campus {campus_id}: updated {asset_updated} asset items")


def main():
    with app.app_context():
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            campus_ids = [0]
        print(f"Campus IDs: {campus_ids}")
        print(f"Reference date (now): {NOW.isoformat()}")
        print()

        for cid in campus_ids:
            update_campus(cid)

    print("\nDone. All asset dates updated to recent (within last 30 days).")


if __name__ == '__main__':
    main()
