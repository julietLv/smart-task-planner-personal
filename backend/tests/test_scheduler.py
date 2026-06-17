"""测试排程服务"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.scheduler_service import schedule_task, detect_conflict, optimize_schedule
from datetime import datetime, timedelta

print("=" * 60)
print("测试排程服务")
print("=" * 60)

# 准备测试数据
existing_tasks = [
    {
        "id": 1,
        "title": "晨会",
        "start_time": (datetime.now().replace(hour=9, minute=0, second=0)).isoformat(),
        "end_time": (datetime.now().replace(hour=9, minute=30, second=0)).isoformat(),
        "status": "pending"
    },
    {
        "id": 2,
        "title": "午餐时间",
        "start_time": (datetime.now().replace(hour=12, minute=0, second=0)).isoformat(),
        "end_time": (datetime.now().replace(hour=13, minute=0, second=0)).isoformat(),
        "status": "pending"
    }
]

preferences = {
    "blocked_time_start": "22:00",
    "blocked_time_end": "08:00",
    "default_priority": "medium"
}

# 测试1：检测冲突
print("\n【测试1】检测时间冲突...")
conflict_test = {
    "start_time": (datetime.now().replace(hour=9, minute=15, second=0)).isoformat(),
    "end_time": (datetime.now().replace(hour=9, minute=45, second=0)).isoformat()
}
result = detect_conflict(conflict_test, existing_tasks, preferences)
print(f"是否有冲突: {result['has_conflict']}")
if result['conflicts']:
    for conflict in result['conflicts']:
        print(f"  - {conflict['message']}")

# 测试2：成功排程
print("\n【测试2】为新任务排程...")
new_task = {
    "title": "完成Python作业",
    "duration": 90,
    "deadline": (datetime.now() + timedelta(days=2)).isoformat(),
    "priority": "high"
}
result = schedule_task(new_task, existing_tasks, preferences)
print(f"排程结果: {result['success']}")
if result['success']:
    print(f"建议时间: {result['scheduled_time']['start_time']} - {result['scheduled_time']['end_time']}")
    print(f"备选时间段数量: {len(result['alternative_slots'])}")
    print(f"消息: {result['message']}")
else:
    print(f"失败原因: {result['message']}")
    if 'suggestions' in result:
        print("建议:")
        for suggestion in result['suggestions']:
            print(f"  - {suggestion}")

# 测试3：批量优化
print("\n【测试3】批量优化多个任务...")
tasks_to_schedule = [
    {"title": "复习数学", "duration": 60, "deadline": (datetime.now() + timedelta(days=1)).isoformat(), "priority": "high"},
    {"title": "阅读书籍", "duration": 45, "deadline": (datetime.now() + timedelta(days=3)).isoformat(), "priority": "low"},
    {"title": "写报告", "duration": 120, "deadline": (datetime.now() + timedelta(days=2)).isoformat(), "priority": "medium"}
]
results = optimize_schedule(tasks_to_schedule, preferences)
for i, result in enumerate(results, 1):
    status = result.get('scheduling_status', 'unknown')
    if status == 'scheduled':
        print(f"  {i}. ✅ {result['title']}: {result['start_time']} - {result['end_time']}")
    else:
        print(f"  {i}. ❌ {result['title']}: {result.get('failure_reason', '未知错误')}")

# 测试4：免安排时段检测
print("\n【测试4】检测免安排时段冲突...")
night_task = {
    "start_time": (datetime.now().replace(hour=23, minute=0, second=0)).isoformat(),
    "end_time": (datetime.now().replace(hour=23, minute=30, second=0)).isoformat()
}
result = detect_conflict(night_task, [], preferences)
print(f"是否有冲突: {result['has_conflict']}")
if result['conflicts']:
    for conflict in result['conflicts']:
        print(f"  - {conflict['message']}")

# 测试5：无法排程的情况
print("\n【测试5】测试无法排程的情况...")
impossible_task = {
    "title": "不可能的任务",
    "duration": 10000,  # 非常长的时间
    "deadline": (datetime.now() + timedelta(hours=1)).isoformat(),  # 很短的截止时间
    "priority": "high"
}
result = schedule_task(impossible_task, existing_tasks, preferences)
print(f"排程结果: {result['success']}")
print(f"消息: {result['message']}")
if 'suggestion' in result:
    print(f"建议: {result['suggestion']}")

print("\n" + "=" * 60)
print("🎉 所有测试完成！")
print("=" * 60)
