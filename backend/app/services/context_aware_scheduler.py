"""
上下文感知排程服务 - 基于历史完成情况调整排程策略

核心功能：
1. 计算用户近期任务完成率
2. 根据完成率动态调整排程参数（缓冲时间、每日最大任务数等）
3. 记录用户的实际工作节奏，优化次日排程
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from app.models.task_model import get_all_tasks


def get_completion_rate(user_id: int = 1, days: int = 7) -> Dict:
    """
    计算用户最近N天的任务完成率

    Args:
        user_id: 用户ID
        days: 统计天数

    Returns:
        {
            "completion_rate": 0.75,  # 完成率 (0-1)
            "total_tasks": 20,         # 总任务数
            "completed_tasks": 15,     # 已完成数
            "overdue_tasks": 3,        # 超时数
            "cancelled_tasks": 2,      # 取消数
            "daily_average": 2.86,     # 日均任务数
            "trend": "improving"       # 趋势: improving/stable/declining
        }
    """
    try:
        all_tasks = get_all_tasks(user_id)

        if not all_tasks:
            return {
                "completion_rate": 0.0,
                "total_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "cancelled_tasks": 0,
                "daily_average": 0.0,
                "trend": "unknown",
                "period_days": days
            }

        # 计算时间范围
        now = datetime.now()
        start_date = now - timedelta(days=days)

        # 过滤最近N天的任务
        recent_tasks = []
        for task in all_tasks:
            try:
                created_at = datetime.fromisoformat(
                    task.created_at.replace('T', ' ') if 'T' in task.created_at else task.created_at)
                if created_at >= start_date:
                    recent_tasks.append(task)
            except:
                continue

        if not recent_tasks:
            return {
                "completion_rate": 0.0,
                "total_tasks": 0,
                "completed_tasks": 0,
                "overdue_tasks": 0,
                "cancelled_tasks": 0,
                "daily_average": 0.0,
                "trend": "unknown",
                "period_days": days
            }

        # 统计各状态任务数
        total = len(recent_tasks)
        completed = len([t for t in recent_tasks if t.status == "done"])
        overdue = len([t for t in recent_tasks if t.status == "overdue"])
        cancelled = len([t for t in recent_tasks if t.status == "cancelled"])
        pending = len([t for t in recent_tasks if t.status == "pending"])

        # 计算完成率（排除已取消的任务）
        active_tasks = total - cancelled
        completion_rate = (completed / active_tasks) if active_tasks > 0 else 0.0

        # 计算日均任务数
        daily_average = total / days

        # 分析趋势（对比前半段和后半段）
        mid_point = start_date + timedelta(days=days / 2)
        first_half_completed = 0
        first_half_total = 0
        second_half_completed = 0
        second_half_total = 0

        for task in recent_tasks:
            try:
                created_at = datetime.fromisoformat(
                    task.created_at.replace('T', ' ') if 'T' in task.created_at else task.created_at)
                if created_at < mid_point:
                    first_half_total += 1
                    if task.status == "done":
                        first_half_completed += 1
                else:
                    second_half_total += 1
                    if task.status == "done":
                        second_half_completed += 1
            except:
                continue

        # 判断趋势
        first_half_rate = (first_half_completed / first_half_total) if first_half_total > 0 else 0
        second_half_rate = (second_half_completed / second_half_total) if second_half_total > 0 else 0

        if second_half_rate > first_half_rate + 0.1:
            trend = "improving"
        elif second_half_rate < first_half_rate - 0.1:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "completion_rate": round(completion_rate, 2),
            "total_tasks": total,
            "completed_tasks": completed,
            "overdue_tasks": overdue,
            "cancelled_tasks": cancelled,
            "pending_tasks": pending,
            "daily_average": round(daily_average, 2),
            "trend": trend,
            "period_days": days,
            "first_half_rate": round(first_half_rate, 2),
            "second_half_rate": round(second_half_rate, 2)
        }

    except Exception as e:
        print(f"❌ 计算完成率失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "completion_rate": 0.0,
            "error": str(e)
        }


def get_context_aware_preferences(user_id: int = 1) -> Dict:
    """
    基于历史完成情况获取上下文感知的排程偏好

    核心逻辑：
    - 完成率低 → 增加缓冲时间，减少每日任务密度
    - 完成率高 → 可以更紧凑的排程
    - 趋势下降 → 需要减轻负荷
    - 趋势上升 → 可以适当增加挑战

    Args:
        user_id: 用户ID

    Returns:
        调整后的偏好配置
    """
    try:
        from app.models.task_model import get_user_preferences

        # 获取基础偏好
        preferences = get_user_preferences(user_id)
        if not preferences:
            from app.models.task_model import create_user_preferences
            preferences = create_user_preferences(user_id)

        prefs_dict = preferences.to_dict()

        # 获取完成率数据（最近7天）
        completion_data = get_completion_rate(user_id, days=7)

        if completion_data.get("error"):
            print(f"⚠️ 无法获取完成率数据，使用默认偏好")
            return prefs_dict

        completion_rate = completion_data["completion_rate"]
        trend = completion_data["trend"]
        daily_average = completion_data["daily_average"]

        # 基础缓冲时间（来自用户配置或默认15分钟）
        base_buffer = prefs_dict.get("task_buffer_minutes", 15)

        # ==================== 动态调整策略 ====================

        # 1. 根据完成率调整缓冲时间
        if completion_rate < 0.4:
            # 完成率很低，大幅增加缓冲
            buffer_multiplier = 2.0
            adjustment_reason = "完成率较低，增加缓冲时间"
        elif completion_rate < 0.6:
            # 完成率偏低，适度增加缓冲
            buffer_multiplier = 1.5
            adjustment_reason = "完成率偏低，适度增加缓冲"
        elif completion_rate > 0.85:
            # 完成率很高，可以减少缓冲
            buffer_multiplier = 0.7
            adjustment_reason = "完成率高，可以紧凑排程"
        else:
            # 正常范围，保持默认
            buffer_multiplier = 1.0
            adjustment_reason = "完成率正常，使用标准缓冲"

        # 2. 根据趋势微调
        if trend == "declining":
            buffer_multiplier *= 1.2  # 趋势下降，再增加20%缓冲
            adjustment_reason += "，且趋势下降"
        elif trend == "improving":
            buffer_multiplier *= 0.9  # 趋势上升，可以减少10%缓冲
            adjustment_reason += "，且趋势上升"

        # 计算最终缓冲时间（限制在5-60分钟范围内）
        adjusted_buffer = int(base_buffer * buffer_multiplier)
        adjusted_buffer = max(5, min(60, adjusted_buffer))

        # 3. 根据日均任务数调整建议的最大每日任务数
        if daily_average > 8:
            max_daily_tasks = 10  # 高负荷用户
        elif daily_average > 5:
            max_daily_tasks = 8  # 中等负荷
        else:
            max_daily_tasks = 6  # 低负荷用户

        # 4. 如果完成率过低，主动限制每日任务数
        if completion_rate < 0.5:
            max_daily_tasks = min(max_daily_tasks, 5)
            adjustment_reason += "，限制每日任务数"

        adjusted_prefs = {
            **prefs_dict,
            "task_buffer_minutes": adjusted_buffer,
            "max_daily_tasks": max_daily_tasks,
            "context_adjustment": {
                "completion_rate": completion_rate,
                "trend": trend,
                "daily_average": daily_average,
                "adjustment_reason": adjustment_reason,
                "original_buffer": base_buffer,
                "adjusted_buffer": adjusted_buffer
            }
        }

        print(f"🧠 上下文感知调整: 完成率={completion_rate:.0%}, 趋势={trend}")
        print(f"   缓冲时间: {base_buffer}分钟 → {adjusted_buffer}分钟")
        print(f"   原因: {adjustment_reason}")

        return adjusted_prefs

    except Exception as e:
        print(f"❌ 获取上下文感知偏好失败: {e}")
        import traceback
        traceback.print_exc()
        # 返回原始偏好
        from app.models.task_model import get_user_preferences
        preferences = get_user_preferences(user_id)
        return preferences.to_dict() if preferences else {}


def apply_context_to_scheduling(task_info: Dict, user_id: int = 1) -> Dict:
    """
    将上下文信息应用到任务排程中

    Args:
        task_info: 任务信息
        user_id: 用户ID

    Returns:
        增强后的任务信息
    """
    try:
        context_prefs = get_context_aware_preferences(user_id)

        enhanced_task = task_info.copy()

        # 添加上下文调整信息
        if "context_adjustment" in context_prefs:
            enhanced_task["context_info"] = context_prefs["context_adjustment"]

            # 如果有缓冲时间调整，添加到任务信息中
            if "task_buffer_minutes" in context_prefs:
                enhanced_task["buffer_minutes"] = context_prefs["task_buffer_minutes"]

        print(f"✅ 已应用上下文感知调整到任务: {task_info.get('title', '未命名')}")

        return enhanced_task

    except Exception as e:
        print(f"⚠️ 应用上下文失败: {e}")
        return task_info


def get_productivity_insights(user_id: int = 1) -> Dict:
    """
    生成生产力洞察报告（用于前端展示）

    Args:
        user_id: 用户ID

    Returns:
        洞察力报告
    """
    try:
        # 获取不同时间段的完成率
        completion_7d = get_completion_rate(user_id, days=7)
        completion_14d = get_completion_rate(user_id, days=14)
        completion_30d = get_completion_rate(user_id, days=30)

        insights = []

        # 分析1: 短期趋势
        if completion_7d["trend"] == "improving":
            insights.append({
                "type": "positive",
                "icon": "📈",
                "message": "你的完成率正在提升！继续保持～"
            })
        elif completion_7d["trend"] == "declining":
            insights.append({
                "type": "warning",
                "icon": "⚠️",
                "message": "最近完成率有所下降，建议适当减少任务量"
            })

        # 分析2: 负荷评估
        daily_avg = completion_7d["daily_average"]
        if daily_avg > 8:
            insights.append({
                "type": "info",
                "icon": "💪",
                "message": f"你平均每天处理{daily_avg:.1f}个任务，工作量很大！注意休息"
            })
        elif daily_avg < 3:
            insights.append({
                "type": "suggestion",
                "icon": "💡",
                "message": "当前任务量较少，可以适当增加一些计划"
            })

        # 分析3: 完成率评估
        rate = completion_7d["completion_rate"]
        if rate > 0.8:
            insights.append({
                "type": "positive",
                "icon": "🎯",
                "message": f"完成率{rate:.0%}，效率很高！"
            })
        elif rate < 0.5:
            insights.append({
                "type": "warning",
                "icon": "🔧",
                "message": f"完成率{rate:.0%}，建议调整排程策略"
            })

        return {
            "success": True,
            "insights": insights,
            "completion_stats": {
                "last_7_days": completion_7d,
                "last_14_days": completion_14d,
                "last_30_days": completion_30d
            }
        }

    except Exception as e:
        print(f"❌ 生成洞察力报告失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }
