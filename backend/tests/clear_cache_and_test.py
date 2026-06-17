"""
清除localStorage缓存并验证user_type字段
"""
import requests
import json

print("=" * 70)
print("测试用户画像数据")
print("=" * 70)

base_url = "http://localhost:8080"

print("\n1. 直接查询数据库中的user_type值...")
# 直接通过Python连接数据库查询
import sys
sys.path.insert(0, 'D:/demo_plan/backend')

from app.models.task_model import get_user_preferences

prefs = get_user_preferences(user_id=1)
if prefs:
    print(f"   ✅ 数据库中 user_type: {prefs.user_type}")
    print(f"   ✅ workday_hours: {prefs.workday_hours}")
    print(f"   ✅ preferred_time_slot: {prefs.preferred_time_slot}")
    print(f"   ✅ time_slot_offset: {prefs.time_slot_offset}")
else:
    print("   ❌ 未找到用户偏好记录")

print("\n2. 测试API GET请求返回的数据...")
response = requests.get(f"{base_url}/api/preferences/?user_id=1")
if response.status_code == 200:
    data = response.json()
    prefs_data = data.get('preferences', {})
    print(f"   ✅ API返回 user_type: {prefs_data.get('user_type', 'MISSING')}")
    print(f"   ✅ API返回 workday_hours: {prefs_data.get('workday_hours', 'MISSING')}")
    print(f"   ✅ API返回 preferred_time_slot: {prefs_data.get('preferred_time_slot', 'MISSING')}")
    print(f"   ✅ API返回 time_slot_offset: {prefs_data.get('time_slot_offset', 'MISSING')}")
    
    # 打印完整的preferences JSON
    print("\n3. 完整的preferences JSON（前500字符）:")
    print(json.dumps(prefs_data, ensure_ascii=False, indent=2)[:500])
else:
    print(f"   ❌ API请求失败: {response.status_code}")

print("\n" + "=" * 70)
print("浏览器操作说明：")
print("=" * 70)
print("""
请在浏览器中按以下步骤操作：

1. 打开开发者工具（F12）
2. 切换到 Console（控制台）标签
3. 粘贴并运行以下代码清除缓存：

   localStorage.removeItem('preferences_1')
   console.log('✅ 缓存已清除')

4. 然后刷新页面（Ctrl+F5）
5. 在Network标签中查找 /api/preferences/?user_id=1 请求
6. 查看该请求的Response，确认包含：
   - "user_type": "student" (或其他你设置的值)
   - "workday_hours": 8.0
   - "preferred_time_slot": "morning"
   - "time_slot_offset": 0

如果API返回的数据正确，但页面仍然显示"worker"，请告诉我！
""")
