"""
冲突检测功能测试脚本
测试场景：通过聊天接口创建任务，验证冲突检测是否生效
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8080"
USER_ID = 1


def print_separator(title):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def send_chat_message(message, user_id=USER_ID):
    """发送聊天消息"""
    url = f"{BASE_URL}/api/chat/send"
    payload = {
        "message": message,
        "user_id": user_id
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def get_all_tasks(user_id=USER_ID):
    """获取所有任务"""
    url = f"{BASE_URL}/api/tasks/"
    params = {"user_id": user_id}

    try:
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"❌ 获取任务失败: {e}")
        return None


def clear_all_tasks(user_id=USER_ID):
    """清理所有测试任务"""
    tasks = get_all_tasks(user_id)
    if tasks and tasks.get("tasks"):
        for task in tasks["tasks"]:
            try:
                url = f"{BASE_URL}/api/tasks/{task['id']}"
                requests.delete(url, params={"user_id": user_id})
            except:
                pass
        print("🗑️ 已清理所有测试任务")


def test_conflict_detection():
    """完整测试冲突检测流程"""

    print_separator("🚀 开始冲突检测测试")

    # 清理旧数据
    print("\n📋 步骤 0: 清理测试数据...")
    clear_all_tasks()

    # ==================== 测试 1: 创建第一个任务（无冲突）====================
    print_separator("📝 测试 1: 创建第一个任务（无冲突）")

    message1 = "明天早上9点开个早会，预计30分钟"
    print(f"\n💬 用户输入: {message1}")

    result1 = send_chat_message(message1)

    if result1:
        print(f"\n✅ 系统回复:\n{result1.get('reply', '无回复')}")

        if result1.get("success"):
            task1 = result1.get("task", {})
            print(f"\n📅 任务信息:")
            print(f"   标题: {task1.get('title')}")
            print(f"   时间: {task1.get('start_time', '')[:16]} - {task1.get('end_time', '')[:16]}")
            print(f"   ✅ 测试通过: 任务创建成功")
        else:
            print(f"\n❌ 测试失败: 任务创建失败")
            return False
    else:
        print(f"\n❌ 测试失败: 无法连接服务器")
        return False

    # ==================== 测试 2: 创建冲突任务 ====================
    print_separator("📝 测试 2: 创建与任务1冲突的任务")

    message2 = "明天早上9点15分产品评审，需要1小时"
    print(f"\n💬 用户输入: {message2}")

    result2 = send_chat_message(message2)

    if result2:
        print(f"\n✅ 系统回复:\n{result2.get('reply', '无回复')}")

        # 检查是否检测到冲突
        if result2.get("has_conflict"):
            print(f"\n✅ 测试通过: 成功检测到冲突！")
            conflicts = result2.get("conflicts", [])
            print(f"   冲突数量: {len(conflicts)}")
            for i, conflict in enumerate(conflicts, 1):
                print(f"   冲突{i}: {conflict.get('message', '未知冲突')}")
        elif not result2.get("success"):
            print(f"\n⚠️ 部分通过: 任务未创建，但未返回冲突标志")
        else:
            print(f"\n❌ 测试失败: 未检测到冲突，任务被直接创建")
            task2 = result2.get("task", {})
            print(f"   任务2时间: {task2.get('start_time', '')[:16]} - {task2.get('end_time', '')[:16]}")
            return False
    else:
        print(f"\n❌ 测试失败: 无法连接服务器")
        return False

    # ==================== 测试 3: 选择"调整"自动排程 ====================
    print_separator("📝 测试 3: 选择自动调整时间")

    message3 = "调整"
    print(f"\n💬 用户输入: {message3}")

    result3 = send_chat_message(message3)

    if result3:
        print(f"\n✅ 系统回复:\n{result3.get('reply', '无回复')}")

        if result3.get("success") and result3.get("task"):
            task3 = result3.get("task", {})
            print(f"\n✅ 测试通过: 自动调整成功！")
            print(f"   新任务时间: {task3.get('start_time', '')[:16]} - {task3.get('end_time', '')[:16]}")

            # 验证新时间是否与任务1冲突
            task1_start = datetime.fromisoformat(task1.get("start_time", "").replace("Z", "+00:00"))
            task1_end = datetime.fromisoformat(task1.get("end_time", "").replace("Z", "+00:00"))
            task3_start = datetime.fromisoformat(task3.get("start_time", "").replace("Z", "+00:00"))
            task3_end = datetime.fromisoformat(task3.get("end_time", "").replace("Z", "+00:00"))

            if task3_start >= task1_end or task3_end <= task1_start:
                print(f"   ✅ 验证通过: 新时间与任务1无重叠")
            else:
                print(f"   ❌ 验证失败: 新时间仍与任务1冲突！")
                return False
        else:
            print(f"\n❌ 测试失败: 自动调整失败")
            return False
    else:
        print(f"\n❌ 测试失败: 无法连接服务器")
        return False

    # ==================== 测试 4: 查询所有任务验证 ====================
    print_separator("📝 测试 4: 验证最终任务列表")

    all_tasks = get_all_tasks()

    if all_tasks and all_tasks.get("tasks"):
        tasks = all_tasks["tasks"]
        print(f"\n📊 当前共有 {len(tasks)} 个任务:\n")

        for i, task in enumerate(tasks, 1):
            start = task.get("start_time", "")[:16] if task.get("start_time") else "未安排"
            end = task.get("end_time", "")[:16] if task.get("end_time") else "未安排"
            status = task.get("status", "unknown")
            print(f"   {i}. {task.get('title')} | {start} - {end} | 状态: {status}")

        # 检查是否有时间重叠
        has_overlap = False
        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                t1 = tasks[i]
                t2 = tasks[j]

                if t1.get("start_time") and t2.get("start_time"):
                    t1_start = datetime.fromisoformat(t1["start_time"].replace("Z", "+00:00"))
                    t1_end = datetime.fromisoformat(t1["end_time"].replace("Z", "+00:00"))
                    t2_start = datetime.fromisoformat(t2["start_time"].replace("Z", "+00:00"))
                    t2_end = datetime.fromisoformat(t2["end_time"].replace("Z", "+00:00"))

                    # 检查时间重叠
                    if t1_start < t2_end and t2_start < t1_end:
                        print(f"\n❌ 发现冲突: 「{t1['title']}」与「{t2['title']}」时间重叠！")
                        has_overlap = True

        if not has_overlap:
            print(f"\n✅ 测试通过: 所有任务时间无冲突")
        else:
            print(f"\n❌ 测试失败: 存在时间冲突的任务")
            return False
    else:
        print(f"\n❌ 测试失败: 无法获取任务列表")
        return False

    # ==================== 总结 ====================
    print_separator("🎉 测试完成")
    print("\n✅ 所有测试通过！冲突检测功能正常工作。")
    print("\n测试覆盖:")
    print("  ✓ 无冲突任务创建")
    print("  ✓ 冲突检测与提示")
    print("  ✓ 自动调整时间")
    print("  ✓ 最终任务验证")

    return True


if __name__ == "__main__":
    try:
        success = test_conflict_detection()

        if success:
            print("\n" + "=" * 70)
            print("  🎊 恭喜！所有测试用例通过！")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print("  ⚠️ 部分测试失败，请检查上述输出")
            print("=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
