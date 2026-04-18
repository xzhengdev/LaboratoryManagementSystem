"""
用户管理蓝图 (user_bp)
功能：用户的增删改查、密码重置等
权限：仅系统管理员可访问所有用户管理接口
"""

from datetime import datetime  # 日期时间处理，用于记录重置时间

from flask import Blueprint, request  # Flask核心：蓝图、请求对象

from app.extensions import db                       # 数据库实例
from app.models import Campus, User                 # 数据模型：校区、用户
from app.utils.decorators import role_required      # 角色权限装饰器
from app.utils.exceptions import AppError           # 自定义异常类
from app.utils.response import success              # 统一成功响应格式
from app.utils.validators import require_fields     # 验证必填字段

# ==================== 蓝图创建 ====================
user_bp = Blueprint("users", __name__)


# ==================== 辅助函数 ====================
def _normalize_campus_id(value):
    """
    规范化校区ID
    
    功能：将各种形式的空值转换为 None，非空值转为整数
    
    参数：
        value - 原始校区ID（可能为 None、空字符串、"0"、0、数字等）
    
    返回：
        int 或 None
    """
    if value in (None, "", 0, "0"):
        return None
    return int(value)


def _ensure_username_unique(username, current_id=None):
    """
    确保用户名唯一性
    
    参数：
        username    - 要检查的用户名
        current_id  - 当前用户的ID（更新时传入，排除自己）
    
    异常：
        AppError - 用户名已存在时抛出
    """
    # 构建查询：查找相同用户名的用户
    query = User.query.filter_by(username=username)
    # 如果是更新操作，排除当前用户自己
    if current_id:
        query = query.filter(User.id != current_id)
    # 如果找到其他用户使用此用户名，抛出异常
    if query.first():
        raise AppError("用户名已存在", 400, 40021)


def _ensure_campus_valid_for_role(role, campus_id):
    """
    验证角色与校区的匹配关系
    
    规则：
        - system_admin：不需要绑定校区
        - 其他角色（student/teacher/lab_admin）：必须绑定有效校区
    
    参数：
        role      - 用户角色
        campus_id - 校区ID
    
    返回：
        验证后的 campus_id（system_admin 返回 None）
    
    异常：
        AppError - 角色不合法或校区无效时抛出
    """
    # 系统管理员不需要校区
    if role == "system_admin":
        return None
    
    # 验证角色是否合法
    if role not in ("student", "teacher", "lab_admin"):
        raise AppError("角色不合法", 400, 40022)
    
    # 其他角色必须绑定校区
    if campus_id is None:
        raise AppError("该角色必须绑定校区", 400, 40023)
    
    # 验证校区是否存在
    campus = Campus.query.get(campus_id)
    if not campus:
        raise AppError("校区不存在", 404, 40421)
    
    return campus.id


def _build_role_text(role):
    """
    将角色代码转换为中文显示名称
    
    参数：
        role - 角色代码（student/teacher/lab_admin/system_admin）
    
    返回：
        中文角色名称
    """
    return {
        "student": "学生",
        "teacher": "老师",
        "lab_admin": "实验室管理员",
        "system_admin": "系统管理员",
    }.get(role, "未知角色")


def _normalize_avatar_url(value):
    """
    规范化头像URL
    
    功能：验证并处理头像地址，空值转为None，检查长度限制
    
    参数：
        value - 原始URL值
    
    返回：
        处理后的URL字符串或None
    
    异常：
        AppError - URL长度超过500字符时抛出
    """
    if value in (None, ""):
        return None
    avatar_url = str(value).strip()
    if not avatar_url:
        return None
    # 检查长度限制（500字符）
    if len(avatar_url) > 500:
        raise AppError("头像地址长度不能超过 500", 400, 40025)
    return avatar_url


# ==================== 获取用户列表 ====================
@user_bp.get("/users")
@role_required("system_admin")  # 仅系统管理员可访问
def list_users():
    """
    获取用户列表（支持筛选和搜索）
    
    查询参数：
        role      - 按角色筛选（student/teacher/lab_admin/system_admin）
        status    - 按状态筛选（active/inactive）
        campus_id - 按校区筛选
        keyword   - 关键词搜索（匹配用户名、真实姓名、角色、校区名称）
    
    返回：
        用户信息数组，包含 role_name 中文字段
    """
    # 基础查询：按 ID 升序
    query = User.query.order_by(User.id.asc())
    
    # ----- 筛选条件 -----
    # 按角色筛选
    if request.args.get("role"):
        query = query.filter_by(role=request.args["role"])
    
    # 按状态筛选
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    
    # 按校区筛选
    if request.args.get("campus_id"):
        query = query.filter_by(campus_id=int(request.args["campus_id"]))

    # ----- 关键词搜索（在内存中模糊匹配）-----
    keyword = (request.args.get("keyword") or "").strip().lower()
    items = query.all()
    
    if keyword:
        # 在用户名、真实姓名、角色、校区名称中搜索关键词
        items = [
            item
            for item in items
            if keyword in f"{item.username}{item.real_name}{item.role}{item.campus.campus_name if item.campus else ''}".lower()
        ]
    
    # 返回用户列表，添加中文角色名称
    return success(
        [item.to_dict({"role_name": _build_role_text(item.role)}) for item in items]
    )


# ==================== 创建用户 ====================
@user_bp.post("/users")
@role_required("system_admin")
def create_user():
    """
    创建新用户（仅系统管理员可用）
    
    请求体必填字段：
        username  - 用户名（至少3位）
        real_name - 真实姓名
        role      - 角色（student/teacher/lab_admin/system_admin）
    
    请求体可选字段：
        password   - 密码（默认 123456）
        campus_id  - 校区ID（非系统管理员必填）
        phone      - 手机号
        email      - 邮箱
        avatar_url - 头像URL
        status     - 状态（默认 active）
    
    返回：
        新创建的用户信息
    """
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["username", "real_name", "role"])

    # ----- 用户名处理 -----
    username = str(payload["username"]).strip()
    if len(username) < 3:
        raise AppError("用户名至少 3 位", 400, 40024)
    _ensure_username_unique(username)

    # ----- 角色和校区验证 -----
    role = str(payload["role"]).strip()
    campus_id = _normalize_campus_id(payload.get("campus_id"))
    campus_id = _ensure_campus_valid_for_role(role, campus_id)

    # ----- 创建用户 -----
    item = User(
        username=username,
        real_name=str(payload["real_name"]).strip(),
        role=role,
        campus_id=campus_id,
        phone=payload.get("phone"),
        email=payload.get("email"),
        avatar_url=_normalize_avatar_url(payload.get("avatar_url")),
        status=payload.get("status", "active"),
    )
    
    # 设置密码（默认 123456）
    item.set_password(str(payload.get("password") or "123456"))
    
    # 保存到数据库
    db.session.add(item)
    db.session.commit()
    
    return success(
        item.to_dict({"role_name": _build_role_text(item.role)}),
        "创建用户成功",
    )


# ==================== 更新用户 ====================
@user_bp.put("/users/<int:user_id>")
@role_required("system_admin")
def update_user(user_id):
    """
    更新用户信息（仅系统管理员可用）
    
    参数：
        user_id - 用户ID（URL路径参数）
    
    请求体可选字段：
        username  - 用户名
        real_name - 真实姓名
        role      - 角色
        status    - 状态
        phone     - 手机号
        email     - 邮箱
        avatar_url - 头像URL
        campus_id - 校区ID
    
    返回：
        更新后的用户信息
    """
    payload = request.get_json(silent=True) or {}
    item = User.query.get_or_404(user_id)

    # ----- 更新用户名（需检查唯一性）-----
    if "username" in payload:
        username = str(payload["username"]).strip()
        if len(username) < 3:
            raise AppError("用户名至少 3 位", 400, 40024)
        _ensure_username_unique(username, current_id=item.id)
        item.username = username
    
    # ----- 更新普通字段 -----
    if "real_name" in payload:
        item.real_name = str(payload["real_name"]).strip()
    if "status" in payload:
        item.status = payload["status"]
    if "phone" in payload:
        item.phone = payload["phone"]
    if "email" in payload:
        item.email = payload["email"]
    if "avatar_url" in payload:
        item.avatar_url = _normalize_avatar_url(payload.get("avatar_url"))

    # ----- 更新角色和校区（需验证匹配关系）-----
    # 确定新角色（如果未传则用原角色）
    next_role = payload["role"] if "role" in payload else item.role
    # 确定新校区ID（如果未传则用原校区ID）
    next_campus_id = (
        _normalize_campus_id(payload["campus_id"])
        if "campus_id" in payload
        else item.campus_id
    )
    
    # 更新角色和校区（会验证合法性）
    item.role = next_role
    item.campus_id = _ensure_campus_valid_for_role(next_role, next_campus_id)

    # 提交更改
    db.session.commit()
    
    return success(
        item.to_dict({"role_name": _build_role_text(item.role)}),
        "更新用户成功",
    )


# ==================== 重置密码 ====================
@user_bp.post("/users/<int:user_id>/reset-password")
@role_required("system_admin")
def reset_password(user_id):
    """
    重置用户密码（仅系统管理员可用）
    
    参数：
        user_id - 用户ID（URL路径参数）
    
    请求体可选字段：
        password - 新密码（默认 123456）
    
    返回：
        包含 user_id 和重置时间的对象
    """
    payload = request.get_json(silent=True) or {}
    item = User.query.get_or_404(user_id)
    
    # 设置新密码（默认 123456）
    new_password = str(payload.get("password") or "123456")
    item.set_password(new_password)
    
    db.session.commit()
    
    return success(
        {
            "user_id": item.id,
            "reset_at": datetime.utcnow().isoformat()  # UTC 时间 ISO 格式
        },
        "重置密码成功",
    )