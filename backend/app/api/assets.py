from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.models import AssetItem, AssetPurchaseRequest
from app.services.asset_service import (
    create_asset_request,
    get_budget_for_user,
    list_asset_requests,
    list_assets,
    review_asset_request,
    stock_in_asset,
    update_budget_total,
)
from app.services.db_router_service import campus_db_session, get_routed_campus_ids
from app.services.file_storage_service import save_image_file
from app.services.rate_limit_service import enforce_create_asset_request_rate_limit
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success


asset_bp = Blueprint("assets", __name__)


def _campus_candidates_for_user(current_user):
    if current_user.role == "system_admin":
        candidates = get_routed_campus_ids()
        return candidates or [0]
    return [current_user.campus_id or 0]


def _find_asset_request(current_user, request_id):
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            item = session.query(AssetPurchaseRequest).get(int(request_id))
            if item:
                return item
    raise AppError("资产申报不存在", 404, 40412)


def _find_asset_item(current_user, asset_id):
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            item = session.query(AssetItem).get(int(asset_id))
            if item:
                return item
    raise AppError("资产不存在", 404, 40414)


@asset_bp.get("/asset-budgets/current")
@jwt_required()
def get_current_budget_api():
    current_user = get_current_user()
    campus_id = request.args.get("campus_id")
    result = get_budget_for_user(current_user, campus_id=campus_id)
    return success(result)


@asset_bp.put("/asset-budgets/<int:campus_id>")
@role_required("system_admin")
def update_budget_total_api(campus_id):
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    result = update_budget_total(
        current_user,
        campus_id,
        payload.get("total_amount"),
        payload.get("remark", ""),
    )
    return success(result, "预算总额更新成功")


@asset_bp.post("/asset-requests")
@role_required("lab_admin", "system_admin")
def create_asset_request_api():
    current_user = get_current_user()
    enforce_create_asset_request_rate_limit(current_user.id)
    payload = request.get_json(silent=True) or {}
    idempotency_key = (request.headers.get("Idempotency-Key") or "").strip()
    result = create_asset_request(current_user, payload, idempotency_key=idempotency_key)
    return success(result, "资产申报提交成功")


@asset_bp.get("/asset-requests")
@jwt_required()
def list_asset_requests_api():
    current_user = get_current_user()
    result = list_asset_requests(current_user, request.args)
    return success(result)


@asset_bp.post("/asset-requests/<int:request_id>/review")
@role_required("lab_admin", "system_admin")
def review_asset_request_api(request_id):
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = _find_asset_request(current_user, request_id)
    result = review_asset_request(
        current_user,
        item,
        payload.get("approval_status", ""),
        payload.get("remark", ""),
    )
    return success(result, "资产申报审批完成")


@asset_bp.post("/asset-requests/<int:request_id>/stock-in")
@role_required("lab_admin", "system_admin")
def stock_in_asset_api(request_id):
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = _find_asset_request(current_user, request_id)
    result = stock_in_asset(current_user, item, payload)
    return success(result, "资产入库成功")


@asset_bp.get("/assets")
@jwt_required()
def list_assets_api():
    current_user = get_current_user()
    result = list_assets(current_user, request.args)
    return success(result)


@asset_bp.post("/assets/<int:asset_id>/photos/upload")
@role_required("lab_admin", "system_admin")
def upload_asset_photo_api(asset_id):
    current_user = get_current_user()
    item = _find_asset_item(current_user, asset_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能上传本校区资产图片", 403, 40348)

    file_storage = request.files.get("file")
    if not file_storage:
        raise AppError("缺少文件字段 file")

    with campus_db_session(item.campus_id) as session:
        file_obj = save_image_file(
            current_user=current_user,
            file_storage=file_storage,
            campus_id=item.campus_id,
            biz_type="asset_photo",
            biz_id=item.id,
            session=session,
        )
        session.commit()
        return success(file_obj.to_dict(), "资产图片上传成功")
