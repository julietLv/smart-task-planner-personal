"""测试长期记忆功能"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scheduler_service import (
    remember_user_preference,
    apply_learned_habits,
    get_learned_habits_summary,
    extract_task_keywords
)
from app.models.database import init_db


def test_extract_keywords():
    """测试关键词提取"""
    print("\n" + "=" * 60)
    print("📝 测试 1: 关键词提取")
    print("=" * 60)

    test_cases = [
        ("下午去健身房运动", ["运动"]),
        ("学习英语单词", ["学习"]),
        "参加工作会议",
        "周末看电影",
        "打王者荣耀游戏",
    ]

    for case in test_cases:
        if isinstance(case, tuple):
            title, expected = case
            keywords = extract_task_keywords(title)
            match = any(kw in keywords for kw in expected)
            status = "✅" if match else "⚠️"
            print(f"{status} '{title}' → {keywords}")
        else:
            keywords = extract_task_keywords(case)
            print(f"   '{case}' → {keywords}")


def test_remember_and_apply():
    """测试记忆和应用习惯"""
    print("\n" + "=" * 60)
    print("🧠 测试 2: 记忆和应用习惯")
    print("=" * 60)

    # 初始化数据库
    init_db()

    # 模拟用户多次调整"运动"类任务的优先级
    print("\n📌 场景: 用户多次将'运动'类任务调整为高优先级\n")

    exercise_tasks = [
        "下午去健身房",
        "晚上跑步锻炼",
        "周末游泳",
        "早上瑜伽练习",
    ]

    for i, task_title in enumerate(exercise_tasks, 1):
        print(f"第 {i} 次调整: '{task_title}'")
        result = remember_user_preference(
            task_title=task_title,
            adjustment_type="priority",
            old_value="medium",
            new_value="high",
            user_id=1
        )
        print(f"   记录结果: {'✅ 成功' if result else '❌ 失败'}\n")

    # 查看学习到的习惯
    print("\n📊 已学习的习惯:")
    summary = get_learned_habits_summary(user_id=1)

    if summary["success"]:
        stats = summary["summary"]
        print(f"   总分类数: {stats['total_categories']}")
        print(f"   活跃习惯: {stats['active_habits']}")

        for habit in stats["learned_habits"]:
            print(f"\n   🔹 关键词: {habit['keyword']}")
            print(f"      出现次数: {habit['count']}")
            print(f"      置信度: {habit['confidence']:.2f}")
            print(f"      偏好: {habit['preferences']}")
    else:
        print(f"   ❌ 获取摘要失败: {summary.get('error')}")

    # 测试应用习惯到新任务
    print("\n\n🎯 测试应用习惯到新任务:")
    new_task = {
        "title": "明天去健身",
        "description": "",
        "priority": None,
        "duration": None
    }

    print(f"   原始任务: {new_task}")
    enhanced_task = apply_learned_habits(new_task.copy(), user_id=1)
    print(f"   增强后: {enhanced_task}")

    if "applied_habits" in enhanced_task:
        print(f"   ✅ 应用了 {len(enhanced_task['applied_habits'])} 个习惯:")
        for habit in enhanced_task["applied_habits"]:
            print(f"      • {habit}")


def test_duration_learning():
    """测试时长学习"""
    print("\n" + "=" * 60)
    print("⏱️  测试 3: 时长学习")
    print("=" * 60)

    # 模拟用户多次调整"会议"类任务的时长
    meeting_tasks = [
        "项目进度会议",
        "团队周会",
        "需求评审会议",
        "客户沟通会议",
    ]

    print("\n📌 场景: 用户多次将'会议'类任务时长调整为 60 分钟\n")

    for i, task_title in enumerate(meeting_tasks, 1):
        print(f"第 {i} 次调整: '{task_title}'")
        result = remember_user_preference(
            task_title=task_title,
            adjustment_type="duration",
            old_value=30,
            new_value=60,
            user_id=1,
            context={"original_estimate": 30}
        )
        print(f"   记录结果: {'✅ 成功' if result else '❌ 失败'}\n")

    # 测试应用
    new_meeting = {
        "title": "下周的项目会议",
        "duration": None
    }

    print(f"\n🎯 新任务: {new_meeting['title']}")
    enhanced = apply_learned_habits(new_meeting.copy(), user_id=1)
    print(f"   建议时长: {enhanced.get('duration', '未设置')} 分钟")

    if enhanced.get("duration") == 60:
        print("   ✅ 成功应用时长习惯！")


def test_custom_keyword():
    """测试自定义关键词"""
    print("\n" + "=" * 60)
    print("🔧 测试 4: 自定义关键词")
    print("=" * 60)

    from app.services.scheduler_service import add_custom_keyword

    # 添加自定义关键词
    print("\n📌 添加自定义关键词: '王者' -> '游戏'")
    result = add_custom_keyword("王者", "娱乐", user_id=1)
    print(f"   添加结果: {'✅ 成功' if result else '❌ 失败'}")

    # 测试提取
    keywords = extract_task_keywords("晚上打王者荣耀")
    print(f"   提取关键词: {keywords}")

    if "娱乐" in keywords:
        print("   ✅ 自定义关键词生效！")


if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("长期记忆功能测试")
    print("🧪" * 30)

    try:
        test_extract_keywords()
        test_remember_and_apply()
        test_duration_learning()
        test_custom_keyword()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
