"""检查原始习惯数据结构"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.task_model import get_user_preferences
import json

print("\n" + "=" * 70)
print("🔍 检查原始习惯数据结构")
print("=" * 70)

preferences = get_user_preferences(user_id=1)

if preferences and preferences.remembered_habits:
    habits = preferences.remembered_habits
    if isinstance(habits, str):
        habits = json.loads(habits)
    
    print(f"\n总习惯数: {len([k for k in habits.keys() if not k.startswith('_')])}")
    
    # 重点检查"晨跑"习惯
    if "晨跑" in habits:
        print(f"\n{'='*70}")
        print("晨跑习惯详情:")
        print(f"{'='*70}")
        print(json.dumps(habits["晨跑"], ensure_ascii=False, indent=2))
    
    # 检查所有已学习的习惯
    print(f"\n{'='*70}")
    print("所有已学习习惯的偏好字段:")
    print(f"{'='*70}")
    
    for keyword, data in habits.items():
        if keyword.startswith("_"):
            continue
        
        if data.get("learned"):
            print(f"\n{keyword}:")
            print(f"  learned: {data.get('learned')}")
            print(f"  confidence: {data.get('confidence', 0):.2f}")
            print(f"  count: {data.get('count', 0)}")
            
            # 列出所有 preferred_ 字段
            prefs = {k: v for k, v in data.items() if k.startswith("preferred_")}
            if prefs:
                print(f"  偏好:")
                for pref_key, pref_value in prefs.items():
                    print(f"    - {pref_key}: {pref_value}")
            else:
                print(f"  ⚠️ 没有 preferred_ 字段!")
else:
    print("\n❌ 没有找到用户偏好数据")

print("\n" + "=" * 70)
