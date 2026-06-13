"""测试通知推送功能"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.notification_service import (
    check_deadline_reminders,
    generate_daily_summary,
    check_and_notify_conflicts
)
from app.models.task_model import create_task
from datetime import datetime, timedelta


def test_deadline_reminders():
    """测试到期提醒"""
    print("\n" + "=" * 60)
    print("🔔 测试1: 到期提醒功能")
    print("=" * 60)

    # 创建一个即将到期的任务(2小时后)
    deadline = (datetime.now() + timedelta(hours=2)).isoformat()

    task = create_task(
        title="测试任务 - 即将到期",
        user_id=1,
        deadline=deadline,
        duration=60,
        priority="high"
    )

    print(f"✅ 创建任务: {task.title}")
    print(f"   截止时间: {task.deadline}")

    # 检查提醒
    reminders = check_deadline_reminders(user_id=1, hours_before=6)

    print(f"\n📋 找到 {len(reminders)} 个提醒:")
    for reminder in reminders:
        print(f"   • {reminder['title']}")
        print(f"     截止: {reminder['deadline']}")
        
        if reminder['status'] == 'overdue':
            overdue_hours = reminder.get('overdue_hours', 0)
            print(f"     已过期: {overdue_hours:.1f} 小时")
        else:
            remaining_hours = reminder.get('remaining_hours', 0)
            print(f"     剩余: {remaining_hours:.1f} 小时")
        
        print(f"     优先级: {reminder['priority']}")

def test_daily_summary():
    """测试每日摘要"""
    print("\n" + "=" * 60)
    print("📅 测试2: 每日日程摘要")
    print("=" * 60)

    summary = generate_daily_summary(user_id=1)

    if summary["success"]:
        print(f"\n{summary['summary']}")
        print(f"\n📊 统计:")
        stats = summary.get('stats', {})
        print(f"   今日任务: {stats.get('total_tasks', 0)} 个")
        print(f"   待完成: {stats.get('pending_tasks', 0)} 个")
        print(f"   已完成: {stats.get('done_tasks', 0)} 个")
        print(f"   预计时长: {stats.get('total_duration_minutes', 0)} 分钟")
    else:
        print(f"❌ 生成摘要失败: {summary['message']}")

def test_conflict_detection():
    """测试冲突检测"""
    print("\n" + "=" * 60)
    print("⚠️  测试3: 冲突检测与建议")
    print("=" * 60)

    # 创建两个时间重叠的任务
    base_time = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)

    task1 = create_task(
        title="会议A",
        user_id=1,
        start_time=base_time.isoformat(),
        end_time=(base_time + timedelta(hours=1)).isoformat(),
        duration=60,
        priority="medium"
    )

    task2 = create_task(
        title="会议B - 与A冲突",
        user_id=1,
        start_time=base_time.isoformat(),
        end_time=(base_time + timedelta(hours=1)).isoformat(),
        duration=60,
        priority="medium"
    )

    print(f"✅ 创建任务1: {task1.title} ({task1.start_time[11:16]}-{task1.end_time[11:16]})")
    print(f"✅ 创建任务2: {task2.title} ({task2.start_time[11:16]}-{task2.end_time[11:16]})")

    # 检测冲突
    result = check_and_notify_conflicts(user_id=1)

    print(f"\n🔍 检测结果:")
    print(f"   冲突数量: {result.get('conflict_count', 0)}")

    if result.get('conflicts'):
        for i, conflict in enumerate(result['conflicts'], 1):
            print(f"\n   冲突 {i}:")
            if 'conflicts' in conflict:
                conflict_details = conflict['conflicts']
                if isinstance(conflict_details, list):
                    for detail in conflict_details:
                        if isinstance(detail, dict):
                            print(f"     类型: {detail.get('type', '未知')}")
                            print(f"     说明: {detail.get('message', '无详细说明')}")
                        else:
                            print(f"     冲突: {detail}")
                else:
                    print(f"     冲突: {conflict_details}")
            if 'task1' in conflict:
                print(f"     任务1: {conflict['task1']['title']}")
                print(f"     任务2: {conflict['task2']['title']}")

    if result.get('suggestions'):
        print(f"\n💡 建议:")
        for suggestion in result['suggestions']:
            print(f"   • {suggestion}")


if __name__ == "__main__":
    print("\n" + "🚀" * 30)
    print("开始测试通知推送功能...")
    print("🚀" * 30)

    try:
        # 运行所有测试
        test_deadline_reminders()
        test_daily_summary()
        test_conflict_detection()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
