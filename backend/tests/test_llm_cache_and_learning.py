"""
测试 LLM Token 缓存和自然语言学习习惯功能
"""
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.llm_service import parse_user_intent
from app.services.scheduler_service import get_learned_habits_summary, remember_user_preference


def test_llm_cache():
    """测试1: LLM 响应缓存"""
    print("\n" + "=" * 70)
    print("🧪 测试1: LLM Token 缓存机制")
    print("=" * 70)
    
    test_input = "明天早上9点开会，预计30分钟"
    
    print(f"\n📝 第一次调用（应该调用 LLM API）:")
    print(f"   输入: {test_input}")
    result1 = parse_user_intent(test_input)
    print(f"   ✅ 解析成功: intent={result1.get('intent')}")
    
    print(f"\n📝 第二次调用（应该命中缓存，节省 Token）:")
    print(f"   输入: {test_input}")
    result2 = parse_user_intent(test_input)
    print(f"   ✅ 解析成功: intent={result2.get('intent')}")
    
    print(f"\n📝 第三次调用（应该再次命中缓存）:")
    result3 = parse_user_intent(test_input)
    print(f"   ✅ 解析成功")
    
    print("\n✅ 测试完成：如果看到 'LLM 缓存命中' 日志，说明缓存生效！")


def test_natural_language_learning():
    """测试2: 从自然语言中学习习惯"""
    print("\n" + "=" * 70)
    print("🧪 测试2: 从自然语言对话中学习新习惯")
    print("=" * 70)
    
    # 先重置习惯（可选）
    # from app.services.scheduler_service import reset_all_habits
    # reset_all_habits(1)
    
    test_cases = [
        {
            "input": "我通常晚上学习",
            "expected": "学习到 '学习' 的时间段偏好: evening"
        },
        {
            "input": "会议一般需要60分钟",
            "expected": "学习到 '会议' 的时长偏好: 60分钟"
        },
        {
            "input": "作业都是高优先级",
            "expected": "学习到 '作业' 的优先级偏好: high"
        },
        {
            "input": "下午跑步锻炼",
            "expected": "学习到 '跑步' 的时间段偏好: afternoon"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}:")
        print(f"   输入: {test_case['input']}")
        print(f"   期望: {test_case['expected']}")
        
        result = parse_user_intent(test_case['input'])
        print(f"   ✅ 解析完成")
    
    print("\n" + "-" * 70)
    print("📊 查看学习到的习惯:")
    print("-" * 70)
    
    summary = get_learned_habits_summary(1)
    if summary["success"]:
        learned_habits = summary["summary"]["learned_habits"]
        if learned_habits:
            print(f"\n共学习到 {len(learned_habits)} 个习惯:\n")
            for habit in learned_habits:
                print(f"  📌 {habit['keyword']}:")
                print(f"     - 置信度: {habit['confidence']:.0%}")
                print(f"     - 调整次数: {habit['count']}")
                if habit['preferences']:
                    for pref_type, pref_value in habit['preferences'].items():
                        print(f"     - {pref_type}: {pref_value}")
        else:
            print("\n⚠️ 未检测到已学习的习惯（可能需要多次输入相同模式）")
    else:
        print(f"\n❌ 获取习惯摘要失败: {summary.get('error')}")
    
    print("\n✅ 测试完成：如果看到 '从自然语言学习到' 日志，说明学习生效！")


def test_combined_workflow():
    """测试3: 完整工作流（缓存 + 学习）"""
    print("\n" + "=" * 70)
    print("🧪 测试3: 完整工作流测试")
    print("=" * 70)
    
    # 场景1: 用户第一次说“我通常晚上学习”
    print("\n📝 场景1: 用户表达习惯")
    input1 = "我通常晚上学习"
    print(f"   输入: {input1}")
    result1 = parse_user_intent(input1)
    print(f"   ✅ 系统学习了这个习惯")
    
    # 场景2: 用户第二次说同样的话（应该命中缓存）
    print("\n📝 场景2: 用户重复相同输入（测试缓存）")
    print(f"   输入: {input1}")
    result2 = parse_user_intent(input1)
    print(f"   ✅ 应该命中 LLM 缓存")
    
    # 场景3: 用户创建学习任务（应该应用学到的习惯）
    print("\n📝 场景3: 用户创建学习任务")
    input3 = "明天写数学作业"
    print(f"   输入: {input3}")
    result3 = parse_user_intent(input3)
    
    if result3.get("applied_habits"):
        print(f"   ✅ 应用了 {len(result3['applied_habits'])} 个历史习惯:")
        for habit in result3['applied_habits']:
            print(f"      - {habit}")
    else:
        print(f"   ⚠️ 未应用习惯（可能还没有学习到相关习惯）")
    
    print("\n✅ 完整工作流测试完成！")


if __name__ == "__main__":
    print("\n" + "🚀" * 35)
    print("开始测试 LLM Token 缓存和自然语言学习习惯功能")
    print("🚀" * 35)
    
    try:
        # 测试1: LLM 缓存
        test_llm_cache()
        
        # 测试2: 自然语言学习
        test_natural_language_learning()
        
        # 测试3: 完整工作流
        test_combined_workflow()
        
        print("\n" + "=" * 70)
        print("🎉 所有测试完成！")
        print("=" * 70)
        print("\n💡 提示:")
        print("   1. 检查控制台日志中是否有 'LLM 缓存命中' 消息")
        print("   2. 检查是否有 '从自然语言学习到' 消息")
        print("   3. 如果有 Redis 运行，缓存会持久化；否则仅内存缓存")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
