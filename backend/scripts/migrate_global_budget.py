import os
import sys
from decimal import Decimal

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.models import AssetBudget, GlobalAssetBudget
from app.services.db_router_service import campus_db_session, get_routed_campus_ids, summary_db_session


def _as_decimal(value):
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0.00")


def main():
    app = create_app()
    with app.app_context():
        campus_ids = get_routed_campus_ids() or [0]
        total_amount = Decimal("0.00")
        locked_amount = Decimal("0.00")
        used_amount = Decimal("0.00")

        for campus_id in campus_ids:
            with campus_db_session(campus_id) as session:
                row = session.query(AssetBudget).filter_by(campus_id=int(campus_id)).first()
                if not row:
                    print(f"[INFO] 校区 {campus_id} 无资产预算记录，跳过")
                    continue
                total_amount += _as_decimal(row.total_amount)
                locked_amount += _as_decimal(row.locked_amount)
                used_amount += _as_decimal(row.used_amount)
                print(
                    f"[INFO] 校区 {campus_id} -> total={row.total_amount}, locked={row.locked_amount}, used={row.used_amount}"
                )

        with summary_db_session() as session:
            bind = session.get_bind()
            GlobalAssetBudget.__table__.create(bind=bind, checkfirst=True)
            budget = session.query(GlobalAssetBudget).first()
            if not budget:
                budget = GlobalAssetBudget()
                session.add(budget)
            budget.total_amount = total_amount
            budget.locked_amount = locked_amount
            budget.used_amount = used_amount
            budget.remark = "由各校区预算汇总迁移生成"
            session.commit()

        print("[DONE] 全校共享预算迁移完成")
        print(f"[DONE] total={total_amount}, locked={locked_amount}, used={used_amount}")


if __name__ == "__main__":
    main()

