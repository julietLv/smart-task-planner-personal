"""测试长期记忆优化功能"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scheduler_service import (
    remember_user_preference,
    apply_learned_habits,
    get_learned_habits_summary,
    delete_learned_habit,
    add_custom_keyword,
    extract_task_keywords
)


def test_enhanced_keywords():
    """测试1: 增强的关键词提取"""
    print("\n🔍 测试1: 增强的关键词提取")

    test_cases = [
        ("早上跑步5公里", ["运动"]),
        ("完成Python编程作业", ["学习"]),
        ("准备项目演示文稿", ["工作"]),
        ("周末去旅行", ["生活"]),
        ("设计新的Logo", ["创作"]),
        ("参加社团活动", ["社交"]),
        ("去医院复查", ["健康"]),
        ("练习瑜伽", ["运动"]),
        ("学习英语单词", ["学习"])
    ]

    for title, expected_categories in test_cases:
        keywords = extract_task_keywords(title)
        match = any(kw in keywords for kw in expected_categories)
        status = "✅" if match else "❌"
        print(f"   {status} '{title}' -> {keywords}")


def test_flexible_thresholds():
    """测试2: 灵活学习阈值"""
    print("\n🎯 测试2: 灵活学习阈值")

    print("   优先级阈值: 2次")
    print("   时长阈值: 3次")
    print("   时间段阈值: 4次")

    for i in range(3):
        remember_user_preference("学习任务", "priority", "medium", "high", user_id=1)

    summary = get_learned_habits_summary(1)
    if summary["success"]:
        for habit in summary["summary"]["learned_habits"]:
            print(
                f"   ✅ {habit['keyword']}: 学习了优先级={habit['preferences'].get('priority')}, 置信度={habit['confidence']:.0%}")


def test_custom_keywords():
    """测试3: 自定义关键词"""
    print("\n📝 测试3: 自定义关键词")

    add_custom_keyword("LeetCode", "学习", user_id=1)
    add_custom_keyword("健身房", "运动", user_id=1)

    keywords1 = extract_task_keywords("做LeetCode题目")
    keywords2 = extract_task_keywords("去健身房锻炼")

    print(f"   ✅ '做LeetCode题目' -> {keywords1}")
    print(f"   ✅ '去健身房锻炼' -> {keywords2}")


def test_habits_summary():
    """测试4: 习惯摘要"""
    print("\n📊 测试4: 习惯摘要")

    summary = get_learned_habits_summary(1)

    if summary["success"]:
        data = summary["summary"]
        print(f"   总分类数: {data['total_categories']}")
        print(f"   活跃习惯: {data['active_habits']}")

        for habit in data["learned_habits"]:
            print(f"\n   📌 {habit['keyword']}:")
            print(f"      偏好: {habit['preferences']}")
            print(f"      置信度: {habit['confidence']:.0%}")
            print(f"      学习次数: {habit['count']}")
            print(f"      最后使用: {habit['last_used'][:10] if habit['last_used'] else 'N/A'}")


def test_apply_habits():
    """测试5: 应用习惯"""
    print("\n🧠 测试5: 应用已学习习惯")

    task1 = {"title": "学习机器学习算法", "priority": "medium", "duration": 60}
    result1 = apply_learned_habits(task1, user_id=1)
    print(f"   原始任务: {task1}")
    print(f"   应用后: {result1}")

    task2 = {"title": "晚上跑步", "priority": "medium", "duration": 30}
    result2 = apply_learned_habits(task2, user_id=1)
    print(f"   原始任务: {task2}")
    print(f"   应用后: {result2}")


def test_delete_habit():
    """测试6: 删除习惯"""
    print("\n🗑️ 测试6: 删除习惯")

    summary_before = get_learned_habits_summary(1)
    if summary_before["success"]:
        habits = summary_before["summary"]["learned_habits"]
        if habits:
            keyword_to_delete = habits[0]["keyword"]
            print(f"   删除习惯: {keyword_to_delete}")

            success = delete_learned_habit(keyword_to_delete, user_id=1)
            print(f"   {'✅ 删除成功' if success else '❌ 删除失败'}")

            summary_after = get_learned_habits_summary(1)
            if summary_after["success"]:
                print(f"   剩余习惯数: {summary_after['summary']['active_habits']}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 长期记忆优化功能测试")
    print("=" * 60)

    test_enhanced_keywords()
    test_flexible_thresholds()
    test_custom_keywords()
    test_habits_summary()
    test_apply_habits()
    test_delete_habit()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成")
    print("=" * 60)
