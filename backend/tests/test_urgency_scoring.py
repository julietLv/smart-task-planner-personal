"""任务紧急度测试 - 测试有截止时间的任务评分变化"""
from datetime import datetime, timedelta
from app.services.scoring_engine import ScoringEngine
from app.services.scheduler_service import parse_time


def calculate_urgency_score(deadline_str: str, current_time: datetime = None) -> float:
    """
    计算任务紧急度分数

    Args:
        deadline_str: 截止时间字符串
        current_time: 当前时间（默认现在）

    Returns:
        紧急度分数 (0-50，越高越紧急)
    """
    if current_time is None:
        current_time = datetime.now()

    deadline = parse_time(deadline_str)
    if not deadline:
        return 0

    # 计算剩余时间（小时）
    hours_left = (deadline - current_time).total_seconds() / 3600

    if hours_left <= 0:
        # 已过期，最高紧急度
        return 50

    if hours_left <= 2:
        # 2小时内，非常紧急
        return 50
    elif hours_left <= 24:
        # 24小时内，紧急
        # 线性映射：2小时->50分，24小时->30分
        return 50 - (hours_left - 2) * (20 / 22)
    elif hours_left <= 72:
        # 3天内，中等紧急
        # 线性映射：24小时->30分，72小时->15分
        return 30 - (hours_left - 24) * (15 / 48)
    elif hours_left <= 168:
        # 7天内，低紧急度
        # 线性映射：72小时->15分，168小时->5分
        return 15 - (hours_left - 72) * (10 / 96)
    else:
        # 超过7天，很低紧急度
        return max(0, 5 - (hours_left - 168) * (5 / 168))


def test_urgency_scoring():
    """测试不同截止时间的紧急度评分"""
    print("\n" + "=" * 70)
    print("📊 任务紧急度评分测试")
    print("=" * 70)

    now = datetime.now()

    test_cases = [
        ("已过期", (now - timedelta(hours=2)).isoformat()),
        ("2小时后", (now + timedelta(hours=2)).isoformat()),
        ("6小时后", (now + timedelta(hours=6)).isoformat()),
        ("12小时后", (now + timedelta(hours=12)).isoformat()),
        ("24小时后", (now + timedelta(hours=24)).isoformat()),
        ("2天后", (now + timedelta(days=2)).isoformat()),
        ("3天后", (now + timedelta(days=3)).isoformat()),
        ("5天后", (now + timedelta(days=5)).isoformat()),
        ("7天后", (now + timedelta(days=7)).isoformat()),
        ("10天后", (now + timedelta(days=10)).isoformat()),
        ("14天后", (now + timedelta(days=14)).isoformat()),
    ]

    print(f"\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"{'场景':<15} {'截止时间':<25} {'剩余时间':<15} {'紧急度分数':<15} {'等级'}")
    print("-" * 90)

    for scenario, deadline_str in test_cases:
        deadline = parse_time(deadline_str)
        hours_left = (deadline - now).total_seconds() / 3600

        if hours_left <= 0:
            time_desc = f"已过期 {abs(hours_left):.1f}h"
        elif hours_left < 24:
            time_desc = f"{hours_left:.1f}小时"
        else:
            days = hours_left / 24
            time_desc = f"{days:.1f}天"

        urgency_score = calculate_urgency_score(deadline_str, now)

        # 确定等级
        if urgency_score >= 40:
            level = "🔴 非常紧急"
        elif urgency_score >= 25:
            level = "🟠 紧急"
        elif urgency_score >= 10:
            level = "🟡 中等"
        else:
            level = "🟢 低优先级"

        print(f"{scenario:<12} {deadline_str:<25} {time_desc:<15} {urgency_score:<15.2f} {level}")

    print("\n" + "=" * 70)
    print("✅ 测试完成\n")


def test_urgency_impact_on_final_score():
    """测试紧急度对最终评分的影响"""
    print("\n" + "=" * 70)
    print("📈 紧急度对最终评分的影响测试")
    print("=" * 70)

    engine = ScoringEngine()
    now = datetime.now()

    test_scenarios = [
        {
            "name": "高紧急度（2小时后截止）",
            "deadline": (now + timedelta(hours=2)).isoformat(),
            "other_scores": {
                "habit_match": 50,
                "date_freshness": 25,
                "time_quality": 40,
                "load_balance": 10,
                "priority": 50,
                "holiday": 0,
                "weather": 10
            }
        },
        {
            "name": "中等紧急度（2天后截止）",
            "deadline": (now + timedelta(days=2)).isoformat(),
            "other_scores": {
                "habit_match": 50,
                "date_freshness": 25,
                "time_quality": 40,
                "load_balance": 10,
                "priority": 50,
                "holiday": 0,
                "weather": 10
            }
        },
        {
            "name": "低紧急度（7天后截止）",
            "deadline": (now + timedelta(days=7)).isoformat(),
            "other_scores": {
                "habit_match": 50,
                "date_freshness": 25,
                "time_quality": 40,
                "load_balance": 10,
                "priority": 50,
                "holiday": 0,
                "weather": 10
            }
        }
    ]

    print(f"\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")

    for scenario in test_scenarios:
        urgency_score = calculate_urgency_score(scenario["deadline"], now)

        dimension_scores = scenario["other_scores"].copy()
        dimension_scores["urgency"] = urgency_score

        result = engine.calculate_final_score(dimension_scores)

        print(f"场景: {scenario['name']}")
        print(f"  紧急度分数: {urgency_score:.2f}")
        print(f"  最终评分: {result['final_score']:.2f}")
        print(f"  紧急度贡献: {result['dimension_details']['urgency']['weighted']:.4f}")
        print()

    print("=" * 70)
    print("✅ 测试完成\n")


if __name__ == "__main__":
    test_urgency_scoring()
    test_urgency_impact_on_final_score()
