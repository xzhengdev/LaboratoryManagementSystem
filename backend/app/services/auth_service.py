from flask_jwt_extended import create_access_token

from app.models import User
from app.utils.exceptions import AppError


def login(username, password, role=None):
    # 登录流程：
    # 1. 查用户
    # 2. 校验密码
    # 3. 校验角色是否匹配
    # 4. 校验账号状态
    # 5. 生成 JWT access token
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        raise AppError("用户名或密码错误", 401, 40100)
    if role and user.role != role:
        raise AppError("所选角色与账号身份不一致", 403, 40319)
    if user.status != "active":
        raise AppError("当前账户已被禁用", 403, 40302)

    token = create_access_token(identity=str(user.id))
    return {"token": token, "user": user.to_dict()}
