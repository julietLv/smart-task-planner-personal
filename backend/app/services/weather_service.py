"""backend/app/services/weather_service.py"""
import os
from datetime import datetime, date
from typing import Optional


class WeatherService:
    """天气服务 - 支持接入第三方天气API和多城市切换"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.api_key = os.getenv("WEATHER_API_KEY", "")
        self.default_city = os.getenv("DEFAULT_CITY", "北京")
        self.cache = {}  # 简单内存缓存
        self._use_mock = not self.api_key  # 如果没有API key，使用模拟数据

        if self._use_mock:
            print("⚠️ 未配置天气API，使用模拟数据")
        else:
            print(f"✅ 天气API已配置，默认城市: {self.default_city}")

        self._initialized = True

    def get_weather(self, check_date: date, city: str = None) -> dict:
        """
        获取指定城市指定日期的天气预报

        Args:
            check_date: 检查日期
            city: 城市名称（默认使用配置的默认城市）

        Returns:
            {
                "temperature": 25,
                "condition": "sunny",  # sunny/rainy/cloudy/snowy/stormy
                "humidity": 60,
                "wind_speed": 10
            }
        """
        city = city or self.default_city
        cache_key = f"{check_date.isoformat()}_{city}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        if self._use_mock:
            weather_data = self._get_mock_weather(check_date, city)
        else:
            weather_data = self._fetch_real_weather(check_date, city)

        self.cache[cache_key] = weather_data
        return weather_data

    def _get_mock_weather(self, check_date: date, city: str = "北京") -> dict:
        """生成模拟天气数据（基于日期哈希，保证同一天数据一致）"""
        import hashlib

        seed_str = f"{check_date.isoformat()}_{city}"
        seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)

        month = check_date.month

        if month in [12, 1, 2]:
            conditions = ["sunny"] * 4 + ["cloudy"] * 3 + ["rainy"] * 2 + ["snowy"] * 1
            temp_range = (-5, 10)
        elif month in [3, 4, 5]:
            conditions = ["sunny"] * 5 + ["cloudy"] * 3 + ["rainy"] * 2
            temp_range = (10, 25)
        elif month in [6, 7, 8]:
            conditions = ["sunny"] * 4 + ["cloudy"] * 2 + ["rainy"] * 3 + ["stormy"] * 1
            temp_range = (25, 35)
        else:
            conditions = ["sunny"] * 6 + ["cloudy"] * 3 + ["rainy"] * 1
            temp_range = (15, 25)

        condition = conditions[seed % len(conditions)]
        temperature = temp_range[0] + (seed % (temp_range[1] - temp_range[0]))
        humidity = 40 + (seed % 40)
        wind_speed = 5 + (seed % 20)
        
        temp_min = temperature - (5 + (seed % 10))
        
        wind_level = min(wind_speed, 12)
        wind_speed_kmh = wind_speed

        return {
            "temperature": temperature,
            "condition": condition,
            "humidity": humidity,
            "wind_level": wind_level,
            "wind_speed_kmh": wind_speed_kmh,
            "wind_speed": wind_level,
            "temp_min": temp_min,
            "city": city,
            "wind_scale": f"{wind_level}级"
        }

    def _get_city_location_id(self, city: str) -> str:
        """获取城市Location ID（和风天气）"""
        cache_key = f"location_{city}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            import requests
            
            # 付费版GeoAPI：使用专属域名 + /geo 路径前缀
            api_host = os.getenv("WEATHER_API_HOST", "devapi.qweather.com")
            url = f"https://{api_host}/geo/v2/city/lookup"
            
            params = {
                "location": city,
                "key": self.api_key
            }
            headers = {
                "X-QW-Api-Key": self.api_key
            }
            
            print(f"   🔍 查询城市ID: {city}")
            print(f"   URL: {url}")
            print(f"   参数: {params}")
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   API返回码: {data.get('code')}")
                print(f"   返回数据: {data}")
                
                if data.get("code") == "200" and data.get("location"):
                    location_id = data["location"][0]["id"]
                    location_name = data["location"][0].get("name", city)
                    self.cache[cache_key] = location_id
                    print(f"   ✅ 成功获取城市ID: {location_id} ({location_name})")
                    return location_id
                else:
                    print(f"   ⚠️ API返回异常: code={data.get('code')}")
            else:
                print(f"    HTTP请求失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ 获取城市ID失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 如果查询失败，抛出异常而不是返回默认值
        raise ValueError(f"无法获取城市 '{city}' 的Location ID，请检查城市名称是否正确")

    def _parse_qweather_response(self, data: dict, check_date: date) -> dict:
        """
        解析和风天气API响应数据
        
        Args:
            data: API返回的JSON数据
            check_date: 查询日期
            
        Returns:
            标准化天气数据字典
        """
        try:
            if data.get("code") != "200" or not data.get("daily"):
                raise ValueError(f"API返回异常: {data.get('code')}")
            
            # 找到对应日期的天气数据
            target_date_str = check_date.isoformat()
            target_daily = None
            
            for daily in data["daily"]:
                if daily.get("fxDate") == target_date_str:
                    target_daily = daily
                    break
            
            if not target_daily:
                # 如果没有找到对应日期，使用第一条数据（通常是今天）
                target_daily = data["daily"][0]
            
            # 解析天气状况
            condition_map = {
                "晴": "sunny",
                "多云": "cloudy",
                "阴": "cloudy",
                "小雨": "rainy",
                "中雨": "rainy",
                "大雨": "rainy",
                "暴雨": "stormy",
                "大暴雨": "stormy",
                "特大暴雨": "stormy",
                "小雪": "snowy",
                "中雪": "snowy",
                "大雪": "snowy",
                "暴雪": "snowy",
                "雷阵雨": "stormy",
                "阵雨": "rainy"
            }
            
            # 优先使用白天天气，夜间用夜间天气
            text_day = target_daily.get("textDay", "")
            condition = condition_map.get(text_day, "cloudy")
            
            # 解析温度
            temp_max = int(target_daily.get("tempMax", 20))
            temp_min = int(target_daily.get("tempMin", 10))
            temperature = (temp_max + temp_min) // 2
            
            # 解析湿度
            humidity = int(target_daily.get("humidity", 50))
            
            # 解析风速和风力
            wind_speed_kmh = int(target_daily.get("windSpeedDay", "15").split("-")[0]) if target_daily.get("windSpeedDay") else 15
            
            # 修复：windScaleDay 可能是范围值如 "1-3"，取最大值
            wind_scale_str = target_daily.get("windScaleDay", "3")
            if wind_scale_str and "-" in str(wind_scale_str):
                # 如果是范围值，取最大值
                wind_level = int(wind_scale_str.split("-")[1])
            else:
                wind_level = int(wind_scale_str) if wind_scale_str else 3
            
            return {
                "temperature": temperature,
                "condition": condition,
                "humidity": humidity,
                "wind_level": wind_level,
                "wind_speed_kmh": wind_speed_kmh,
                "wind_speed": wind_level,
                "temp_min": temp_min,
                "wind_scale": f"{wind_level}级"
            }
            
        except Exception as e:
            print(f"⚠️ 解析天气数据失败: {e}")
            raise

    def _wind_level_to_speed(self, level: int) -> int:
        """
        将风力等级转换为风速范围中间值(km/h)
        """
        speed_ranges = {
            0: 0, 1: 3, 2: 8, 3: 15, 4: 24,
            5: 33, 6: 44, 7: 55, 8: 68, 9: 81,
            10: 95, 11: 110, 12: 125, 13: 141, 14: 158,
            15: 175, 16: 192, 17: 210
        }
        return speed_ranges.get(level, 15)

    def _wind_speed_to_level(self, speed_kmh: int) -> int:
        """
        将风速(km/h)转换为风力等级（0-17级）
        
        根据中国气象局风力等级标准：
        0级: <1 km/h
        1级: 1-5 km/h
        2级: 6-11 km/h
        3级: 12-19 km/h
        4级: 20-28 km/h
        5级: 29-38 km/h
        6级: 39-49 km/h
        7级: 50-61 km/h
        8级: 62-74 km/h
        9级: 75-88 km/h
        10级: 89-102 km/h
        11级: 103-117 km/h
        12级: 118-133 km/h
        13级: 134-149 km/h
        14级: 150-166 km/h
        15级: 167-183 km/h
        16级: 184-201 km/h
        17级: >201 km/h
        """
        if speed_kmh < 1:
            return 0
        elif speed_kmh <= 5:
            return 1
        elif speed_kmh <= 11:
            return 2
        elif speed_kmh <= 19:
            return 3
        elif speed_kmh <= 28:
            return 4
        elif speed_kmh <= 38:
            return 5
        elif speed_kmh <= 49:
            return 6
        elif speed_kmh <= 61:
            return 7
        elif speed_kmh <= 74:
            return 8
        elif speed_kmh <= 88:
            return 9
        elif speed_kmh <= 102:
            return 10
        elif speed_kmh <= 117:
            return 11
        elif speed_kmh <= 133:
            return 12
        elif speed_kmh <= 149:
            return 13
        elif speed_kmh <= 166:
            return 14
        elif speed_kmh <= 183:
            return 15
        elif speed_kmh <= 201:
            return 16
        else:
            return 17

    def _fetch_real_weather(self, check_date: date, city: str) -> dict:
        """
        从和风天气API获取真实数据
        """
        try:
            import requests

            print(f"🌤️ 开始获取 {city} {check_date} 的真实天气数据...")
            
            location_id = self._get_city_location_id(city)
            print(f"   城市ID: {location_id}")

            # 使用环境变量中的专属API Host
            api_host = os.getenv("WEATHER_API_HOST", "devapi.qweather.com")
            url = f"https://{api_host}/v7/weather/3d"
            
            params = {
                "location": location_id,
                "key": self.api_key
            }
            
            headers = {
                "X-QW-Api-Key": self.api_key
            }
            
            print(f"   请求URL: {url}")
            print(f"   请求参数: {params}")
            print(f"   请求头: X-QW-Api-Key: {self.api_key[:10]}...")

            response = requests.get(url, params=params, headers=headers, timeout=5)
            print(f"   响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   API返回码: {data.get('code')}")
                print(f"   API返回数据: {data}")
                
                weather_data = self._parse_qweather_response(data, check_date)
                weather_data["city"] = city
                print(f"   ✅ 成功获取真实天气数据")
                return weather_data
            else:
                print(f"   ❌ HTTP请求失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"⚠️ 获取{city}真实天气失败: {e}")
            import traceback
            traceback.print_exc()

        print(f"   ⚠️ 降级使用模拟数据")
        return self._get_mock_weather(check_date, city)

    def get_weather_impact_score(self, check_date: date, task_type: str, city: str = None) -> float:
        """
        计算天气对任务的影响分数（-30~20分）

        Args:
            check_date: 检查日期
            task_type: 任务类型
            city: 城市名称（可选）

        Returns:
            影响分数
        """
        weather = self.get_weather(check_date, city)
        condition = weather["condition"]
        temperature = weather["temperature"]

        # 户外运动受天气影响大
        if task_type == "exercise":
            condition_scores = {
                "sunny": 20,  # 晴天非常适合运动
                "cloudy": 10,  # 多云还可以
                "rainy": -30,  # 雨天不适合户外运动
                "stormy": -30,  # 暴雨非常危险
                "snowy": -20  # 雪天较冷
            }

            base_score = condition_scores.get(condition, 0)

            # 温度极端时额外扣分
            if temperature < 0 or temperature > 35:
                base_score -= 10
            elif temperature < 5 or temperature > 30:
                base_score -= 5

            return base_score

        # 室内活动受影响小
        if task_type in ["meeting", "study", "work"]:
            if condition in ["rainy", "stormy", "snowy"]:
                return 5  # 恶劣天气反而适合室内工作
            elif condition == "sunny":
                return 0  # 晴天无特殊影响
            else:
                return 0

        # 其他任务
        if condition in ["rainy", "stormy"]:
            return -10  # 下雨天稍微不方便
        elif condition == "sunny":
            return 5  # 晴天稍微加分

        return 0


# 全局单例
weather_service = WeatherService()
