"""
打印API完整响应
"""
import requests
import json

base_url = "http://localhost:8080"

print("=" * 70)
print("获取完整的preferences响应")
print("=" * 70)

response = requests.get(f"{base_url}/api/preferences/?user_id=1")

if response.status_code == 200:
    data = response.json()
    prefs = data.get('preferences', {})
    
    print("\n完整的preferences JSON:")
    print(json.dumps(prefs, ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 70)
    print("关键字段检查:")
    print("=" * 70)
    print(f"user_type: {prefs.get('user_type', ' MISSING')}")
    print(f"workday_hours: {prefs.get('workday_hours', ' MISSING')}")
    print(f"preferred_time_slot: {prefs.get('preferred_time_slot', '❌ MISSING')}")
    print(f"time_slot_offset: {prefs.get('time_slot_offset', '❌ MISSING')}")
else:
    print(f"请求失败: {response.status_code}")
    print(response.text)
