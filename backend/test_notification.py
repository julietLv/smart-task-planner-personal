"""测试通知服务"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.notification_service import (
    check_deadline_reminders,
    suggest_reschedule,
    generate_daily_summary,
    generate_weekly_summary,
    check_and_notify_conflicts
)
from app.models.task_model import create_task, get_all_tasks
from datetime import datetime, timedelta

print("=" * 60)
print("测试通知服务")
print("=" * 60)

# 准备测试数据
user_id = 1
now = datetime.now()

print("\n【准备】创建测试任务...")

# 创建一些测试任务
task1 = create_task(
    title="紧急会议",
    user_id=user_id,
    duration=60,
    deadline=(now + timedelta(hours=2)).isoformat(),  # 2小时后到期
    priority="high",
    start_time=(now + timedelta(hours=1)).isoformat(),
    end_time=(now + timedelta(hours=2)).isoformat()
)
print(f"✅ 创建任务1: {task1.title} (2小时后到期)")

task2 = create_task(
    title="完成报告",
    user_id=user_id,
    duration=120,
    deadline=(now + timedelta(hours=5)).isoformat(),  # 5小时后到期
    priority="medium",
    start_time=(now + timedelta(hours=3)).isoformat(),
    end_time=(now + timedelta(hours=5)).isoformat()
)
print(f"✅ 创建任务2: {task2.title} (5小时后到期)")

task3 = create_task(
    title="阅读文档",
    user_id=user_id,
    duration=90,
    deadline=(now + timedelta(days=2)).isoformat(),  # 2天后到期
    priority="low",
    start_time=(now + timedelta(days=1)).isoformat(),
    end_time=(now + timedelta(days=1, hours=1, minutes=30)).isoformat()
)
print(f"✅ 创建任务3: {task3.title} (2天后到期)")

# 创建一个已过期的任务
task4 = create_task(
    title="过期任务",
    user_id=user_id,
    duration=30,
    deadline=(now - timedelta(hours=1)).isoformat(),  # 1小时前已过期
    priority="high",
    start_time=(now - timedelta(hours=2)).isoformat(),
    end_time=(now - timedelta(hours=1, minutes=30)).isoformat()
)
print(f"✅ 创建任务4: {task4.title} (已过期)")

# 测试1：检查到期提醒
print("\n" + "=" * 60)
print("【测试1】检查到期提醒...")
print("=" * 60)
reminders = check_deadline_reminders(user_id, hours_before=6)
print(f"\n找到 {len(reminders)} 个提醒:")
for i, reminder in enumerate(reminders, 1):
    print(f"\n{i}. {reminder['message']}")
    print(f"   状态: {reminder['status']}")
    print(f"   优先级: {reminder['priority']}")
    if 'remaining_hours' in reminder:
        print(f"   剩余时间: {reminder['remaining_hours']:.1f}小时")
    elif 'overdue_hours' in reminder:
        print(f"   已过期: {reminder['overdue_hours']:.1f}小时")

# 测试2：生成每日摘要
print("\n" + "=" * 60)
print("【测试2】生成今日日程摘要...")
print("=" * 60)
daily_summary = generate_daily_summary(user_id)
if daily_summary["success"]:
    print(f"\n{daily_summary['summary']}")
    print(f"\n📊 统计信息:")
    print(f"   总任务数: {daily_summary['stats']['total_tasks']}")
    print(f"   待完成: {daily_summary['stats']['pending_tasks']}")
    print(f"   已完成: {daily_summary['stats']['done_tasks']}")
    print(f"   总时长: {daily_summary['stats']['total_duration_minutes']}分钟")
else:
    print(f"❌ 失败: {daily_summary['message']}")

# 测试3：生成每周摘要
print("\n" + "=" * 60)
print("【测试3】生成本周日程摘要...")
print("=" * 60)
weekly_summary = generate_weekly_summary(user_id, week_offset=0)
if weekly_summary["success"]:
    print(f"\n{weekly_summary['summary']}")
    print(f"\n📊 统计信息:")
    print(f"   总任务数: {weekly_summary['stats']['total_tasks']}")
    print(f"   活跃天数: {weekly_summary['stats']['active_days']}")
    print(f"   总时长: {weekly_summary['stats']['total_duration_minutes']}分钟")
else:
    print(f"❌ 失败: {weekly_summary['message']}")

# 测试4：检测冲突
print("\n" + "=" * 60)
print("【测试4】检测时间冲突...")
print("=" * 60)
conflict_result = check_and_notify_conflicts(user_id)
print(f"\n{conflict_result['message']}")
if conflict_result["conflict_count"] > 0:
    print(f"\n发现 {conflict_result['conflict_count']} 个冲突:")
    for i, conflict in enumerate(conflict_result["conflicts"], 1):
        print(f"\n{i}. 冲突详情:")
        print(f"   任务1: {conflict['task1']['title']}")
        print(f"   任务2: {conflict['task2']['title']}")

        # 显示重排建议
        if i <= len(conflict_result["suggestions"]):
            suggestion = conflict_result["suggestions"][i - 1]
            if suggestion["success"]:
                print(f"   💡 建议: {suggestion['message']}")
            else:
                print(f"   ⚠️ 无法重排: {suggestion['message']}")
else:
    print("✅ 没有时间冲突")

# 测试5：重排建议
print("\n" + "=" * 60)
print("【测试5】测试重排建议...")
print("=" * 60)
existing_tasks = [t.to_dict() for t in get_all_tasks(user_id)]
if existing_tasks:
    test_task = existing_tasks[0]
    print(f"\n为任务「{test_task['title']}」生成重排建议...")
    suggestion = suggest_reschedule(test_task, existing_tasks, user_id)

    if suggestion["success"]:
        print(f"\n✅ {suggestion['message']}")
        print(f"   建议时间: {suggestion['suggested_time']['readable']}")
        if suggestion.get("alternative_slots"):
            print(f"   备选时间段数量: {len(suggestion['alternative_slots'])}")
    else:
        print(f"\n❌ {suggestion['message']}")
        if "reason" in suggestion:
            print(f"   原因: {suggestion['reason']}")
else:
    print("没有现有任务可供测试")

print("\n" + "=" * 60)
print("🎉 所有测试完成！")
print("=" * 60)
