"""backend/test_holiday_weather.py"""
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

from app.services.holiday_service import holiday_service
from app.services.weather_service import weather_service


def test_holiday_service():
    """测试节假日服务"""
    print("\n" + "=" * 70)
    print("📅 节假日服务测试")
    print("=" * 70)

    now = datetime.now()

    test_dates = [
        ("今天", now.date()),
        ("明天", (now + timedelta(days=1)).date()),
        ("五一劳动节", date(2026, 5, 1)),
        ("国庆节", date(2026, 10, 1)),
        ("普通工作日", date(2026, 5, 12)),
        ("周末", date(2026, 5, 16)),
    ]

    print(f"\n当前日期: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"{'日期':<15} {'是否节假日':<12} {'节假日名称':<15} {'工作会议影响':<15} {'运动影响':<15}")
    print("-" * 80)

    for label, test_date in test_dates:
        is_holiday = holiday_service.is_holiday(test_date)
        holiday_name = holiday_service.get_holiday_name(test_date) or "无"

        meeting_impact = holiday_service.get_holiday_impact_score(test_date, "meeting")
        exercise_impact = holiday_service.get_holiday_impact_score(test_date, "exercise")

        print(f"{label:<12} {str(is_holiday):<12} {holiday_name:<15} {meeting_impact:<15} {exercise_impact:<15}")

    print("\n✅ 节假日服务测试完成\n")


def test_weather_service():
    """测试天气服务"""
    print("\n" + "=" * 70)
    print("🌤️  天气服务测试")
    print("=" * 70)

    now = datetime.now()

    test_dates = [
        ("今天", now.date()),
        ("明天", (now + timedelta(days=1)).date()),
        ("一周后", (now + timedelta(days=7)).date()),
        ("一个月后", (now + timedelta(days=30)).date()),
    ]

    print(f"\n当前城市: {weather_service.city}\n")
    print(f"{'日期':<15} {'天气状况':<12} {'温度':<10} {'湿度':<10} {'风速':<10} {'运动影响':<12} {'会议影响':<12}")
    print("-" * 95)

    for label, test_date in test_dates:
        weather = weather_service.get_weather(test_date)

        exercise_impact = weather_service.get_weather_impact_score(test_date, "exercise")
        meeting_impact = weather_service.get_weather_impact_score(test_date, "meeting")

        condition_cn = {
            "sunny": "晴",
            "cloudy": "多云",
            "rainy": "雨",
            "snowy": "雪",
            "stormy": "暴雨"
        }.get(weather["condition"], weather["condition"])

        print(
            f"{label:<12} {condition_cn:<12} {weather['temperature']:<8}°C {weather['humidity']:<8}% {weather['wind_speed']:<8}km/h {exercise_impact:<12} {meeting_impact:<12}")

    print("\n✅ 天气服务测试完成\n")


def test_combined_scoring():
    """测试综合评分（节假日+天气）"""
    print("\n" + "=" * 70)
    print("🎯 综合评分测试（节假日+天气）")
    print("=" * 70)

    test_cases = [
        {
            "name": "五一假期安排会议",
            "date": date(2026, 5, 2),
            "task_type": "meeting"
        },
        {
            "name": "五一假期安排运动",
            "date": date(2026, 5, 2),
            "task_type": "exercise"
        },
        {
            "name": "雨天安排户外运动",
            "date": date(2026, 7, 15),  # 假设这天模拟为雨天
            "task_type": "exercise"
        },
        {
            "name": "工作日晴天开会",
            "date": date(2026, 5, 12),
            "task_type": "meeting"
        }
    ]

    print()
    for case in test_cases:
        holiday_score = holiday_service.get_holiday_impact_score(case["date"], case["task_type"])
        weather_score = weather_service.get_weather_impact_score(case["date"], case["task_type"])

        total_impact = holiday_score + weather_score

        print(f"场景: {case['name']}")
        print(f"  日期: {case['date']}")
        print(f"  节假日影响: {holiday_score:+d} 分")
        print(f"  天气影响: {weather_score:+d} 分")
        print(f"  总影响: {total_impact:+d} 分")
        print()

    print("✅ 综合评分测试完成\n")


if __name__ == "__main__":
    test_holiday_service()
    test_weather_service()
    test_combined_scoring()
