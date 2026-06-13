"""
测试设置user_type为student
"""
import requests
import json

base_url = "http://localhost:8080"

print("=" * 70)
print("测试设置user_type")
print("=" * 70)

# 1. 先设置为student
print("\n1. 尝试设置user_type为student...")
response = requests.post(
    f"{base_url}/api/preferences/user-type",
    json={"user_type": "student", "user_id": 1},
    headers={"Content-Type": "application/json"}
)

print(f"   状态码: {response.status_code}")
print(f"   响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

# 2. 立即查询确认
print("\n2. 立即查询确认...")
response = requests.get(f"{base_url}/api/preferences/?user_id=1")
if response.status_code == 200:
    data = response.json()
    prefs = data.get('preferences', {})
    print(f"   数据库中 user_type: {prefs.get('user_type', 'MISSING')}")
else:
    print(f"   查询失败: {response.status_code}")

# 3. 使用通用更新接口测试
print("\n3. 使用通用更新接口测试...")
response = requests.post(
    f"{base_url}/api/preferences/",
    json={"user_type": "student", "user_id": 1},
    headers={"Content-Type": "application/json"}
)

print(f"   状态码: {response.status_code}")
print(f"   响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)[:300]}")

# 4. 再次查询
print("\n4. 再次查询确认...")
response = requests.get(f"{base_url}/api/preferences/?user_id=1")
if response.status_code == 200:
    data = response.json()
    prefs = data.get('preferences', {})
    print(f"   数据库中 user_type: {prefs.get('user_type', 'MISSING')}")
