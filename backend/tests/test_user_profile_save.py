"""
测试用户画像字段是否正确保存和读取
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.models.task_model import get_user_preferences, update_user_preferences

print("=" * 70)
print("测试用户画像字段")
print("=" * 70)

# 1. 读取当前用户偏好
print("\n1. 读取当前用户偏好...")
prefs = get_user_preferences(user_id=1)

if prefs:
    print(f"   ✅ 用户偏好存在")
    print(f"      user_type: {prefs.user_type}")
    print(f"      workday_hours: {prefs.workday_hours}")
    print(f"      preferred_time_slot: {prefs.preferred_time_slot}")
    print(f"      time_slot_offset: {prefs.time_slot_offset}")
else:
    print(f"   ❌ 用户偏好不存在")
    sys.exit(1)

# 2. 测试更新 user_type
print("\n2. 测试更新 user_type 为 'student'...")
prefs = update_user_preferences(1, user_type="student")
print(f"   更新后 user_type: {prefs.user_type}")

# 3. 重新读取验证
print("\n3. 重新读取验证...")
prefs = get_user_preferences(user_id=1)
print(f"   读取的 user_type: {prefs.user_type}")

if prefs.user_type == "student":
    print("   ✅ 测试通过！user_type 已正确保存")
else:
    print(f"   ❌ 测试失败！期望 'student'，实际 '{prefs.user_type}'")

# 4. 恢复默认值
print("\n4. 恢复默认值...")
prefs = update_user_preferences(1, user_type="worker")
print(f"   已恢复为: {prefs.user_type}")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
