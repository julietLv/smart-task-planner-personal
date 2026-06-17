"""
直接检查数据库中当前的user_type值
"""
import sys
sys.path.insert(0, 'D:/demo_plan/backend')

from app.models.task_model import get_user_preferences

print("=" * 70)
print("检查数据库中的user_type当前值")
print("=" * 70)

prefs = get_user_preferences(user_id=1)

if prefs:
    print(f"\n数据库中的值:")
    print(f"  user_type: {prefs.user_type}")
    print(f"  workday_hours: {prefs.workday_hours}")
    print(f"  preferred_time_slot: {prefs.preferred_time_slot}")
    print(f"  time_slot_offset: {prefs.time_slot_offset}")
    
    print("\n转换为中文:")
    type_names = {
        'student': '学生',
        'worker': '工作者',
        'elderly': '老年人'
    }
    print(f"  用户类型: {type_names.get(prefs.user_type, prefs.user_type)}")
else:
    print("未找到用户偏好记录")
