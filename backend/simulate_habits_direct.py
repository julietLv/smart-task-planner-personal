"""直接模拟学习习惯积累（无需交互）"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scheduler_service import remember_user_preference

print("\n" + "=" * 70)
print("📚 模拟学习习惯积累")
print("=" * 70)

user_id = 1

# 模拟多次调整"晨跑"任务的优先级
print("\n模拟用户对『晨跑』的调整行为...")
for i in range(5):
    remember_user_preference(
        task_title="晨跑",
        adjustment_type="priority",
        old_value="medium",
        new_value="high",
        user_id=user_id,
        context={"test": True}
    )
print("✅ 已记录 5 次优先级调整（medium → high）")

# 模拟多次调整"晨跑"的时长
for i in range(4):
    remember_user_preference(
        task_title="晨跑",
        adjustment_type="duration",
        old_value=30,
        new_value=45,
        user_id=user_id,
        context={"test": True}
    )
print("✅ 已记录 4 次时长调整（30分钟 → 45分钟）")

# 模拟多次调整"会议"的时长
for i in range(6):
    remember_user_preference(
        task_title="会议",
        adjustment_type="duration",
        old_value=30,
        new_value=60,
        user_id=user_id,
        context={"test": True}
    )
print("✅ 已记录 6 次时长调整（会议 30分钟 → 60分钟）")

print("\n✅ 学习习惯模拟完成！")
print("\n现在请运行: python test_phase1_habit_enrichment.py 并选择选项 2")
