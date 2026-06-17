"""Holiday service - Multi-country support using the `holidays` library."""

from datetime import datetime, date
from functools import lru_cache
from typing import Optional

import holidays


# Country display info: code -> (english_name, chinese_name)
COUNTRY_INFO = {
    "CN": ("China", "中国"),
    "HK": ("Hong Kong", "中国香港"),
    "TW": ("Taiwan", "中国台湾"),
    "US": ("United States", "美国"),
    "GB": ("United Kingdom", "英国"),
    "JP": ("Japan", "日本"),
    "KR": ("South Korea", "韩国"),
    "DE": ("Germany", "德国"),
    "FR": ("France", "法国"),
    "IT": ("Italy", "意大利"),
    "ES": ("Spain", "西班牙"),
    "CA": ("Canada", "加拿大"),
    "AU": ("Australia", "澳大利亚"),
    "RU": ("Russia", "俄罗斯"),
    "BR": ("Brazil", "巴西"),
    "IN": ("India", "印度"),
    "SG": ("Singapore", "新加坡"),
    "MY": ("Malaysia", "马来西亚"),
    "TH": ("Thailand", "泰国"),
    "VN": ("Vietnam", "越南"),
    "PH": ("Philippines", "菲律宾"),
    "ID": ("Indonesia", "印度尼西亚"),
    "AE": ("United Arab Emirates", "阿联酋"),
    "SA": ("Saudi Arabia", "沙特阿拉伯"),
    "IL": ("Israel", "以色列"),
    "TR": ("Turkey", "土耳其"),
    "ZA": ("South Africa", "南非"),
    "EG": ("Egypt", "埃及"),
    "NL": ("Netherlands", "荷兰"),
    "SE": ("Sweden", "瑞典"),
    "NO": ("Norway", "挪威"),
    "DK": ("Denmark", "丹麦"),
    "FI": ("Finland", "芬兰"),
    "CH": ("Switzerland", "瑞士"),
    "AT": ("Austria", "奥地利"),
    "BE": ("Belgium", "比利时"),
    "PT": ("Portugal", "葡萄牙"),
    "PL": ("Poland", "波兰"),
    "CZ": ("Czechia", "捷克"),
    "HU": ("Hungary", "匈牙利"),
    "RO": ("Romania", "罗马尼亚"),
    "GR": ("Greece", "希腊"),
    "IE": ("Ireland", "爱尔兰"),
    "NZ": ("New Zealand", "新西兰"),
    "AR": ("Argentina", "阿根廷"),
    "CL": ("Chile", "智利"),
    "CO": ("Colombia", "哥伦比亚"),
    "MX": ("Mexico", "墨西哥"),
    "KE": ("Kenya", "肯尼亚"),
    "NG": ("Nigeria", "尼日利亚"),
}


class HolidayService:
    """Holiday service - multi-country support using the `holidays` library.

    Uses the Python `holidays` library (https://github.com/dr-prodigy/python-holidays)
    to provide accurate public holiday data for 150+ countries and territories.

    Features:
    - Automatic holiday calendar updates per country and year
    - Handles complex holiday rules (lunar calendar, floating dates, etc.)
    - Correct weekend day detection per country (e.g., Fri-Sat in Israel/UAE)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── cached helpers ────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=256)
    def _get_holidays(country: str, year: int) -> "holidays.CountryHolidays":
        """Get cached CountryHolidays instance for a given country and year."""
        try:
            return holidays.country_holidays(country, years=year)
        except Exception:
            return holidays.country_holidays("CN", years=year)

    @staticmethod
    @lru_cache(maxsize=64)
    def _get_weekend(country: str) -> set:
        """Get weekend days for a country (Monday=0 ... Sunday=6)."""
        # Check manual overrides first (for countries where library returns wrong data)
        if country in WEEKEND_OVERRIDES:
            return WEEKEND_OVERRIDES[country]
        try:
            cal = holidays.country_holidays(country, years=2024)
            return cal.weekend
        except Exception:
            return {5, 6}

    @staticmethod
    def _is_supplementary_rest_day(holiday_name: str) -> bool:
        """Check if a holiday name indicates a supplementary rest day (调休).

        Only matches the holidays library pattern "休息日（由 X 调休）",
        NOT the generic weekend label "休息日" from _get_weekend_name.
        """
        if not holiday_name:
            return False
        if "休息日" not in holiday_name:
            return False
        return "（由" in holiday_name and "调休）" in holiday_name

    # ── public API ────────────────────────────────────

    def is_holiday(self, check_date: date, country: str = "CN") -> bool:
        """Check whether a date is a holiday or weekend for the given country."""
        holidays_cal = self._get_holidays(country, check_date.year)
        if check_date in holidays_cal:
            return True
        weekend = self._get_weekend(country)
        return check_date.weekday() in weekend

    def get_holiday_info(self, check_date: date, country: str = "CN") -> Optional[dict]:
        """Get structured holiday info for a date.

        Returns dict with keys:
          - date:         ISO date string
          - name:         Holiday name (None if not holiday/weekend)
          - is_weekend:   True if it's a weekend day
          - is_legal_holiday:  True if it's an official public holiday
        """
        name = self.get_holiday_name(check_date, country)
        if name is None:
            return None

        weekend = self._get_weekend(country)
        is_supplementary = self._is_supplementary_rest_day(name)
        is_weekend = check_date.weekday() in weekend

        # If the day is in the holiday calendar (not just a weekend), it's a legal holiday
        holidays_cal = self._get_holidays(country, check_date.year)
        in_holiday_calendar = check_date in holidays_cal

        if in_holiday_calendar and is_weekend and not is_supplementary:
            # e.g., Chinese New Year falls on a weekend → still a legal holiday
            is_legal = True
        elif is_supplementary:
            is_legal = False  # 调休 day
        elif in_holiday_calendar:
            is_legal = True
        else:
            is_legal = False

        return {
            "date": check_date.isoformat(),
            "name": name,
            "is_weekend": is_weekend,
            "is_legal_holiday": is_legal,
        }

    def get_holiday_name(self, check_date: date, country: str = "CN") -> Optional[str]:
        """Get holiday name for a date. Returns None if it's a regular workday."""
        date_str = check_date.strftime("%Y-%m-%d")

        # 1. Check the holidays library
        holidays_cal = self._get_holidays(country, check_date.year)
        holiday_name = holidays_cal.get(date_str)
        if holiday_name:
            return holiday_name

        # 2. Check weekend
        weekend = self._get_weekend(country)
        if check_date.weekday() in weekend:
            return self._get_weekend_name(country)

        return None

    @staticmethod
    def _get_weekend_name(country: str) -> str:
        """Get localized weekend name."""
        special = {
            "CN": "周末",
            "HK": "周末",
            "TW": "周末",
            "AE": "Weekend (Fri-Sat)", "SA": "Weekend (Fri-Sat)",
            "IL": "Weekend (Fri-Sat)", "IQ": "Weekend (Fri-Sat)",
            "IR": "Weekend (Fri)", "AF": "Weekend (Fri)",
            "NP": "Weekend (Sun)",
        }
        if country in special:
            return special[country]
        return "Weekend"

    def get_month_holidays(self, year: int, month: int, country: str = "CN") -> list:
        """Get all holiday/date info for a specific month."""
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        results = []
        for day in range(1, last_day + 1):
            d = date(year, month, day)
            info = self.get_holiday_info(d, country)
            if info:
                results.append(info)
        return results

    def get_holiday_impact_score(self, check_date: date, task_type: str,
                                 country: str = "CN") -> float:
        """Calculate holiday impact score for scheduling (-40 ~ 0).

        Kept for backward compatibility with the scheduling engine.
        """
        info = self.get_holiday_info(check_date, country)
        if not info:
            return 0.0

        is_legal = info["is_legal_holiday"]
        is_supplementary = self._is_supplementary_rest_day(info.get("name", ""))

        if is_legal:
            if task_type in ("meeting", "study", "work"):
                return -40.0
            elif task_type == "exercise":
                return -5.0
            else:
                return -15.0

        if is_supplementary:
            if task_type in ("meeting", "work"):
                return -25.0
            elif task_type == "study":
                return -15.0
            else:
                return -5.0

        # Weekends
        if task_type in ("meeting", "work"):
            return -20.0
        elif task_type == "study":
            return -10.0
        elif task_type == "exercise":
            return 0.0
        else:
            return -5.0

    @staticmethod
    def get_supported_countries() -> dict:
        """Get the supported country list for the frontend selector."""
        result = {}
        for code, (en, zh) in COUNTRY_INFO.items():
            if code in WEEKEND_OVERRIDES:
                # Use manual override
                js_weekend = sorted([(d + 1) % 7 for d in WEEKEND_OVERRIDES[code]])
            else:
                try:
                    cal = holidays.country_holidays(code, years=2024)
                    # Python weekday: 0=Mon ... 6=Sun. Convert to JS: 0=Sun ... 6=Sat
                    js_weekend = sorted([(d + 1) % 7 for d in cal.weekend])
                except Exception:
                    js_weekend = [0, 6]  # default Sat+Sun
            result[code] = {"en": en, "zh": zh, "weekend": js_weekend}
        return result


# Manual weekend overrides for countries where the holidays library returns incorrect values
# Format: Python weekday (0=Mon, 6=Sun)
WEEKEND_OVERRIDES = {
    'AE': {4, 5},   # UAE: Fri-Sat (library returns {5,6})
    'IR': {3, 4},   # Iran: Thu-Fri (library returns {4})
    'AF': {3, 4},   # Afghanistan: Thu-Fri (library returns {4,5})
    'NP': {5},      # Nepal: Sat only (library returns {5,6})
}

# Global singleton
holiday_service = HolidayService()