"""检查学习习惯数据"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scheduler_service import get_learned_habits_summary
import json

print("\n" + "=" * 70)
print("📚 检查学习习惯数据")
print("=" * 70)

summary = get_learned_habits_summary(user_id=1)

if summary["success"]:
    print(f"\n总类别数: {summary['summary']['total_categories']}")
    print(f"已学习习惯数: {summary['summary']['active_habits']}")
    
    if summary['summary']['learned_habits']:
        print(f"\n详细习惯列表:")
        print("-" * 70)
        
        for habit in summary['summary']['learned_habits']:
            print(f"\n关键词: {habit['keyword']}")
            print(f"  学习次数: {habit['count']}")
            print(f"  置信度: {habit['confidence']:.2f}")
            print(f"  偏好:")
            for pref_type, pref_value in habit['preferences'].items():
                print(f"    - {pref_type}: {pref_value}")
    else:
        print("\n⚠️ 没有已学习的习惯！")
else:
    print(f"\n❌ 获取失败: {summary.get('error')}")

print("\n" + "=" * 70)
