"""Phase 1 数据打通功能测试"""
import requests
import json
from datetime import datetime, timedelta

# 后端服务地址
BASE_URL = "http://localhost:8080"

def test_phase1_habit_enrichment():
    """测试 Phase 1: 习惯融合功能"""
    
    print("\n" + "=" * 70)
    print("🧠 Phase 1: 数据打通功能测试")
    print("=" * 70)
    
    # 测试用例1: 用户输入缺少优先级和时长，应该从习惯中补充
    test_cases = [
        {
            "name": "场景1: 晨跑任务（应该有学习习惯）",
            "input": "明天早上晨跑",
            "expected_habits": ["优先级", "时长"]
        },
        {
            "name": "场景2: 会议任务",
            "input": "安排一个项目会议",
            "expected_habits": ["时长"]
        },
        {
            "name": "场景3: 学习任务",
            "input": "下午学习英语",
            "expected_habits": []
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"测试 {i}: {test_case['name']}")
        print(f"{'='*70}")
        print(f"用户输入: \"{test_case['input']}\"")
        
        try:
            # 调用解析 API
            response = requests.post(
                f"{BASE_URL}/api/tasks/parse",
                json={"text": test_case['input']},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\n✅ 解析成功!")
                print(f"   意图: {result.get('intent')}")
                print(f"   实体: {json.dumps(result.get('entities', {}), ensure_ascii=False, indent=6)}")
                
                # ⭐ 检查是否应用了习惯
                applied_habits = result.get('applied_habits', [])
                
                if applied_habits:
                    print(f"\n✨ [Phase 1] 应用了 {len(applied_habits)} 个历史习惯:")
                    for habit in applied_habits:
                        print(f"   - {habit}")
                    
                    print(f"\n💡 效果验证:")
                    entities = result.get('entities', {})
                    
                    if entities.get('priority'):
                        print(f"   ✅ 优先级已设置: {entities['priority']}")
                    else:
                        print(f"   ⚪ 优先级未设置")
                    
                    if entities.get('duration'):
                        print(f"   ✅ 时长已设置: {entities['duration']}分钟")
                    else:
                        print(f"   ⚪ 时长未设置")
                        
                else:
                    print(f"\n⚪ 未应用任何习惯（可能是新任务或无相关习惯）")
                
            else:
                print(f"\n❌ 解析失败: HTTP {response.status_code}")
                print(f"   错误信息: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ 连接失败: 请确保后端服务正在运行")
            break
        except Exception as e:
            print(f"\n❌ 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("✅ Phase 1 测试完成")
    print(f"{'='*70}\n")


def simulate_habit_learning():
    """模拟学习习惯积累（用于测试前的数据准备）"""
    
    print("\n" + "=" * 70)
    print("📚 模拟学习习惯积累")
    print("=" * 70)
    
    from app.services.scheduler_service import remember_user_preference
    
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
    
    print("\n✅ 学习习惯模拟完成！现在可以运行 test_phase1_habit_enrichment() 测试")


if __name__ == "__main__":
    import sys
    import os
    
    # 添加 backend 目录到路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    print("\n请选择操作:")
    print("1. 先模拟学习习惯积累（推荐首次测试时运行）")
    print("2. 直接测试 Phase 1 功能")
    
    choice = input("\n请输入选项 (1/2): ").strip()
    
    if choice == "1":
        simulate_habit_learning()
        print("\n现在请重启后端服务，然后再次运行此脚本选择选项 2")
    elif choice == "2":
        test_phase1_habit_enrichment()
    else:
        print("无效选项")
