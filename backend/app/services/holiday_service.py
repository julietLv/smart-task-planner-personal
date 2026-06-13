"""backend/app/services/holiday_service.py"""
from datetime import datetime, date
from pathlib import Path
import json


class HolidayService:
    """节假日服务 - 支持中国法定节假日配置"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.holidays = self.load_holidays()
        self._initialized = True

    def load_holidays(self) -> dict:
        """加载节假日配置（从JSON文件）"""
        config_path = Path(__file__).parent.parent.parent / "config" / "holidays.json"

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    holidays = json.load(f)
                    print(f"✅ 已加载节假日配置: {len(holidays)} 年")
                    return holidays
            except Exception as e:
                print(f"⚠️ 加载节假日配置失败: {e}，使用默认配置")

        # 默认配置（2026年中国法定节假日）
        return {
            "2026": {
                "元旦": ["2026-01-01"],
                "春节": ["2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22",
                         "2026-02-23"],
                "清明节": ["2026-04-05", "2026-04-06", "2026-04-07"],
                "劳动节": ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05"],
                "端午节": ["2026-06-19", "2026-06-20", "2026-06-21"],
                "中秋节": ["2026-09-25", "2026-09-26", "2026-09-27"],
                "国庆节": ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06",
                           "2026-10-07"]
            },
            "2025": {
                "元旦": ["2025-01-01"],
                "春节": ["2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31", "2025-02-01", "2025-02-02",
                         "2025-02-03"],
                "清明节": ["2025-04-04", "2025-04-05", "2025-04-06"],
                "劳动节": ["2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04", "2025-05-05"],
                "端午节": ["2025-05-31", "2025-06-01", "2025-06-02"],
                "中秋节": ["2025-10-06", "2025-10-07", "2025-10-08"],
                "国庆节": ["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05", "2025-10-06",
                           "2025-10-07"]
            }
        }

    def is_holiday(self, check_date: date) -> bool:
        """检查是否是节假日"""
        year = str(check_date.year)
        date_str = check_date.strftime("%Y-%m-%d")

        if year in self.holidays:
            for holiday_name, dates in self.holidays[year].items():
                if date_str in dates:
                    return True

        # 检查周末
        if check_date.weekday() >= 5:
            return True

        return False

    def get_holiday_name(self, check_date: date) -> str:
        """获取节假日名称"""
        year = str(check_date.year)
        date_str = check_date.strftime("%Y-%m-%d")

        if year in self.holidays:
            for holiday_name, dates in self.holidays[year].items():
                if date_str in dates:
                    return holiday_name

        if check_date.weekday() >= 5:
            return "周末"

        return None

    def get_holiday_impact_score(self, check_date: date, task_type: str) -> float:
        """
        计算节假日对任务的影响分数（-40~0分）

        Args:
            check_date: 检查日期
            task_type: 任务类型 (meeting/study/exercise/work/other)

        Returns:
            影响分数（负数表示不适合安排）
        """
        holiday_name = self.get_holiday_name(check_date)

        if not holiday_name:
            return 0  # 工作日，无影响

        # 判断是法定节假日还是周末
        is_legal_holiday = holiday_name != "周末"

        # 法定节假日不适合工作安排会议、学习等
        if is_legal_holiday:
            if task_type in ["meeting", "study", "work"]:
                return -40  # 强烈不建议在法定假日安排工作
            elif task_type == "exercise":
                return -5  # 假日可以运动，轻微扣分
            else:
                return -15  # 其他任务适度扣分

        # 周末的影响较小
        else:
            if task_type in ["meeting", "work"]:
                return -20  # 周末不太适合工作会议
            elif task_type == "exercise":
                return 0  # 周末适合运动
            elif task_type == "study":
                return -10  # 周末可以学习，但效率可能较低
            else:
                return -5

        return 0


# 全局单例
holiday_service = HolidayService()
