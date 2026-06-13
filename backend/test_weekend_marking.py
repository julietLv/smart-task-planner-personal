"""backend/test_weekend_marking.py - 测试周末标记功能"""
from datetime import date, timedelta
import sys

sys.path.insert(0, 'D:/demo_plan/backend')

from app.services.holiday_service import holiday_service


def test_month_weekends(year, month):
    """测试指定月份的周末标记"""
    print(f"\n{'=' * 70}")
    print(f"测试 {year}年{month}月 的周末标记")
    print(f"{'=' * 70}\n")

    # 计算该月的第一天和最后一天
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    weekends_count = 0
    holidays_count = 0

    current = first_day
    while current <= last_day:
        holiday_name = holiday_service.get_holiday_name(current)
        is_weekend = current.weekday() >= 5

        if holiday_name:
            marker = "🔴 法定假日" if holiday_name != "周末" else "🟡 周末"
            print(f"{current.strftime('%Y-%m-%d')} ({weekday_names[current.weekday()]}) - {holiday_name:8} {marker}")

            if holiday_name == "周末":
                weekends_count += 1
            else:
                holidays_count += 1

        current += timedelta(days=1)

    print(f"\n统计:")
    print(f"  - 法定节假日: {holidays_count} 天")
    print(f"  - 周末: {weekends_count} 天")
    print(f"  - 总计标记: {holidays_count + weekends_count} 天")


if __name__ == "__main__":
    # 测试2026年3月和7月
    test_month_weekends(2026, 3)
    test_month_weekends(2026, 7)

    print(f"\n{'=' * 70}")
    print("✅ 测试完成！如果看到周末标记，说明功能正常")
    print(f"{'=' * 70}")
