"""
测试 task_buffer_minutes 字段是否正常工作
"""
import requests
import json

BASE_URL = "http://localhost:8080"

print("=" * 70)
print("🧪 测试 task_buffer_minutes 字段")
print("=" * 70)

# 1. 获取当前用户偏好设置
print("\n【步骤1】获取当前用户偏好设置")
print("-" * 70)
response = requests.get(f"{BASE_URL}/api/preferences/", params={"user_id": 1})
if response.status_code == 200:
    data = response.json()
    prefs = data.get("preferences", {})
    print(f"✅ 获取成功")
    print(f"   当前缓冲时间: {prefs.get('task_buffer_minutes', '未设置')} 分钟")
    print(f"   完整偏好设置: {json.dumps(prefs, ensure_ascii=False, indent=2)}")
else:
    print(f"❌ 获取失败: {response.status_code}")
    print(f"   响应: {response.text}")

# 2. 更新缓冲时间为30分钟
print("\n【步骤2】更新缓冲时间为30分钟")
print("-" * 70)
update_data = {"task_buffer_minutes": 30}
response = requests.post(f"{BASE_URL}/api/preferences/", json={**update_data, "user_id": 1})
if response.status_code == 200:
    data = response.json()
    prefs = data.get("preferences", {})
    print(f"✅ 更新成功")
    print(f"   新缓冲时间: {prefs.get('task_buffer_minutes')} 分钟")
else:
    print(f"❌ 更新失败: {response.status_code}")
    print(f"   响应: {response.text}")

# 3. 再次获取确认更新
print("\n【步骤3】再次获取确认更新")
print("-" * 70)
response = requests.get(f"{BASE_URL}/api/preferences/", params={"user_id": 1})
if response.status_code == 200:
    data = response.json()
    prefs = data.get("preferences", {})
    print(f"✅ 获取成功")
    print(f"   当前缓冲时间: {prefs.get('task_buffer_minutes')} 分钟")

    if prefs.get('task_buffer_minutes') == 30:
        print("\n🎉 测试通过！task_buffer_minutes 字段工作正常！")
    else:
        print(f"\n⚠️ 警告：期望值为30，实际值为{prefs.get('task_buffer_minutes')}")
else:
    print(f"❌ 获取失败: {response.status_code}")

print("\n" + "=" * 70)
print("✅ 测试完成")
print("=" * 70)
