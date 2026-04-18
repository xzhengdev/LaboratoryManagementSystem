"""
统计服务模块
提供校区、实验室、预约相关的统计功能
"""
from sqlalchemy import case, func

from app.models import Campus, Laboratory, Reservation


def _reservation_scope(campus_id=None):
    """
    获取预约查询的作用域（私有辅助函数）
    
    根据校区ID筛选预约记录，如果不传campus_id则返回所有预约
    
    Args:
        campus_id: 校区ID，可选参数，默认为None表示获取所有校区数据
        
    Returns:
        SQLAlchemy Query对象: 预约记录的查询对象
    """
    # 创建基础查询
    query = Reservation.query
    
    # 如果指定了校区ID，则添加筛选条件
    if campus_id is not None:
        query = query.filter(Reservation.campus_id == campus_id)
    
    return query


def _laboratory_scope(campus_id=None):
    """
    获取实验室查询的作用域（私有辅助函数）
    
    根据校区ID筛选实验室记录，如果不传campus_id则返回所有实验室
    
    Args:
        campus_id: 校区ID，可选参数，默认为None表示获取所有校区数据
        
    Returns:
        SQLAlchemy Query对象: 实验室的查询对象
    """
    # 创建基础查询
    query = Laboratory.query
    
    # 如果指定了校区ID，则添加筛选条件
    if campus_id is not None:
        query = query.filter(Laboratory.campus_id == campus_id)
    
    return query


def get_overview(campus_id=None):
    """
    获取总览统计数据
    
    返回指定校区（或全部校区）的核心指标数据，包括校区数量、实验室数量、
    预约总数、已批准预约数、待审批预约数
    
    Args:
        campus_id: 校区ID，可选参数
                   - 如果传入：统计单个校区数据
                   - 如果不传：统计所有校区数据
    
    Returns:
        dict: 包含以下统计指标的字典
            - campus_count: 校区数量（传入campus_id时固定为1，否则统计全部）
            - lab_count: 实验室数量
            - reservation_count: 预约总数量
            - approved_count: 已批准的预约数量
            - pending_count: 待审批的预约数量
    """
    # 获取预约查询作用域
    reservation_query = _reservation_scope(campus_id=campus_id)
    
    # 获取实验室查询作用域
    laboratory_query = _laboratory_scope(campus_id=campus_id)

    return {
        # 校区数量：如果指定了校区ID则返回1，否则统计所有校区
        "campus_count": 1 if campus_id is not None else Campus.query.count(),
        
        # 实验室总数
        "lab_count": laboratory_query.count(),
        
        # 预约总数
        "reservation_count": reservation_query.count(),
        
        # 已批准的预约数量
        "approved_count": reservation_query.filter(Reservation.status == "approved").count(),
        
        # 待审批的预约数量
        "pending_count": reservation_query.filter(Reservation.status == "pending").count(),
    }


def get_campus_statistics(campus_id=None):
    """
    获取校区维度统计数据
    统计每个校区（或指定校区）的实验室数量和预约总数
    Args:
        campus_id: 校区ID，可选参数
                   - 如果传入：只统计指定校区
                   - 如果不传：统计所有校区
    
    Returns:
        list: 校区统计信息列表，每个元素包含：
            - campus_id: 校区ID
            - campus_name: 校区名称
            - lab_count: 该校区的实验室数量
            - reservation_count: 该校区的预约总数
    """
    # 构建多表关联查询
    # 1. 以校区表为主表
    # 2. 左连接实验室表（按校区ID关联）
    # 3. 左连接预约表（按校区ID关联）
    query = (
        Campus.query
        .outerjoin(Laboratory, Laboratory.campus_id == Campus.id)  # 左连接实验室表
        .outerjoin(Reservation, Reservation.campus_id == Campus.id)  # 左连接预约表
        .with_entities(
            # 选择需要的字段
            Campus.id,                      # 校区ID
            Campus.campus_name,             # 校区名称
            # 统计实验室数量（去重，避免重复计数）
            func.count(func.distinct(Laboratory.id)).label("lab_count"),
            # 统计预约数量（去重，避免重复计数）
            func.count(func.distinct(Reservation.id)).label("reservation_count"),
        )
    )

    # 如果指定了校区ID，则添加筛选条件
    if campus_id is not None:
        query = query.filter(Campus.id == campus_id)

    # 按校区ID和校区名称分组
    rows = query.group_by(Campus.id, Campus.campus_name).all()

    # 将查询结果转换为字典列表并返回
    return [
        {
            "campus_id": row.id,
            "campus_name": row.campus_name,
            # 实验室数量：如果没有关联数据则为0
            "lab_count": int(row.lab_count or 0),
            # 预约总数：如果没有关联数据则为0
            "reservation_count": int(row.reservation_count or 0),
        }
        for row in rows
    ]


def get_lab_usage(campus_id=None):
    """
    获取实验室使用情况统计
    
    统计每个实验室（或指定校区的实验室）的预约总数和已批准数量
    
    Args:
        campus_id: 校区ID，可选参数
                   - 如果传入：只统计指定校区下的实验室
                   - 如果不传：统计所有实验室
    
    Returns:
        list: 实验室使用情况列表，每个元素包含：
            - lab_id: 实验室ID
            - lab_name: 实验室名称
            - campus_id: 所属校区ID
            - reservation_count: 该实验室的预约总数（所有状态）
            - approved_count: 该实验室已批准的预约数量
    """
    # 构建多表关联查询
    # 1. 以实验室表为主表
    # 2. 左连接预约表（按实验室ID关联）
    query = (
        Laboratory.query
        .outerjoin(Reservation, Reservation.lab_id == Laboratory.id)  # 左连接预约表
        .with_entities(
            # 选择需要的字段
            Laboratory.id,                      # 实验室ID
            Laboratory.lab_name,                # 实验室名称
            Laboratory.campus_id,               # 所属校区ID
            # 统计预约总数（COUNT自动忽略NULL值）
            func.count(Reservation.id).label("reservation_count"),
            # 统计已批准的预约数量
            # 使用CASE语句：当status为'approved'时计1，否则计0，然后求和
            func.sum(case((Reservation.status == "approved", 1), else_=0)).label("approved_count"),
        )
    )

    # 如果指定了校区ID，则添加筛选条件
    if campus_id is not None:
        query = query.filter(Laboratory.campus_id == campus_id)

    # 按实验室ID、名称和校区ID分组
    rows = query.group_by(Laboratory.id, Laboratory.lab_name, Laboratory.campus_id).all()

    # 将查询结果转换为字典列表并返回
    return [
        {
            "lab_id": row.id,
            "lab_name": row.lab_name,
            "campus_id": row.campus_id,
            # 预约总数：如果没有预约记录则为0
            "reservation_count": int(row.reservation_count or 0),
            # 已批准数量：如果没有批准记录则为0
            "approved_count": int(row.approved_count or 0),
        }
        for row in rows
    ]