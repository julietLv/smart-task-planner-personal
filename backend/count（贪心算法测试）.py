"""测试贪心排程算法"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scheduler_service import schedule_task_greedy


def test_greedy_scheduling():
    """测试贪心排程算法"""
    print("\n" + "=" * 70)
    print("🧪 测试贪心排程算法")
    print("=" * 70)

    # 模拟已有任务
    existing_tasks = [
        {
            "id": 1,
            "title": "晨会",
            "start_time": (datetime.now().replace(hour=9, minute=0)).isoformat(),
            "end_time": (datetime.now().replace(hour=10, minute=0)).isoformat(),
            "status": "pending"
        },
        {
            "id": 2,
            "title": "午餐会议",
            "start_time": (datetime.now().replace(hour=12, minute=0)).isoformat(),
            "end_time": (datetime.now().replace(hour=13, minute=0)).isoformat(),
            "status": "pending"
        },
        {
            "id": 3,
            "title": "项目评审",
            "start_time": (datetime.now().replace(hour=14, minute=0)).isoformat(),
            "end_time": (datetime.now().replace(hour=16, minute=0)).isoformat(),
            "status": "pending"
        }
    ]

    # 用户偏好
    preferences = {
        "blocked_time_start": "22:00",
        "blocked_time_end": "08:00"
    }

    print(f"\n📋 已有任务:")
    for task in existing_tasks:
        start = datetime.fromisoformat(task['start_time']).strftime('%H:%M')
        end = datetime.fromisoformat(task['end_time']).strftime('%H:%M')
        print(f"   • {task['title']}: {start}-{end}")

    # 测试用例
    test_cases = [
        {
            "name": "测试1: 1小时任务，无截止时间",
            "task": {
                "title": "写报告",
                "duration": 60,
                "priority": "medium"
            }
        },
        {
            "name": "测试2: 2小时任务，高优先级",
            "task": {
                "title": "重要会议",
                "duration": 120,
                "priority": "high"
            }
        },
        {
            "name": "测试3: 30分钟任务，有截止时间",
            "task": {
                "title": "回复邮件",
                "duration": 30,
                "priority": "low",
                "deadline": (datetime.now() + timedelta(days=2)).isoformat()
            }
        },
        {
            "name": "测试4: 时间不足的任务",
            "task": {
                "title": "紧急任务",
                "duration": 480,
                "priority": "high",
                "deadline": (datetime.now() + timedelta(hours=2)).isoformat()
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n{'─' * 70}")
        print(f"{test_case['name']}")
        print(f"{'─' * 70}")

        task_info = test_case['task']
        print(f"任务: {task_info['title']}")
        print(f"时长: {task_info['duration']}分钟")
        print(f"优先级: {task_info.get('priority', 'medium')}")
        if task_info.get('deadline'):
            deadline = datetime.fromisoformat(task_info['deadline'])
            print(f"截止时间: {deadline.strftime('%m-%d %H:%M')}")

        # 执行排程
        result = schedule_task_greedy(task_info, existing_tasks, preferences)

        # 显示结果
        if result['success']:
            print(f"\n✅ 排程成功!")
            start = datetime.fromisoformat(result['scheduled_time']['start_time'])
            end = datetime.fromisoformat(result['scheduled_time']['end_time'])
            print(f"   建议时间: {start.strftime('%m-%d %H:%M')} - {end.strftime('%H:%M')}")

            if result.get('alternative_slots'):
                print(f"\n   备选时间段:")
                for i, alt in enumerate(result['alternative_slots'], 1):
                    alt_start = datetime.fromisoformat(alt['start_time'])
                    alt_end = datetime.fromisoformat(alt['end_time'])
                    print(f"     {i}. {alt_start.strftime('%m-%d %H:%M')} - {alt_end.strftime('%H:%M')}")

            if result.get('search_stats'):
                stats = result['search_stats']
                print(f"\n   搜索统计: 检查了 {stats['slots_checked']} 个时间段, 找到 {stats['alternatives_found']} 个备选")
        else:
            print(f"\n❌ 排程失败!")
            print(f"   原因: {result['message']}")
            if result.get('suggestions'):
                print(f"   建议:")
                for suggestion in result['suggestions']:
                    print(f"     • {suggestion}")

    print("\n" + "=" * 70)
    print("✅ 所有测试完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        test_greedy_scheduling()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
