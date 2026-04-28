from decimal import Decimal, InvalidOperation
from datetime import datetime

from app.models import (
    AssetBudget,
    AssetBudgetLedger,
    AssetItem,
    AssetPurchaseRequest,
    Laboratory,
    OperationLog,
)
from app.services.db_router_service import campus_db_session, get_routed_campus_ids
from app.services.distributed_lock_service import asset_budget_lock
from app.services.event_bus_service import publish_async_event
from app.services.idempotency_service import (
    build_payload_signature,
    claim_idempotency_record,
    mark_idempotency_failed,
    mark_idempotency_success,
    normalize_idempotency_key,
)
from app.utils.exceptions import AppError

IDEMPOTENCY_ENDPOINT_CREATE_ASSET_REQUEST = "create_asset_request"


def _to_decimal(value, field_name):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise AppError(f"{field_name} 格式不正确")
    if amount <= 0:
        raise AppError(f"{field_name} 必须大于 0")
    return amount


def _build_request_no(campus_id):
    return f"AR{int(campus_id):03d}{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:20]}"


def _ensure_budget(session, campus_id):
    budget = session.query(AssetBudget).filter_by(campus_id=campus_id).first()
    if budget:
        return budget
    budget = AssetBudget(
        campus_id=campus_id,
        total_amount=Decimal("0.00"),
        locked_amount=Decimal("0.00"),
        used_amount=Decimal("0.00"),
    )
    session.add(budget)
    session.flush()
    return budget


def _write_budget_ledger(
    session,
    campus_id,
    request_id,
    op_type,
    amount,
    before_locked,
    after_locked,
    before_used,
    after_used,
    operator_id,
    remark="",
):
    session.add(
        AssetBudgetLedger(
            campus_id=campus_id,
            request_id=request_id,
            op_type=op_type,
            amount=amount,
            before_locked=before_locked,
            after_locked=after_locked,
            before_used=before_used,
            after_used=after_used,
            operator_id=operator_id,
            remark=remark,
        )
    )


def _write_log(session, user_id, action, detail):
    session.add(OperationLog(user_id=user_id, module="asset", action=action, detail=detail))


def _lab_belongs_to_campus(campus_id, lab_id):
    with campus_db_session(campus_id) as session:
        lab = session.query(Laboratory).get(int(lab_id))
        if not lab:
            raise AppError("实验室不存在", 404, 40401)
        if lab.campus_id != campus_id:
            raise AppError("实验室与校区不匹配")


def _campus_id_for_user(current_user, campus_id=None):
    if current_user.role == "system_admin" and campus_id:
        return int(campus_id)
    if not current_user.campus_id:
        raise AppError("当前用户未绑定校区", 400, 40081)
    return current_user.campus_id


def get_budget_for_user(current_user, campus_id=None):
    target_campus_id = _campus_id_for_user(current_user, campus_id=campus_id)
    with campus_db_session(target_campus_id) as session:
        try:
            budget = _ensure_budget(session, target_campus_id)
            session.commit()
            return budget.to_dict()
        except Exception:
            session.rollback()
            raise


def update_budget_total(current_user, campus_id, total_amount, remark=""):
    if current_user.role != "system_admin":
        raise AppError("只有系统管理员可以修改预算额度", 403, 40341)

    target_campus_id = int(campus_id)
    amount = _to_decimal(total_amount, "total_amount")

    with campus_db_session(target_campus_id) as session:
        try:
            with asset_budget_lock(target_campus_id):
                budget = _ensure_budget(session, target_campus_id)
                used_and_locked = (budget.locked_amount or 0) + (budget.used_amount or 0)
                if amount < used_and_locked:
                    raise AppError("总额度不能小于当前锁定额度与已使用额度之和", 400, 40082)
                budget.total_amount = amount
                budget.remark = str(remark or "")[:255]
                _write_log(session, current_user.id, "budget_update", f"更新校区{target_campus_id}预算总额为{amount}")
                session.commit()
                return budget.to_dict()
        except Exception:
            session.rollback()
            raise


def create_asset_request(current_user, payload, idempotency_key=""):
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("仅管理员可提交资产申报", 403, 40342)

    campus_id = int(payload.get("campus_id") or 0)
    if current_user.role == "lab_admin":
        if not current_user.campus_id:
            raise AppError("管理员账号未绑定校区", 400, 40083)
        if campus_id and campus_id != current_user.campus_id:
            raise AppError("只能提交本校区资产申报", 403, 40343)
        campus_id = current_user.campus_id
    if not campus_id:
        raise AppError("campus_id 不能为空")

    lab_id = payload.get("lab_id")
    if str(lab_id or "").strip() == "":
        lab_id = None
    if lab_id is not None:
        _lab_belongs_to_campus(campus_id, lab_id)

    asset_name = str(payload.get("asset_name") or "").strip()
    category = str(payload.get("category") or "").strip()
    if not asset_name:
        raise AppError("asset_name 不能为空")
    if not category:
        raise AppError("category 不能为空")

    quantity = int(payload.get("quantity") or 1)
    if quantity <= 0:
        raise AppError("quantity 必须大于 0")
    unit_price = _to_decimal(payload.get("unit_price"), "unit_price")
    amount = (unit_price * Decimal(quantity)).quantize(Decimal("0.01"))
    reason = str(payload.get("reason") or "").strip()

    normalized_key = normalize_idempotency_key(idempotency_key)
    idempotency_record = None
    if normalized_key:
        request_hash = build_payload_signature(
            {
                "user_id": current_user.id,
                "campus_id": campus_id,
                "lab_id": int(lab_id) if lab_id is not None else None,
                "asset_name": asset_name,
                "category": category,
                "quantity": quantity,
                "unit_price": str(unit_price),
                "amount": str(amount),
                "reason": reason,
            }
        )
        idempotency_record, cached = claim_idempotency_record(
            current_user,
            IDEMPOTENCY_ENDPOINT_CREATE_ASSET_REQUEST,
            normalized_key,
            request_hash,
        )
        if cached is not None:
            return cached

    with campus_db_session(campus_id) as session:
        try:
            with asset_budget_lock(campus_id):
                budget = _ensure_budget(session, campus_id)
                total = budget.total_amount or Decimal("0.00")
                locked = budget.locked_amount or Decimal("0.00")
                used = budget.used_amount or Decimal("0.00")
                available = total - locked - used
                if available < amount:
                    raise AppError("可用预算不足，无法锁定额度", 409, 40941)

                before_locked = locked
                before_used = used
                budget.locked_amount = locked + amount

                request_item = AssetPurchaseRequest(
                    request_no=_build_request_no(campus_id),
                    campus_id=campus_id,
                    lab_id=int(lab_id) if lab_id is not None else None,
                    requester_id=current_user.id,
                    asset_name=asset_name,
                    category=category,
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount,
                    reason=reason,
                    status="pending",
                )
                session.add(request_item)
                session.flush()
                _write_budget_ledger(
                    session=session,
                    campus_id=campus_id,
                    request_id=request_item.id,
                    op_type="lock",
                    amount=amount,
                    before_locked=before_locked,
                    after_locked=budget.locked_amount,
                    before_used=before_used,
                    after_used=before_used,
                    operator_id=current_user.id,
                    remark="资产申报锁定预算",
                )
                _write_log(session, current_user.id, "request_create", f"创建资产申报#{request_item.request_no}")
                session.commit()
                result = request_item.to_dict()
                publish_async_event(
                    "asset.request.created",
                    {
                        "request_id": request_item.id,
                        "request_no": request_item.request_no,
                        "campus_id": request_item.campus_id,
                        "amount": float(request_item.amount),
                        "status": request_item.status,
                    },
                )
            if idempotency_record:
                mark_idempotency_success(idempotency_record.id, result)
            return result
        except AppError as error:
            session.rollback()
            if idempotency_record:
                mark_idempotency_failed(idempotency_record.id, error.message, error.code)
            raise
        except Exception:
            session.rollback()
            if idempotency_record:
                mark_idempotency_failed(idempotency_record.id, "服务器内部错误", 500)
            raise


def _list_requests_in_one_campus(session, filters, current_user):
    query = session.query(AssetPurchaseRequest).order_by(AssetPurchaseRequest.created_at.desc())
    if current_user.role in {"student", "teacher"}:
        query = query.filter_by(requester_id=current_user.id)
    if filters.get("status"):
        query = query.filter_by(status=str(filters["status"]).strip())
    if filters.get("requester_id") and current_user.role in {"lab_admin", "system_admin"}:
        query = query.filter_by(requester_id=int(filters["requester_id"]))
    return [item.to_dict() for item in query.all()]


def list_asset_requests(current_user, filters):
    # 指定校区时只查该校区
    if filters.get("campus_id"):
        target_campus_id = int(filters["campus_id"])
        if current_user.role == "lab_admin" and target_campus_id != current_user.campus_id:
            raise AppError("只能查看本校区资产申报", 403, 40349)
        with campus_db_session(target_campus_id) as session:
            return _list_requests_in_one_campus(session, filters, current_user)

    # 未指定校区：系统管理员聚合全部分库，其它角色查自己的校区
    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            with campus_db_session(0) as session:
                return _list_requests_in_one_campus(session, filters, current_user)
        rows = []
        for campus_id in campus_ids:
            with campus_db_session(campus_id) as session:
                rows.extend(_list_requests_in_one_campus(session, filters, current_user))
        rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return rows

    with campus_db_session(current_user.campus_id) as session:
        return _list_requests_in_one_campus(session, filters, current_user)


def _load_request_for_review(session, request_id):
    item = session.query(AssetPurchaseRequest).get(int(request_id))
    if not item:
        raise AppError("资产申报不存在", 404, 40412)
    return item


def review_asset_request(current_user, request_item, approval_status, remark=""):
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审批资产申报", 403, 40344)

    campus_id = request_item.campus_id
    with campus_db_session(campus_id) as session:
        item = _load_request_for_review(session, request_item.id)
        if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
            raise AppError("只能审批本校区资产申报", 403, 40345)
        if item.status != "pending":
            raise AppError("当前申报不在待审批状态")

        status = str(approval_status or "").strip().lower()
        if status not in {"approved", "rejected"}:
            raise AppError("approval_status 只能是 approved 或 rejected")

        try:
            with asset_budget_lock(item.campus_id):
                budget = _ensure_budget(session, item.campus_id)
                amount = item.amount
                before_locked = budget.locked_amount or Decimal("0.00")
                before_used = budget.used_amount or Decimal("0.00")

                if before_locked < amount:
                    raise AppError("预算锁定额度异常，请联系管理员", 409, 40942)

                budget.locked_amount = before_locked - amount
                if status == "approved":
                    budget.used_amount = before_used + amount
                else:
                    budget.used_amount = before_used

                item.status = status
                item.reviewer_id = current_user.id
                item.review_remark = str(remark or "")[:255]
                item.reviewed_at = datetime.utcnow()

                _write_budget_ledger(
                    session=session,
                    campus_id=item.campus_id,
                    request_id=item.id,
                    op_type="consume" if status == "approved" else "release",
                    amount=amount,
                    before_locked=before_locked,
                    after_locked=budget.locked_amount,
                    before_used=before_used,
                    after_used=budget.used_amount,
                    operator_id=current_user.id,
                    remark="审批通过转已用" if status == "approved" else "审批拒绝释放锁定",
                )
                _write_log(session, current_user.id, "request_review", f"审批资产申报#{item.request_no}: {status}")
                session.commit()
                result = item.to_dict()
                publish_async_event(
                    f"asset.request.{status}",
                    {
                        "request_id": item.id,
                        "request_no": item.request_no,
                        "campus_id": item.campus_id,
                        "status": item.status,
                    },
                )
                return result
        except Exception:
            session.rollback()
            raise


def stock_in_asset(current_user, request_item, payload):
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以执行资产入库", 403, 40346)

    campus_id = request_item.campus_id
    with campus_db_session(campus_id) as session:
        item = _load_request_for_review(session, request_item.id)
        if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
            raise AppError("只能操作本校区资产入库", 403, 40347)
        if item.status != "approved":
            raise AppError("仅审批通过的申报可入库")

        exists = session.query(AssetItem).filter_by(request_id=item.id).first()
        if exists:
            raise AppError("该申报已完成入库", 409, 40943)

        asset_code = str(payload.get("asset_code") or "").strip()
        if not asset_code:
            asset_code = f"AS{item.campus_id:03d}{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{item.id:04d}"

        description = str(payload.get("description") or "").strip()
        try:
            asset_row = AssetItem(
                asset_code=asset_code,
                campus_id=item.campus_id,
                lab_id=item.lab_id,
                request_id=item.id,
                asset_name=item.asset_name,
                category=item.category,
                price=item.amount,
                status=str(payload.get("status") or "in_use"),
                description=description,
            )
            session.add(asset_row)
            _write_log(session, current_user.id, "stock_in", f"资产申报#{item.request_no}入库为资产#{asset_code}")
            session.commit()
            result = asset_row.to_dict()
            publish_async_event(
                "asset.stocked_in",
                {
                    "asset_id": asset_row.id,
                    "asset_code": asset_row.asset_code,
                    "request_id": item.id,
                    "campus_id": asset_row.campus_id,
                },
            )
            return result
        except Exception:
            session.rollback()
            raise


def _list_assets_in_one_campus(session, filters):
    query = session.query(AssetItem).order_by(AssetItem.created_at.desc())
    if filters.get("status"):
        query = query.filter_by(status=str(filters["status"]).strip())
    if filters.get("category"):
        query = query.filter_by(category=str(filters["category"]).strip())
    if filters.get("lab_id"):
        query = query.filter_by(lab_id=int(filters["lab_id"]))
    return [item.to_dict() for item in query.all()]


def list_assets(current_user, filters):
    if filters.get("campus_id"):
        target_campus_id = int(filters["campus_id"])
        if current_user.role == "lab_admin" and target_campus_id != current_user.campus_id:
            raise AppError("只能查看本校区资产", 403, 40350)
        with campus_db_session(target_campus_id) as session:
            return _list_assets_in_one_campus(session, filters)

    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            with campus_db_session(0) as session:
                return _list_assets_in_one_campus(session, filters)
        rows = []
        for campus_id in campus_ids:
            with campus_db_session(campus_id) as session:
                rows.extend(_list_assets_in_one_campus(session, filters))
        rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return rows

    with campus_db_session(current_user.campus_id) as session:
        return _list_assets_in_one_campus(session, filters)
