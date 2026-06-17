"""
端到端测试用例 - 智能任务规划系统
测试完整业务流程
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8080"


class TestTaskPlanningSystem:
    """智能任务规划系统端到端测试"""

    def __init__(self):
        self.base_url = BASE_URL
        self.user_id = 1
        self.session = requests.Session()

    # ==================== 健康检查 ====================

    def test_health_check(self):
        """测试1: 健康检查"""
        print("\n🔍 测试1: 健康检查")
        response = self.session.get(f"{self.base_url}/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("✅ 健康检查通过")
        return True

    # ==================== 任务管理测试 ====================

    def test_create_task_with_scheduling(self):
        """测试2: 创建任务并自动排程"""
        print("\n📝 测试2: 创建任务并自动排程")

        task_data = {
            "title": "完成Python作业",
            "description": "编写一个完整的Python项目",
            "duration": 120,
            "deadline": (datetime.now() + timedelta(days=3)).isoformat(),
            "priority": "high",
            "user_id": self.user_id
        }

        response = self.session.post(
            f"{self.base_url}/api/tasks/",
            json=task_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        if data.get("has_conflict"):
            print(f"⚠️ 检测到冲突: {data['message']}")
        else:
            print(f"✅ 任务创建成功，已安排到: {data['task']['start_time']}")

        return data.get("task")

    def test_get_all_tasks(self):
        """测试3: 获取所有任务"""
        print("\n📋 测试3: 获取所有任务")

        response = self.session.get(
            f"{self.base_url}/api/tasks/",
            params={"user_id": self.user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 共 {data['count']} 个任务")
        for task in data["tasks"][:3]:
            print(f"   - {task['title']} ({task['status']})")

        return data["tasks"]

    def test_update_task(self):
        """测试4: 更新任务"""
        print("\n✏️ 测试4: 更新任务")

        # 先获取一个任务
        tasks = self.test_get_all_tasks()
        if not tasks:
            print("⚠️ 没有可更新的任务")
            return None

        task_id = tasks[0]["id"]
        update_data = {
            "priority": "high",
            "status": "done"
        }

        response = self.session.put(
            f"{self.base_url}/api/tasks/{task_id}",
            json=update_data,
            params={"user_id": self.user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 任务 {task_id} 更新成功")
        return data["task"]

    def test_delete_task(self):
        """测试5: 删除任务"""
        print("\n🗑️ 测试5: 删除任务")

        # 创建一个临时任务用于删除
        temp_task = {
            "title": "临时测试任务",
            "duration": 30,
            "priority": "low",
            "user_id": self.user_id
        }

        create_response = self.session.post(
            f"{self.base_url}/api/tasks/",
            json=temp_task
        )
        task_id = create_response.json()["task"]["id"]

        # 删除任务
        response = self.session.delete(
            f"{self.base_url}/api/tasks/{task_id}",
            params={"user_id": self.user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 任务 {task_id} 删除成功")
        return True

    # ==================== 自然语言解析测试 ====================

    def test_parse_natural_language(self):
        """测试6: 自然语言解析"""
        print("\n🧠 测试6: 自然语言解析")

        test_cases = [
            "明天下午3点开会，预计1小时",
            "周三前完成数学作业，优先级高",
            "本周五之前写完项目报告"
        ]

        for text in test_cases:
            response = self.session.post(
                f"{self.base_url}/api/tasks/parse",
                json={"text": text}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            print(f"✅ 解析成功: '{text}'")
            print(f"   意图: {data['intent']}")
            print(f"   实体: {data['entities'].get('title', 'N/A')}")

        return True

    # ==================== 聊天功能测试 ====================

    def test_chat_add_task(self):
        """测试7: 聊天添加任务"""
        print("\n💬 测试7: 聊天添加任务")

        response = self.session.post(
            f"{self.base_url}/api/chat/",
            json={
                "message": "明天上午10点健身，预计1.5小时",
                "user_id": self.user_id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 回复: {data['reply'][:100]}...")

        if data.get("task_preview"):
            print(f"   识别任务: {data['task_preview']['title']}")

        return data

    def test_chat_query_schedule(self):
        """测试8: 聊天查询日程"""
        print("\n💬 测试8: 聊天查询日程")

        response = self.session.post(
            f"{self.base_url}/api/chat/",
            json={
                "message": "我明天有什么任务",
                "user_id": self.user_id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 回复: {data['reply'][:100]}...")
        return data

    def test_chat_weekly_summary(self):
        """测试9: 聊天生成本周总结"""
        print("\n💬 测试9: 聊天生成本周总结")

        response = self.session.post(
            f"{self.base_url}/api/chat/",
            json={
                "message": "本周总结",
                "user_id": self.user_id
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 周报生成成功")
        print(f"   回复长度: {len(data['reply'])} 字符")
        print(f"\n{data['reply'][:500]}...")

        return data

    # ==================== 通知和提醒测试 ====================

    def test_deadline_reminders(self):
        """测试10: 截止提醒"""
        print("\n⏰ 测试10: 截止提醒")

        response = self.session.get(
            f"{self.base_url}/api/notifications/reminders",
            params={"user_id": self.user_id, "hours_before": 24}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 找到 {data['count']} 个提醒")
        for reminder in data["reminders"][:3]:
            print(f"   - {reminder['message']}")

        return data

    def test_daily_summary(self):
        """测试11: 每日摘要"""
        print("\n📅 测试11: 每日摘要")

        response = self.session.get(
            f"{self.base_url}/api/notifications/daily-summary",
            params={"user_id": self.user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 每日摘要生成成功")
        print(f"\n{data['summary'][:300]}...")

        return data

    def test_weekly_summary_api(self):
        """测试12: 每周摘要API"""
        print("\n📆 测试12: 每周摘要API")

        response = self.session.get(
            f"{self.base_url}/api/notifications/weekly-summary",
            params={"user_id": self.user_id, "week_offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 每周摘要生成成功")
        stats = data.get("stats", {})
        print(f"   总任务: {stats.get('total_tasks', 0)}")
        print(f"   已完成: {stats.get('done_tasks', 0)}")
        print(f"   完成率: {(stats.get('done_tasks', 0) / max(stats.get('total_tasks', 1), 1) * 100):.1f}%")

        return data

    # ==================== 冲突检测测试 ====================

    def test_conflict_detection(self):
        """测试13: 冲突检测"""
        print("\n⚠️ 测试13: 冲突检测")

        response = self.session.get(
            f"{self.base_url}/api/tasks/conflicts",
            params={"user_id": self.user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 冲突检测完成")
        print(f"   总任务: {data['total_tasks']}")
        print(f"   冲突数: {data['conflict_count']}")

        return data

    # ==================== 用户偏好测试 ====================

    def test_user_preferences(self):
        """测试14: 用户偏好设置"""
        print("\n⚙️ 测试14: 用户偏好设置")

        # 获取偏好
        response = self.session.get(
            f"{self.base_url}/api/preferences/",
            params={"user_id": self.user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print(f"✅ 当前偏好:")
        prefs = data["preferences"]
        print(f"   免安排时间: {prefs['blocked_time_start']} - {prefs['blocked_time_end']}")
        print(f"   默认优先级: {prefs['default_priority']}")

        # 更新偏好
        update_data = {
            "blocked_time_start": "23:00",
            "blocked_time_end": "07:00",
            "default_priority": "high"
        }

        response = self.session.post(
            f"{self.base_url}/api/preferences/",
            json={**update_data, "user_id": self.user_id}
        )

        assert response.status_code == 200
        print(f"✅ 偏好更新成功")

        return data

    # ==================== WebSocket测试 ====================

    def test_websocket_connection(self):
        """测试15: WebSocket连接"""
        print("\n🔌 测试15: WebSocket连接")

        try:
            import asyncio
            import websockets

            async def connect_ws():
                uri = f"ws://localhost:8080/ws/{self.user_id}"
                async with websockets.connect(uri) as websocket:
                    # 接收欢迎消息
                    welcome = await websocket.recv()
                    welcome_data = json.loads(welcome)

                    assert welcome_data["type"] == "welcome"
                    print(f"✅ WebSocket连接成功")
                    print(f"   消息: {welcome_data['data']['message']}")

                    # 发送心跳
                    await websocket.send(json.dumps({"type": "heartbeat"}))
                    ack = await websocket.recv()
                    ack_data = json.loads(ack)

                    assert ack_data["type"] == "heartbeat_ack"
                    print(f"✅ 心跳响应正常")

            asyncio.run(connect_ws())
            return True

        except Exception as e:
            print(f"❌ WebSocket测试失败: {e}")
            return False

    # ==================== 运行所有测试 ====================

    def run_all_tests(self):
        """运行所有端到端测试"""
        print("=" * 60)
        print("🚀 智能任务规划系统 - 端到端测试")
        print("=" * 60)

        tests = [
            ("健康检查", self.test_health_check),
            ("创建任务", self.test_create_task_with_scheduling),
            ("获取任务列表", self.test_get_all_tasks),
            ("更新任务", self.test_update_task),
            ("删除任务", self.test_delete_task),
            ("自然语言解析", self.test_parse_natural_language),
            ("聊天添加任务", self.test_chat_add_task),
            ("聊天查询日程", self.test_chat_query_schedule),
            ("聊天生成周报", self.test_chat_weekly_summary),
            ("截止提醒", self.test_deadline_reminders),
            ("每日摘要", self.test_daily_summary),
            ("每周摘要API", self.test_weekly_summary_api),
            ("冲突检测", self.test_conflict_detection),
            ("用户偏好", self.test_user_preferences),
            ("WebSocket连接", self.test_websocket_connection),
        ]

        results = []
        for name, test_func in tests:
            try:
                result = test_func()
                results.append((name, "✅ 通过", result))
            except AssertionError as e:
                results.append((name, "❌ 断言失败", str(e)))
                print(f"❌ {name} 失败: {e}")
            except Exception as e:
                results.append((name, "❌ 异常", str(e)))
                print(f"❌ {name} 异常: {e}")

        # 打印测试总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        print("=" * 60)

        passed = sum(1 for _, status, _ in results if "通过" in status)
        failed = len(results) - passed

        for name, status, _ in results:
            print(f"{status} {name}")

        print("\n" + "-" * 60)
        print(f"总计: {len(results)} 个测试")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print("=" * 60)

        return passed == len(results)


if __name__ == "__main__":
    tester = TestTaskPlanningSystem()
    success = tester.run_all_tests()

    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败，请检查日志")
