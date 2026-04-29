"""
数据统计蓝图 (statistics_bp)
功能：提供实验室预约系统的各类统计数据
权限：仅实验室管理员和系统管理员可访问
"""

from flask import Blueprint  # Flask核心：蓝图

from app.services.statistics_service import (
    get_campus_statistics,
    get_daily_report_campus_statistics,
    get_daily_report_lab_statistics,
    get_daily_report_overview,
    get_lab_usage,
    get_overview,
)  # 统计服务
from app.services.summary_sync_service import (
    get_latest_campus_summary_rows,
    sync_summary_for_system_admin,
)
from app.utils.decorators import get_current_user, role_required  # 用户获取、角色权限
from app.utils.response import success  # 统一成功响应格式

# ==================== 蓝图创建 ====================
statistics_bp = Blueprint("statistics", __name__)


# ==================== 概览统计 ====================
@statistics_bp.get("/statistics/overview")
@role_required("lab_admin", "system_admin")  # 需要实验室管理员或系统管理员角色
def overview_api():
    """
    获取系统概览统计数据（仪表盘核心数据）
    
    功能：返回实验室预约系统的核心指标
    
    数据范围：
        - 系统管理员：查看全校区的统计数据
        - 实验室管理员：只查看自己所在校区的统计数据
    
    返回示例：
        {
            "total_labs": 15,           // 实验室总数
            "total_equipment": 120,     // 设备总数
            "total_reservations": 350,  // 预约总数
            "pending_approvals": 8,     // 待审批数量
            "monthly_reservations": 45  // 本月预约数
        }
    """
    # 获取当前登录用户
    current_user = get_current_user()
    
    # 根据角色确定统计范围
    # 实验室管理员：只能查看自己校区，传入 campus_id
    # 系统管理员：查看全部，传入 None
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    
    # 调用服务层获取概览数据
    result = get_overview(campus_id=campus_id)
    
    return success(result)


# ==================== 校区统计 ====================
@statistics_bp.get("/statistics/campus")
@role_required("lab_admin", "system_admin")
def campus_statistics_api():
    """
    获取校区维度的统计数据
    
    功能：返回各校区的实验室数量、预约数量等
    
    数据范围：
        - 系统管理员：返回所有校区的统计
        - 实验室管理员：只返回自己校区的统计
    
    返回示例：
        [
            {
                "campus_id": 1,
                "campus_name": "本部校区",
                "lab_count": 8,           // 实验室数量
                "reservation_count": 120, // 预约总数
                "equipment_count": 50     // 设备总数
            },
            {
                "campus_id": 2,
                "campus_name": "东校区",
                "lab_count": 7,
                "reservation_count": 95,
                "equipment_count": 45
            }
        ]
    """
    # 获取当前登录用户
    current_user = get_current_user()
    
    # 确定统计范围
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    
    # 调用服务层获取校区统计数据
    result = get_campus_statistics(campus_id=campus_id)
    
    return success(result)


# ==================== 实验室使用率统计 ====================
@statistics_bp.get("/statistics/lab_usage")
@role_required("lab_admin", "system_admin")
def lab_usage_api():
    """
    获取实验室使用率统计数据
    
    功能：返回各实验室的使用频率、预约时长等指标
    
    数据范围：
        - 系统管理员：查看所有实验室
        - 实验室管理员：只查看自己校区的实验室
    
    返回示例：
        [
            {
                "lab_id": 1,
                "lab_name": "计算机实验室A",
                "campus_name": "本部校区",
                "total_reservations": 45,    // 总预约次数
                "total_hours": 180,          // 总使用时长（小时）
                "usage_rate": 0.68,          // 使用率（68%）
                "avg_duration": 4.0          // 平均每次使用时长（小时）
            },
            {
                "lab_id": 2,
                "lab_name": "电子实验室B",
                "campus_name": "本部校区",
                "total_reservations": 32,
                "total_hours": 128,
                "usage_rate": 0.52,
                "avg_duration": 4.0
            }
        ]
    """
    # 获取当前登录用户
    current_user = get_current_user()
    
    # 确定统计范围
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    
    # 调用服务层获取实验室使用率数据
    result = get_lab_usage(campus_id=campus_id)
    
    return success(result)


@statistics_bp.get("/statistics/daily-report/overview")
@role_required("lab_admin", "system_admin")
def daily_report_overview_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    return success(get_daily_report_overview(campus_id=campus_id))


@statistics_bp.get("/statistics/daily-report/campus")
@role_required("lab_admin", "system_admin")
def daily_report_campus_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    return success(get_daily_report_campus_statistics(campus_id=campus_id))


@statistics_bp.get("/statistics/daily-report/lab")
@role_required("lab_admin", "system_admin")
def daily_report_lab_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    return success(get_daily_report_lab_statistics(campus_id=campus_id))


@statistics_bp.post("/statistics/summary/sync")
@role_required("system_admin")
def sync_summary_api():
    current_user = get_current_user()
    result = sync_summary_for_system_admin(current_user)
    return success(result, "中心汇总总表同步完成")


@statistics_bp.get("/statistics/summary/latest")
@role_required("lab_admin", "system_admin")
def latest_summary_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    result = get_latest_campus_summary_rows(campus_id=campus_id)
    return success(result)
