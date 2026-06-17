"""
测试 Phase 3 API 端点
使用 FastAPI TestClient 进行自动化测试，无需启动服务器
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
import main

app = main.app

# 创建测试客户端
client = TestClient(app)


def test_set_user_type():
    """测试1: POST /api/preferences/user-type - 设置用户类型"""
    
    print("\n" + "=" * 70)
    print("测试1: 设置用户类型")
    print("=" * 70)
    
    # 测试1.1: 设置为学生
    print("\n[INFO] 测试1.1: 设置为用户类型为学生")
    response = client.post("/api/preferences/user-type", json={
        "user_type": "student",
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 成功: {data['message']}")
        print(f"   user_type: {data['preferences']['user_type']}")
    else:
        print(f"   ❌ 失败: {response.text}")
    
    # 测试1.2: 设置为工作者
    print("\n[INFO] 测试1.2: 设置为用户类型为工作者")
    response = client.post("/api/preferences/user-type", json={
        "user_type": "worker",
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 成功: {data['message']}")
        print(f"   user_type: {data['preferences']['user_type']}")
    else:
        print(f"   ❌ 失败: {response.text}")
    
    # 测试1.3: 设置为老年人
    print("\n[INFO] 测试1.3: 设置为用户类型为老年人")
    response = client.post("/api/preferences/user-type", json={
        "user_type": "elderly",
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 成功: {data['message']}")
        print(f"   user_type: {data['preferences']['user_type']}")
    else:
        print(f"   ❌ 失败: {response.text}")
    
    # 测试1.4: 无效的用户类型
    print("\n[INFO] 测试1.4: 设置无效的用户类型（应失败）")
    response = client.post("/api/preferences/user-type", json={
        "user_type": "invalid_type",
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✅ 正确拒绝: {response.json()['detail']}")
    else:
        print(f"   ❌ 应该返回400错误")


def test_get_standard_profiles():
    """测试2: GET /api/preferences/standard-profiles - 获取标准模板"""
    
    print("\n" + "=" * 70)
    print("测试2: 获取标准作息模板")
    print("=" * 70)
    
    response = client.get("/api/preferences/standard-profiles")
    
    print(f"\n   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 成功获取 {len(data['profiles'])} 个模板")
        
        for profile_type, profile in data['profiles'].items():
            print(f"\n   📋 {profile['name']}:")
            print(f"      描述: {profile['description']}")
            schedule = profile['typical_schedule']
            print(f"      起床: {schedule['wake_up']}, 睡觉: {schedule['sleep']}")
            print(f"      高效时段: {', '.join(schedule['productive_hours'])}")
    else:
        print(f"   ❌ 失败: {response.text}")


def test_set_personalization_params():
    """测试3: POST /api/preferences/personalization-params - 设置个性化参数"""
    
    print("\n" + "=" * 70)
    print("测试3: 设置个性化参数（带自动校验）")
    print("=" * 70)
    
    # 测试3.1: 正常参数
    print("\n[INFO] 测试3.1: 设置正常参数")
    response = client.post("/api/preferences/personalization-params", json={
        "workday_hours": 8,
        "preferred_time_slot": "evening",
        "max_continuous_work": 4,
        "min_break_minutes": 15,
        "time_slot_offset": 1,
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 成功: {data['message']}")
        print(f"   验证通过参数: {list(data['validated_params'].keys())}")
        print(f"   校验错误: {len(data['validation_errors'])} 个")
    else:
        print(f"   ❌ 失败: {response.text}")
    
    # 测试3.2: 需要校正的参数
    print("\n[INFO] 测试3.2: 设置需要校正的参数")
    response = client.post("/api/preferences/personalization-params", json={
        "workday_hours": 15,  # 过长，应校正为12
        "time_slot_offset": 5,  # 过度推迟，应校正为3
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ⚠️ 部分校正: {data['message']}")
        print(f"   验证通过参数: {data['validated_params']}")
        print(f"   校验错误数: {len(data['validation_errors'])}")
        
        for error in data['validation_errors']:
            print(f"      - {error['param']}: {error['error']}")
            print(f"        校正值: {error['corrected_value']}")
    else:
        print(f"   ❌ 失败: {response.text}")
    
    # 测试3.3: 无效的偏好时段
    print("\n[INFO] 测试3.3: 设置无效的偏好时段")
    response = client.post("/api/preferences/personalization-params", json={
        "preferred_time_slot": "invalid_slot",
        "user_id": 1
    })
    
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ⚠️ 校验错误数: {len(data['validation_errors'])}")
        
        for error in data['validation_errors']:
            print(f"      - {error['param']}: {error['error']}")
    else:
        print(f"   ❌ 失败: {response.text}")


def test_get_preferences():
    """测试4: GET /api/preferences/ - 获取当前偏好"""
    
    print("\n" + "=" * 70)
    print("测试4: 获取当前用户偏好")
    print("=" * 70)
    
    response = client.get("/api/preferences/", params={"user_id": 1})
    
    print(f"\n   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        prefs = data['preferences']
        print(f"   ✅ 成功获取偏好设置")
        print(f"   user_id: {prefs['user_id']}")
        print(f"   user_type: {prefs['user_type']}")
        print(f"   user_city: {prefs['user_city']}")
        print(f"   blocked_time: {prefs['blocked_time_start']} - {prefs['blocked_time_end']}")
        print(f"   default_priority: {prefs['default_priority']}")
        print(f"   task_buffer_minutes: {prefs['task_buffer_minutes']}")
    else:
        print(f"   ❌ 失败: {response.text}")


if __name__ == "__main__":
    print("\n开始测试 Phase 3 API 端点...\n")
    
    test_set_user_type()
    test_get_standard_profiles()
    test_set_personalization_params()
    test_get_preferences()
    
    print("\n" + "=" * 70)
    print("所有API测试完成！")
    print("=" * 70 + "\n")
