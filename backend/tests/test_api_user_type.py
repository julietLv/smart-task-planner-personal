"""
测试 API 返回的 user_type 字段
"""
import requests
import json

print("=" * 70)
print("测试 API 返回的用户画像数据")
print("=" * 70)

# 1. 先设置为学生
print("\n1. 设置用户类型为学生...")
response = requests.post(
    "http://localhost:8080/api/preferences/user-type",
    json={"user_type": "student", "user_id": 1}
)
print(f"   状态码: {response.status_code}")
print(f"   响应: {response.json()}")

# 2. 获取偏好设置
print("\n2. 获取偏好设置...")
response = requests.get("http://localhost:8080/api/preferences/?user_id=1")
print(f"   状态码: {response.status_code}")

data = response.json()
if data["success"]:
    prefs = data["preferences"]
    print(f"\n   ✅ API 返回的偏好设置:")
    print(f"      user_type: {prefs.get('user_type', 'MISSING')}")
    print(f"      workday_hours: {prefs.get('workday_hours', 'MISSING')}")
    print(f"      preferred_time_slot: {prefs.get('preferred_time_slot', 'MISSING')}")
    print(f"      time_slot_offset: {prefs.get('time_slot_offset', 'MISSING')}")
    
    if prefs.get('user_type') == 'student':
        print("\n   ✅ 测试通过！API 正确返回了 user_type = student")
    else:
        print(f"\n   ❌ 测试失败！期望 'student'，实际 '{prefs.get('user_type')}'")
else:
    print(f"   ❌ API 请求失败: {data}")

# 3. 恢复为 worker
print("\n3. 恢复用户类型为 worker...")
response = requests.post(
    "http://localhost:8080/api/preferences/user-type",
    json={"user_type": "worker", "user_id": 1}
)
print(f"   状态码: {response.status_code}")

print("\n" + "=" * 70)
print("测试完成！")
print("=" * 70)
