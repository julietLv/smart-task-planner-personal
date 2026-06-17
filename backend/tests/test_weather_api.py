"""测试和风天气API是否正常工作"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

api_key = os.getenv("WEATHER_API_KEY")
print(f"API密钥: {api_key}")
print(f"API密钥长度: {len(api_key) if api_key else 0}")

if not api_key:
    print("\n❌ 错误：未找到WEATHER_API_KEY环境变量")
    print("请检查 .env 文件是否正确配置")
    exit(1)

try:
    import requests

    # 测试广州天气
    city = "广州"
    location_id = "101280101"  # 广州的城市ID

    print(f"\n正在获取 {city} 的天气数据...")
    url = "https://api.qweather.com/v7/weather/3d"
    params = {
        "location": location_id,
        "key": api_key
    }

    response = requests.get(url, params=params, timeout=10)

    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ API调用成功！")
        print(f"返回码: {data.get('code')}")

        if data.get('code') == '200' and data.get('daily'):
            today = data['daily'][0]
            print(f"\n📅 今日天气数据（{today.get('fxDate')}）:")
            print(f"  最高温度: {today.get('tempMax')}°C")
            print(f"  最低温度: {today.get('tempMin')}°C")
            print(f"  白天天气: {today.get('textDay')}")
            print(f"  夜间天气: {today.get('textNight')}")
            print(f"  湿度: {today.get('humidity')}%")
            print(f"  风速: {today.get('windSpeedDay')}")
            print(f"  风向: {today.get('windDirDay')}")

            print(f"\n完整数据:")
            import json

            print(json.dumps(today, ensure_ascii=False, indent=2))
        else:
            print(f"\n❌ API返回数据格式错误: {data}")
    else:
        print(f"\n❌ HTTP请求失败: {response.status_code}")
        print(f"响应内容: {response.text}")

except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback

    traceback.print_exc()
