"""通知与提醒路由"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.notification_service import (
    check_deadline_reminders,
    suggest_reschedule,
    generate_daily_summary,
    generate_weekly_summary,
    check_and_notify_conflicts
)
from app.models.notification_model import (
    get_user_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class ReminderRequest(BaseModel):
    user_id: Optional[int] = 1
    hours_before: Optional[int] = 6


class RescheduleRequest(BaseModel):
    task_id: int
    user_id: Optional[int] = 1


class SummaryRequest(BaseModel):
    user_id: Optional[int] = 1
    date: Optional[str] = None
    week_offset: Optional[int] = 0


# ==================== 原有接口 ====================

@router.get("/reminders")
def get_reminders(user_id: int = 1, hours_before: int = 6):
    """获取即将到期的任务提醒"""
    try:
        reminders = check_deadline_reminders(user_id, hours_before)

        return {
            "success": True,
            "count": len(reminders),
            "reminders": reminders
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提醒失败: {str(e)}")


@router.post("/reschedule-suggestion")
def get_reschedule_suggestion(request: RescheduleRequest):
    """获取任务重排建议"""
    try:
        from app.models.task_model import get_task_by_id, get_all_tasks

        task = get_task_by_id(request.task_id, request.user_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        existing_tasks = [
            t.to_dict() for t in get_all_tasks(request.user_id)
            if t.id != request.task_id
        ]

        suggestion = suggest_reschedule(task.to_dict(), existing_tasks, request.user_id)

        return {
            "success": suggestion["success"],
            **suggestion
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成建议失败: {str(e)}")


@router.get("/daily-summary")
def get_daily_summary(user_id: int = 1, date: Optional[str] = None):
    """获取每日日程摘要"""
    try:
        summary = generate_daily_summary(user_id, date)

        if summary["success"]:
            return summary
        else:
            raise HTTPException(status_code=500, detail=summary["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成摘要失败: {str(e)}")


@router.get("/weekly-summary")
def get_weekly_summary(user_id: int = 1, week_offset: int = 0):
    """获取每周日程摘要"""
    try:
        summary = generate_weekly_summary(user_id, week_offset)

        if summary["success"]:
            return summary
        else:
            raise HTTPException(status_code=500, detail=summary["message"])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成摘要失败: {str(e)}")


@router.get("/conflicts")
def get_conflicts(user_id: int = 1):
    """检测并获取所有冲突及建议"""
    try:
        result = check_and_notify_conflicts(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测冲突失败: {str(e)}")


# ==================== 新增：通知持久化接口 ====================

@router.get("/")
def get_notifications(
    user_id: int,
    limit: int = 100,
    unread_only: bool = False
):
    """获取用户通知列表（仅返回最近7天的通知）"""
    try:
        notifications = get_user_notifications(user_id, limit, unread_only)
        
        if notifications:
            print(f"🔍 返回的通知数据示例: {notifications[0]}")
        
        return {
            "success": True,
            "count": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{notification_id}/read")
def mark_as_read(notification_id: int, user_id: int):
    """标记单个通知为已读"""
    try:
        success = mark_notification_as_read(notification_id, user_id)
        if success:
            return {"success": True, "message": "通知已标记为已读"}
        else:
            raise HTTPException(status_code=404, detail="通知不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read-all")
def mark_all_read(user_id: int = Query(..., description="用户ID")):
    """标记所有通知为已读"""
    try:
        count = mark_all_notifications_as_read(user_id)
        return {
            "success": True,
            "message": f"已标记 {count} 条通知为已读",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, user_id: int = Query(..., description="用户ID")):
    """删除单个通知"""
    try:
        from app.models.notification_model import delete_notification
        
        success = delete_notification(notification_id, user_id)
        if success:
            return {"success": True, "message": "通知已删除"}
        else:
            raise HTTPException(status_code=404, detail="通知不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-all")
def clear_all_notifications(user_id: int = Query(..., description="用户ID")):
    """清空用户的所有通知（7天内的）"""
    try:
        from app.models.notification_model import clear_user_notifications
        
        count = clear_user_notifications(user_id)
        return {
            "success": True,
            "message": f"已清空 {count} 条通知",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
