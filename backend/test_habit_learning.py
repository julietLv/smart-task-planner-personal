"""习惯学习验证 - 测试系统是否能学习到用户偏好"""
from app.services.scheduler_service import remember_user_preference, get_learned_habits_summary
from app.models.task_model import get_user_preferences, create_user_preferences
import json


def simulate_user_adjustments():
    """模拟用户的多次调整行为"""
    print("\n" + "=" * 70)
    print("🧠 习惯学习验证测试")
    print("=" * 70)

    user_id = 1

    # 确保用户偏好存在
    preferences = get_user_preferences(user_id)
    if not preferences:
        print("创建用户偏好...")
        preferences = create_user_preferences(user_id)

    print(f"\n开始模拟用户对『晨跑』任务的调整行为...\n")

    # 模拟场景1：用户多次将晨跑的优先级从 medium 调整为 high
    scenarios = [
        {
            "title": "晨跑",
            "adjustment_type": "priority",
            "old_value": "medium",
            "new_value": "high",
            "count": 5
        },
        {
            "title": "阅读",
            "adjustment_type": "duration",
            "old_value": 30,
            "new_value": 60,
            "count": 4
        },
        {
            "title": "工作会议",
            "adjustment_type": "time_period",
            "old_value": None,
            "new_value": "morning",
            "count": 6
        }
    ]

    for scenario in scenarios:
        print(f"\n📝 场景: {scenario['title']} - {scenario['adjustment_type']} 调整")
        print(f"   从 {scenario['old_value']} → {scenario['new_value']}")
        print(f"   模拟次数: {scenario['count']}")

        for i in range(scenario['count']):
            remember_user_preference(
                task_title=scenario['title'],
                adjustment_type=scenario['adjustment_type'],
                old_value=scenario['old_value'],
                new_value=scenario['new_value'],
                user_id=user_id,
                context={"simulation": True, "iteration": i + 1}
            )

    print("\n" + "-" * 70)
    print("✅ 模拟完成，查看学习到的习惯:\n")

    # 获取学习习惯摘要
    summary = get_learned_habits_summary(user_id)

    if summary['success']:
        # ✅ 修复：从 summary 嵌套结构中获取 learned_habits
        summary_data = summary.get('summary', {})
        learned_habits_list = summary_data.get('learned_habits', [])

        if not learned_habits_list:
            print("⚠️ 未检测到已学习的习惯")
        else:
            print(f"共学习到 {len(learned_habits_list)} 个习惯:\n")

            for habit_info in learned_habits_list:
                keyword = habit_info.get('keyword', '未知')
                print(f"关键词: {keyword}")
                print(f"  调整次数: {habit_info.get('count', 0)}")
                print(f"  已学习: ✅ 是")
                
                # 显示偏好信息
                preferences = habit_info.get('preferences', {})
                for pref_type, pref_value in preferences.items():
                    print(f"  偏好 {pref_type}: {pref_value}")
                
                print(f"  置信度: {habit_info.get('confidence', 0):.2%}")
                print(f"  学习时间: {habit_info.get('learned_at', 'N/A')}")
                print()
    else:
        print(f"❌ 获取习惯摘要失败: {summary.get('error')}")

    print("=" * 70)

    # 测试应用学到的习惯
    print("\n🎯 测试应用学到的习惯到新任务排程:\n")

    preferences = get_user_preferences(user_id)
    if preferences:
        habits = preferences.remembered_habits
        if isinstance(habits, str):
            habits = json.loads(habits)

        learned_count = sum(1 for h in habits.values() if isinstance(h, dict) and h.get('learned'))
        print(f"系统中已学习到 {learned_count} 个用户习惯")

        if learned_count > 0:
            print("\n✅ 习惯学习功能正常工作！")
            print("   系统会在排程时自动应用这些偏好。")
        else:
            print("\n⚠️ 尚未达到学习阈值，需要更多调整数据。")

    print("\n" + "=" * 70 + "\n")


def reset_and_test():
    """重置并重新测试"""
    print("\n⚠️ 是否要重置所有学习习惯？(y/n): ", end="")

    # 在脚本中直接执行重置
    from app.services.scheduler_service import reset_all_habits

    user_id = 1
    print(f"\n重置用户 {user_id} 的学习习惯...")

    success = reset_all_habits(user_id)

    if success:
        print("✅ 已重置所有学习习惯")
        print("可以重新运行 simulate_user_adjustments() 进行测试\n")
    else:
        print("❌ 重置失败\n")


if __name__ == "__main__":
    simulate_user_adjustments()

    # 如需重置，取消下面的注释
    # reset_and_test()
