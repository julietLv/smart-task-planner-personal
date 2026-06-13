"""
周报数据处理器 - 使用 Pandas 进行数据分析
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app.models.task_model import get_all_tasks


def query_tasks_for_report(user_id: int, time_range: str = 'this_week') -> pd.DataFrame:
    """
    查询任务数据并转为 DataFrame

    Args:
        user_id: 用户ID
        time_range: 时间范围 (this_week/last_week/this_month)

    Returns:
        DataFrame with columns: task_id, title, start_time, end_time, status, priority, type, duration
    """
    all_tasks = get_all_tasks(user_id)

    # 过滤时间范围
    now = datetime.now()
    if time_range == 'this_week':
        start_date = now - timedelta(days=now.weekday())
        end_date = start_date + timedelta(days=6)
    elif time_range == 'last_week':
        start_date = now - timedelta(days=now.weekday() + 7)
        end_date = start_date + timedelta(days=6)
    elif time_range == 'this_month':
        start_date = now.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    else:
        start_date = now - timedelta(days=7)
        end_date = now

    # 过滤任务
    tasks = []
    for task in all_tasks:
        if task.start_time:
            task_date = datetime.fromisoformat(task.start_time)
            if start_date <= task_date <= end_date:
                tasks.append({
                    'task_id': task.id,
                    'title': task.title,
                    'start_time': task.start_time,
                    'end_time': task.end_time,
                    'status': task.status,
                    'priority': task.priority,
                    'type': getattr(task, 'type', 'other'),
                    'duration': getattr(task, 'duration', 60)
                })

    return pd.DataFrame(tasks) if tasks else pd.DataFrame()


def calculate_statistics(tasks_df: pd.DataFrame) -> Dict[str, Any]:
    """
    计算周报核心指标

    Args:
        tasks_df: DataFrame with columns:
            - task_id, title, start_time, end_time, status, priority, type, duration
    """
    total = len(tasks_df)
    if total == 0:
        return {
            'total': 0,
            'completed': 0,
            'overdue': 0,
            'in_progress': 0,
            'completed_rate': 0.0,
            'overtime_rate': 0.0,
            'total_hours': 0,
            'error': '无任务数据'
        }

    # 基础统计
    completed = len(tasks_df[tasks_df['status'] == 'done'])
    overdue = len(tasks_df[tasks_df['status'] == 'overdue'])
    in_progress = len(tasks_df[tasks_df['status'] == 'pending'])

    # 完成率
    completed_rate = completed / total

    # 超时率
    overtime_rate = overdue / total

    # 总工作时长（分钟转小时）
    total_minutes = tasks_df['duration'].sum() if 'duration' in tasks_df.columns else total * 60
    total_hours = total_minutes / 60

    # 日均任务数
    days_in_period = 7
    daily_avg = total / days_in_period

    # 优先级分布
    priority_dist = tasks_df['priority'].value_counts().to_dict() if 'priority' in tasks_df.columns else {}

    # 任务类型分布
    type_dist = tasks_df['type'].value_counts().to_dict() if 'type' in tasks_df.columns else {}

    return {
        'total': total,
        'completed': completed,
        'overdue': overdue,
        'in_progress': in_progress,
        'completed_rate': completed_rate,
        'overtime_rate': overtime_rate,
        'total_hours': round(total_hours, 1),
        'daily_avg': round(daily_avg, 1),
        'priority_distribution': priority_dist,
        'type_distribution': type_dist
    }


def analyze_user_habit(tasks_df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析用户习惯和偏好变化
    """
    if len(tasks_df) == 0:
        return {
            'habit_completion': {},
            'type_distribution': {},
            'consistency_score': 0
        }

    # 习惯完成率（特定类型的任务）
    habit_types = ['exercise', 'reading', 'early_rise', 'study']
    habit_completion = {}

    for habit_type in habit_types:
        type_tasks = tasks_df[tasks_df['type'] == habit_type] if 'type' in tasks_df.columns else pd.DataFrame()
        if len(type_tasks) > 0:
            completed = len(type_tasks[type_tasks['status'] == 'done'])
            total = len(type_tasks)
            habit_completion[habit_type] = {
                'completed': completed,
                'total': total,
                'rate': round(completed / total, 2)
            }

    # 任务类型分布
    type_distribution = tasks_df['type'].value_counts().to_dict() if 'type' in tasks_df.columns else {}

    # 一致性评分（简化版：基于按时完成率）
    on_time_tasks = len(tasks_df[tasks_df['status'] == 'done'])
    consistency_score = on_time_tasks / len(tasks_df) if len(tasks_df) > 0 else 0

    return {
        'habit_completion': habit_completion,
        'type_distribution': type_distribution,
        'consistency_score': round(consistency_score, 2)
    }


def calculate_daily_trend(tasks_df: pd.DataFrame) -> Dict[str, Any]:
    """
    计算每日完成趋势
    """
    if len(tasks_df) == 0:
        return {
            'labels': [],
            'values': [],
            'daily_data': []
        }

    # 按日期分组
    tasks_df['date'] = pd.to_datetime(tasks_df['start_time']).dt.date
    daily_stats = tasks_df.groupby('date').agg({
        'task_id': 'count',
        'status': lambda x: (x == 'done').sum()
    }).rename(columns={'task_id': 'total', 'status': 'completed'})

    # 生成7天数据
    labels = []
    values = []
    daily_data = []

    today = datetime.now().date()
    for i in range(7):
        date = today - timedelta(days=6-i)
        date_str = date.strftime('%Y-%m-%d')
        day_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date.weekday()]

        if date in daily_stats.index:
            completed = daily_stats.loc[date, 'completed']
            total = daily_stats.loc[date, 'total']
        else:
            completed = 0
            total = 0

        labels.append(day_name)
        values.append(completed)
        daily_data.append({
            'date': date_str,
            'day': day_name,
            'completed': completed,
            'total': total,
            'overdue': 0  # 可以进一步优化
        })

    return {
        'labels': labels,
        'values': values,
        'daily_data': daily_data
    }
