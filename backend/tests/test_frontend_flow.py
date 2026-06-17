"""
完整模拟前端保存流程
"""
import requests
import json
import time

base_url = "http://localhost:8080"

print("=" * 70)
print("模拟前端完整保存流程")
print("=" * 70)

# 1. 先设置为student
print("\n1. 设置user_type为student...")
response = requests.post(
    f"{base_url}/api/preferences/user-type",
    json={"user_type": "student", "user_id": 1},
    headers={"Content-Type": "application/json"}
)

print(f"   状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   返回消息: {data.get('message', 'N/A')}")
    print(f"   返回的user_type: {data.get('preferences', {}).get('user_type', 'MISSING')}")
else:
    print(f"   错误: {response.text}")

# 2. 等待1秒确保数据库写入完成
time.sleep(1)

# 3. 查询确认
print("\n2. 查询确认...")
response = requests.get(f"{base_url}/api/preferences/?user_id=1")
if response.status_code == 200:
    data = response.json()
    prefs = data.get('preferences', {})
    print(f"   数据库中 user_type: {prefs.get('user_type', 'MISSING')}")
else:
    print(f"   查询失败: {response.status_code}")

# 4. 测试个性化参数
print("\n3. 设置个性化参数...")
response = requests.post(
    f"{base_url}/api/preferences/personalization-params",
    json={
        "workday_hours": 8.0,
        "preferred_time_slot": "morning",
        "time_slot_offset": 0,
        "user_id": 1
    },
    headers={"Content-Type": "application/json"}
)

print(f"   状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   返回消息: {data.get('message', 'N/A')}")
else:
    print(f"   错误: {response.text}")

# 5. 最终查询
print("\n4. 最终查询所有字段...")
response = requests.get(f"{base_url}/api/preferences/?user_id=1")
if response.status_code == 200:
    data = response.json()
    prefs = data.get('preferences', {})
    print(f"   user_type: {prefs.get('user_type', 'MISSING')}")
    print(f"   workday_hours: {prefs.get('workday_hours', 'MISSING')}")
    print(f"   preferred_time_slot: {prefs.get('preferred_time_slot', 'MISSING')}")
    print(f"   time_slot_offset: {prefs.get('time_slot_offset', 'MISSING')}")

print("\n" + "=" * 70)
print("请在浏览器中按以下步骤操作：")
print("=" * 70)
print("""
1. 打开浏览器开发者工具（F12）
2. 切换到 Network（网络）标签
3. 勾选 "Disable cache"（禁用缓存）
4. 刷新页面（Ctrl+F5）
5. 查找以下请求：
   - GET /api/preferences/?user_id=1
   - POST /api/preferences/user-type
   
6. 点击 GET /api/preferences/ 请求，查看 Response
7. 确认响应中包含：
   "user_type": "student"

如果响应中user_type是"worker"，请告诉我！
""")
