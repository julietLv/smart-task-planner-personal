import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app.models.task_model import create_task


def add_future_tasks():
    """添加未来的测试任务"""
    now = datetime.now()

    # 创建未来几天的测试任务（确保时间正确）
    test_tasks = [
        {
            "title": "明天晨会",
            "description": "团队每日站会",
            "start_time": (now + timedelta(days=1, hours=9)).strftime('%Y-%m-%dT%H:%M:%S'),
            "end_time": (now + timedelta(days=1, hours=9, minutes=30)).strftime('%Y-%m-%dT%H:%M:%S'),
            "priority": "high",
            "duration": 30
        },
        {
            "title": "明天下午编码",
            "description": "完成用户登录功能",
            "start_time": (now + timedelta(days=1, hours=14)).strftime('%Y-%m-%dT%H:%M:%S'),
            "end_time": (now + timedelta(days=1, hours=16)).strftime('%Y-%m-%dT%H:%M:%S'),
            "priority": "medium",
            "duration": 120
        },
        {
            "title": "后天健身",
            "description": "跑步和力量训练",
            "start_time": (now + timedelta(days=2, hours=18)).strftime('%Y-%m-%dT%H:%M:%S'),
            "end_time": (now + timedelta(days=2, hours=19)).strftime('%Y-%m-%dT%H:%M:%S'),
            "priority": "low",
            "duration": 60
        },
        {
            "title": "本周六看电影",
            "description": "放松娱乐",
            "start_time": (now + timedelta(days=5, hours=15)).strftime('%Y-%m-%dT%H:%M:%S'),
            "end_time": (now + timedelta(days=5, hours=17)).strftime('%Y-%m-%dT%H:%M:%S'),
            "priority": "low",
            "duration": 120
        }
    ]

    print("📝 正在添加未来的测试任务...\n")

    for i, task_data in enumerate(test_tasks, 1):
        task = create_task(
            title=task_data["title"],
            user_id=1,
            description=task_data["description"],
            start_time=task_data["start_time"],
            end_time=task_data["end_time"],
            priority=task_data["priority"],
            duration=task_data["duration"]
        )
        print(f"✅ 任务 {i} 已创建: {task.title}")
        print(f"   时间: {task.start_time} - {task.end_time}")
        print(f"   优先级: {task.priority}\n")

    print(f"🎉 成功创建 {len(test_tasks)} 个测试任务！")
    print("💡 刷新浏览器页面，切换到对应日期即可看到这些任务")


if __name__ == "__main__":
    add_future_tasks()
