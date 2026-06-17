"""
测试冲突检测和智能排程的缓冲时间一致性
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8080"

print("=" * 70)
print("🧪 测试冲突检测和智能排程的缓冲时间一致性")
print("=" * 70)

# ==================== 步骤1：设置缓冲时间为30分钟 ====================
print("\n【步骤1】设置缓冲时间为30分钟")
print("-" * 70)
response = requests.post(f"{BASE_URL}/api/preferences/", json={
    "task_buffer_minutes": 30,
    "user_id": 1
})
if response.status_code == 200:
    data = response.json()
    buffer_time = data["preferences"]["task_buffer_minutes"]
    print(f"✅ 缓冲时间已设置为: {buffer_time} 分钟")
else:
    print(f"❌ 设置失败: {response.text}")
    exit(1)

# ==================== 步骤2：创建一个基准任务 ====================
print("\n【步骤2】创建基准任务（09:00-10:00）")
print("-" * 70)
now = datetime.now()
today = now.strftime("%Y-%m-%d")
base_task_start = f"{today}T10:30:00"
base_task_end = f"{today}T11:30:00"

response = requests.post(f"{BASE_URL}/api/tasks/", json={
    "title": "晨会",
    "user_id": 1,
    "start_time": base_task_start,
    "end_time": base_task_end,
    "duration": 60,
    "priority": "high",
    "status": "pending"
})

if response.status_code == 200:
    result = response.json()
    task = result.get("task", {})
    if task:
        print(f"✅ 基准任务已创建: {task.get('title', '未知')} ({task.get('start_time', '')[11:16]}-{task.get('end_time', '')[11:16]})")
    else:
        # 可能有冲突，使用preview
        preview = result.get("task_preview", {})
        if preview:
            print(f"⚠️ 检测到冲突，但获取到预览: {preview.get('title')} ({preview.get('start_time', '')[11:16]}-{preview.get('end_time', '')[11:16]})")
            # 强制创建
            response = requests.post(f"{BASE_URL}/api/tasks/confirm", json={
                "action": "ignore",
                "task_data": preview,
                "user_id": 1
            })
            if response.status_code == 200:
                confirmed = response.json()
                task = confirmed.get("task", {})
                print(f"✅ 强制创建成功: {task.get('title')} ({task.get('start_time', '')[11:16]}-{task.get('end_time', '')[11:16]})")
        else:
            print(f"❌ 任务创建失败: {result}")
            exit(1)
else:
    print(f"❌ 任务创建失败: {response.status_code}")
    print(f"   响应: {response.text[:200]}")
    exit(1)

# ==================== 步骤3：尝试创建冲突任务（11:30-12:30）====================
print("\n【步骤3】尝试创建冲突任务（11:30-12:30，考虑30分钟缓冲）")
print("-" * 70)
conflict_task_start = f"{today}T11:30:00"
conflict_task_end = f"{today}T12:30:00"

# 通过聊天接口创建任务（这样才会触发冲突检测）
print(f"📤 发送请求: 帮我安排一个编程任务，今天{conflict_task_start[11:16]}到{conflict_task_end[11:16]}，时长60分钟")
response = requests.post(f"{BASE_URL}/api/chat/send", json={
    "message": f"帮我安排一个编程任务，今天{conflict_task_start[11:16]}到{conflict_task_end[11:16]}，时长60分钟",
    "user_id": 1
})

if response.status_code == 200:
    data = response.json()
    print(f"📝 AI回复: {data['reply'][:300]}...")
    print(f"🔍 意图: {data.get('intent', 'unknown')}")
    print(f"⚠️ 是否有冲突标志: {data.get('has_conflict', False)}")

    if data.get("has_conflict"):
        print(f"\n✅ 冲突检测成功！")
        print(f"   冲突数量: {len(data.get('conflicts', []))}")
        for conflict in data.get('conflicts', []):
            print(f"   - {conflict['message']}")

        # ==================== 步骤4：选择自动调整 ====================
        print("\n【步骤4】发送'调整'指令")
        print("-" * 70)
        response = requests.post(f"{BASE_URL}/api/chat/send", json={
            "message": "调整",
            "user_id": 1
        })

        if response.status_code == 200:
            data = response.json()
            print(f"📝 AI回复: {data['reply']}")
            print(f"🔍 意图: {data.get('intent', 'unknown')}")

            if data.get("success") and data.get("task"):
                new_task = data["task"]
                new_start = new_task["start_time"]
                new_end = new_task["end_time"]

                print(f"\n✅ 自动调整成功！")
                print(f"   新任务时间: {new_start[11:16]}-{new_end[11:16]}")

                # 验证缓冲时间是否正确
                base_end_time = datetime.fromisoformat(base_task_end)
                new_start_time = datetime.fromisoformat(new_start)
                actual_buffer = (new_start_time - base_end_time).total_seconds() / 60

                print(f"\n📊 缓冲时间验证:")
                print(f"   基准任务结束: {base_task_end[11:16]}")
                print(f"   新任务开始: {new_start[11:16]}")
                print(f"   实际缓冲: {actual_buffer:.0f} 分钟")
                print(f"   期望缓冲: 30 分钟")

                if 28 <= actual_buffer <= 32:  # 允许2分钟误差
                    print(f"\n🎉 测试通过！缓冲时间正确使用了30分钟！")
                else:
                    print(f"\n⚠️ 警告：缓冲时间不符合预期！")
            else:
                print(f"\n❌ 自动调整失败: {data.get('reply')}")
                print(f"   完整响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   响应: {response.text}")
    else:
        print(f"\n⚠️ 未检测到冲突（这可能有问题）")
else:
    print(f"❌ 请求失败: {response.status_code}")
    print(f"   响应: {response.text}")

print("\n" + "=" * 70)
print("✅ 测试完成")
print("=" * 70)
