from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.models import User
from .exceptions import AppError


def get_current_user():
    # 从 JWT 中取出当前登录用户 id，并查询数据库得到完整用户对象。
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        raise AppError("用户不存在或登录已失效", 401, 40101)
    return user


def role_required(*roles):
    # 角色权限装饰器：
    # 用于限制某些接口只能由指定角色访问。
    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if user.role not in roles:
                raise AppError("没有权限访问该资源", 403, 40301)
            return func(*args, **kwargs)

        return wrapper

    return decorator
