from .entities import (
    Approval,
    Campus,
    Equipment,
    IdempotencyRecord,
    Laboratory,
    OperationLog,
    Reservation,
    User,
)

# 统一导出模型，方便其他模块直接 from app.models import User 这种写法。
__all__ = [
    "Approval",
    "Campus",
    "Equipment",
    "IdempotencyRecord",
    "Laboratory",
    "OperationLog",
    "Reservation",
    "User",
]
