"""通知服务 - 冲突检测与主动提醒"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.task_model import get_all_tasks, get_user_preferences
from app.services.scheduler_service import schedule_task, parse_time


def check_deadline_reminders(user_id: int = 1, hours_before: int = 6) -> List[Dict]:
    """
    检测即将到期的任务（deadline前指定小时数）

    Args:
        user_id: 用户ID
        hours_before: 提前多少小时提醒，默认6小时

    Returns:
        提醒列表，每个元素包含任务信息和剩余时间
    """
    try:
        # 获取所有待完成任务
        tasks = get_all_tasks(user_id, status="pending")

        reminders = []
        now = datetime.now()

        for task in tasks:
            if not task.deadline:
                continue

            deadline = parse_time(task.deadline)
            if not deadline:
                continue

            # 计算剩余时间
            time_remaining = deadline - now

            # 如果任务已过期
            if time_remaining.total_seconds() < 0:
                reminder = {
                    "task_id": task.id,
                    "title": task.title,
                    "deadline": task.deadline,
                    "status": "overdue",
                    "message": f"⚠️ 任务「{task.title}」已过期！",
                    "overdue_hours": abs(time_remaining.total_seconds()) / 3600,
                    "priority": task.priority,
                    "notification_type": "urgent"  # ✅ 紧急通知
                }
                reminders.append(reminder)
                
                # ✅ 实时推送紧急通知
                _push_urgent_notification(reminder, user_id)
                
            # 如果任务即将到期（在提醒时间范围内）
            elif time_remaining.total_seconds() <= hours_before * 3600:
                remaining_hours = time_remaining.total_seconds() / 3600

                # 根据剩余时间生成不同的提醒消息
                if remaining_hours < 1:
                    remaining_minutes = int(remaining_hours * 60)
                    message = f"⏰ 紧急！任务「{task.title}」将在{remaining_minutes}分钟后到期"
                    notification_type = "urgent"  # ✅ 1小时内为紧急
                elif remaining_hours < 24:
                    message = f"⏰ 提醒：任务「{task.title}」将在{int(remaining_hours)}小时后到期"
                    notification_type = "normal"  # ✅ 24小时内为普通
                else:
                    days = int(remaining_hours / 24)
                    hours = int(remaining_hours % 24)
                    message = f"📅 提示：任务「{task.title}」将在{days}天{hours}小时后到期"
                    notification_type = "info"  # ✅ 超过24小时为信息

                reminder = {
                    "task_id": task.id,
                    "title": task.title,
                    "deadline": task.deadline,
                    "status": "upcoming",
                    "message": message,
                    "remaining_hours": remaining_hours,
                    "priority": task.priority,
                    "notification_type": notification_type  # ✅ 添加通知类型
                }
                reminders.append(reminder)
                
                # ✅ 如果是紧急通知，实时推送
                if notification_type == "urgent":
                    _push_urgent_notification(reminder, user_id)

        # 按优先级和紧急程度排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        reminders.sort(key=lambda x: (
            0 if x["status"] == "overdue" else 1,  # 过期的优先
            priority_order.get(x["priority"], 1),  # 高优先级优先
            x.get("remaining_hours", 0)  # 剩余时间少的优先
        ))

        return reminders

    except Exception as e:
        print(f"检查到期提醒时出错: {e}")
        return []


def _push_urgent_notification(reminder: Dict, user_id: int):
    """
    推送紧急通知（通过WebSocket）
    
    Args:
        reminder: 提醒数据
        user_id: 用户ID
    """
    try:
        import asyncio
        from app.services.websocket_service import push_deadline_reminder
        
        # 异步推送（不阻塞主流程）
        asyncio.create_task(push_deadline_reminder(reminder, user_id))
        print(f"🔔 已推送紧急通知: {reminder['title']}")
    except Exception as e:
        print(f"推送通知失败: {e}")


def suggest_reschedule(conflicting_task: Dict, existing_tasks: List[Dict],
                       user_id: int = 1) -> Dict:
    """
    当检测到冲突时，自动给出重排建议

    Args:
        conflicting_task: 冲突的任务信息
        existing_tasks: 已有任务列表
        user_id: 用户ID

    Returns:
        重排建议，包含推荐的新时间段
    """
    try:
        # 获取用户偏好
        preferences = get_user_preferences(user_id)
        prefs_dict = preferences.to_dict()

        # 准备任务信息用于重新排程
        task_info = {
            "title": conflicting_task.get("title", "未命名任务"),
            "duration": conflicting_task.get("duration"),
            "deadline": conflicting_task.get("deadline"),
            "priority": conflicting_task.get("priority", "medium")
        }

        # 如果没有时长信息，使用默认值
        if not task_info["duration"]:
            task_info["duration"] = 60  # 默认1小时

        # 排除当前任务本身
        filtered_tasks = [
            t for t in existing_tasks
            if t.get("id") != conflicting_task.get("id")
        ]

        # 尝试重新排程
        schedule_result = schedule_task(task_info, filtered_tasks, prefs_dict)

        if schedule_result["success"]:
            new_start = schedule_result["scheduled_time"]["start_time"]
            new_end = schedule_result["scheduled_time"]["end_time"]

            # 格式化时间为可读格式
            start_dt = parse_time(new_start)
            weekday_map = {
                0: "周一", 1: "周二", 2: "周三",
                3: "周四", 4: "周五", 5: "周六", 6: "周日"
            }
            weekday = weekday_map[start_dt.weekday()]
            time_str = f"{start_dt.hour:02d}:{start_dt.minute:02d}"

            suggestion = {
                "success": True,
                "original_task": conflicting_task,
                "suggested_time": {
                    "start_time": new_start,
                    "end_time": new_end,
                    "readable": f"{weekday} {time_str}"
                },
                "message": f"💡 建议：将任务「{task_info['title']}」移到{weekday}{time_str}",
                "alternative_slots": schedule_result.get("alternative_slots", [])
            }

            # 如果有备选时间段，也提供
            if schedule_result.get("alternative_slots"):
                alt_count = len(schedule_result["alternative_slots"])
                suggestion["message"] += f"\n还有{alt_count}个其他可选时间段"

            return suggestion
        else:
            return {
                "success": False,
                "message": f"❌ 无法为重排找到合适的时间段",
                "reason": schedule_result.get("message", "未知原因"),
                "suggestions": schedule_result.get("suggestions", [
                    "尝试调整任务的截止时间",
                    "减少任务时长",
                    "取消或重新安排一些已有任务"
                ])
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"生成重排建议时出错: {str(e)}"
        }


def generate_daily_summary(user_id: int = 1, date: Optional[str] = None) -> Dict:
    """
    生成每日日程摘要

    Args:
        user_id: 用户ID
        date: 指定日期（ISO格式），默认为今天

    Returns:
        每日摘要，包含当天的任务安排
    """
    try:
        # 确定查询的日期
        if date:
            target_date = parse_time(date).date()
        else:
            target_date = datetime.now().date()

        # 获取所有任务
        all_tasks = get_all_tasks(user_id)

        # 筛选出目标日期的任务
        day_tasks = []
        for task in all_tasks:
            if task.start_time:
                task_date = parse_time(task.start_time).date()
                if task_date == target_date:
                    day_tasks.append(task)

        # 按开始时间排序
        day_tasks.sort(key=lambda t: t.start_time or "")

        # 统计信息
        total_tasks = len(day_tasks)
        pending_tasks = [t for t in day_tasks if t.status == "pending"]
        done_tasks = [t for t in day_tasks if t.status == "done"]

        # 计算总工作时长
        total_duration = sum(t.duration or 0 for t in day_tasks)

        # 生成摘要文本
        date_str = target_date.strftime("%Y年%m月%d日")
        weekday_map = {
            0: "星期一", 1: "星期二", 2: "星期三",
            3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"
        }
        weekday = weekday_map[target_date.weekday()]

        summary_lines = [
            f"📅 {date_str} ({weekday}) 日程摘要",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 总任务数: {total_tasks} | 待完成: {len(pending_tasks)} | 已完成: {len(done_tasks)}",
            f"⏱️ 预计工作时长: {total_duration}分钟 ({total_duration / 60:.1f}小时)",
            ""
        ]

        if day_tasks:
            summary_lines.append("📋 今日任务安排:")
            for i, task in enumerate(day_tasks, 1):
                time_info = ""
                if task.start_time and task.end_time:
                    start_t = parse_time(task.start_time)
                    end_t = parse_time(task.end_time)
                    time_info = f" [{start_t.strftime('%H:%M')}-{end_t.strftime('%H:%M')}]"

                status_icon = "✅" if task.status == "done" else "⏳"
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")

                summary_lines.append(
                    f"  {i}. {status_icon} {priority_icon} {task.title}{time_info}"
                )
                if task.description:
                    summary_lines.append(f"     💬 {task.description}")
        else:
            summary_lines.append("✨ 今天没有安排任务，好好休息吧！")

        summary_text = "\n".join(summary_lines)

        return {
            "success": True,
            "date": target_date.isoformat(),
            "summary": summary_text,
            "stats": {
                "total_tasks": total_tasks,
                "pending_tasks": len(pending_tasks),
                "done_tasks": len(done_tasks),
                "total_duration_minutes": total_duration
            },
            "tasks": [t.to_dict() for t in day_tasks]
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"生成每日摘要时出错: {str(e)}"
        }


def generate_weekly_summary(user_id: int = 1, week_offset: int = 0) -> Dict:
    """
    生成每周日程摘要

    Args:
        user_id: 用户ID
        week_offset: 周偏移量，0表示本周，-1表示上周，1表示下周

    Returns:
        每周摘要
    """
    try:
        now = datetime.now()
        # 计算目标周的起始日期（周一）
        current_weekday = now.weekday()
        target_monday = now.date() - timedelta(days=current_weekday) + timedelta(weeks=week_offset)
        target_sunday = target_monday + timedelta(days=6)

        # 获取所有任务
        all_tasks = get_all_tasks(user_id)

        # 筛选出目标周的任务
        week_tasks = []
        for task in all_tasks:
            if task.start_time:
                task_date = parse_time(task.start_time).date()
                if target_monday <= task_date <= target_sunday:
                    week_tasks.append(task)

        # 按日期分组
        daily_breakdown = {}
        for task in week_tasks:
            task_date = parse_time(task.start_time).date().isoformat()
            if task_date not in daily_breakdown:
                daily_breakdown[task_date] = []
            daily_breakdown[task_date].append(task)

        # 统计信息
        total_tasks = len(week_tasks)
        pending_tasks = [t for t in week_tasks if t.status == "pending"]
        done_tasks = [t for t in week_tasks if t.status == "done"]
        total_duration = sum(t.duration or 0 for t in week_tasks)

        # 生成摘要文本
        week_label = "本周" if week_offset == 0 else ("上周" if week_offset == -1 else "下周")
        summary_lines = [
            f"📆 {week_label}日程摘要 ({target_monday} ~ {target_sunday})",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 总任务数: {total_tasks} | 待完成: {len(pending_tasks)} | 已完成: {len(done_tasks)}",
            f"⏱️ 预计总时长: {total_duration}分钟 ({total_duration / 60:.1f}小时)",
            ""
        ]

        if week_tasks:
            # 按日期输出
            weekday_map = {
                0: "周一", 1: "周二", 2: "周三",
                3: "周四", 4: "周五", 5: "周六", 6: "周日"
            }

            summary_lines.append("📋 每日安排:")
            for date_str in sorted(daily_breakdown.keys()):
                date_obj = datetime.fromisoformat(date_str).date()
                weekday = weekday_map[date_obj.weekday()]
                day_tasks_list = daily_breakdown[date_str]

                summary_lines.append(f"\n  📍 {date_str} ({weekday}) - {len(day_tasks_list)}个任务")
                for task in sorted(day_tasks_list, key=lambda t: t.start_time or ""):
                    status_icon = "✅" if task.status == "done" else "⏳"
                    time_info = ""
                    if task.start_time:
                        time_info = parse_time(task.start_time).strftime(" %H:%M")
                    summary_lines.append(f"    {status_icon} {task.title}{time_info}")
        else:
            summary_lines.append("✨ 这周没有安排任务")

        summary_text = "\n".join(summary_lines)

        return {
            "success": True,
            "week_start": target_monday.isoformat(),
            "week_end": target_sunday.isoformat(),
            "summary": summary_text,
            "stats": {
                "total_tasks": total_tasks,
                "pending_tasks": len(pending_tasks),
                "done_tasks": len(done_tasks),
                "total_duration_minutes": total_duration,
                "active_days": len(daily_breakdown)
            },
            "daily_breakdown": {
                date: [t.to_dict() for t in tasks]
                for date, tasks in daily_breakdown.items()
            }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"生成每周摘要时出错: {str(e)}"
        }


def check_and_notify_conflicts(user_id: int = 1) -> Dict:
    """
    检查并通知所有冲突

    Args:
        user_id: 用户ID

    Returns:
        冲突检测结果和建议
    """
    try:
        from app.services.scheduler_service import detect_conflict

        tasks = get_all_tasks(user_id, status="pending")
        preferences = get_user_preferences(user_id)

        conflicts = []
        suggestions = []

        # 检查每对任务之间的冲突
        for i, task1 in enumerate(tasks):
            if not task1.start_time or not task1.end_time:
                continue

            for j, task2 in enumerate(tasks):
                if i >= j or not task2.start_time or not task2.end_time:
                    continue

                # 检测冲突
                conflict_check = detect_conflict(
                    {"start_time": task1.start_time, "end_time": task1.end_time},
                    [task2.to_dict()],
                    preferences.to_dict()
                )

                if conflict_check["has_conflict"]:
                    conflicts.append({
                        "task1": task1.to_dict(),
                        "task2": task2.to_dict(),
                        "conflicts": conflict_check["conflicts"]
                    })

                    # 为重排较低优先级的任务生成建议
                    lower_priority_task = task2 if task1.priority == "high" else task1
                    suggestion = suggest_reschedule(
                        lower_priority_task.to_dict(),
                        [t.to_dict() for t in tasks if t.id != lower_priority_task.id],
                        user_id
                    )
                    suggestions.append(suggestion)

        return {
            "success": True,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "suggestions": suggestions,
            "message": f"发现{len(conflicts)}个时间冲突" if conflicts else "✅ 没有时间冲突"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"检查冲突时出错: {str(e)}"
        }
