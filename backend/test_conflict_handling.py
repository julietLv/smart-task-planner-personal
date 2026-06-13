#!/usr/bin/env python3
"""
冲突处理功能测试脚本（仅依赖 /api/chat/send）
前提：后端服务已启动，数据库中无冲突任务（可手动清理）
"""

import requests
import time

BASE_URL = "http://localhost:8080"
CHAT_ENDPOINT = f"{BASE_URL}/api/chat/send"
USER_ID = 1

def send_message(message: str, user_id: int = USER_ID) -> dict:
    """发送聊天消息并返回响应"""
    resp = requests.post(CHAT_ENDPOINT, json={"message": message, "user_id": user_id})
    resp.raise_for_status()
    return resp.json()

def print_result(stage: str, response: dict):
    print(f"\n{'='*60}\n📌 {stage}\n{'='*60}")
    print(f"回复: {response.get('reply', '')[:300]}")
    print(f"意图: {response.get('intent')}")
    print(f"成功: {response.get('success')}")
    if "has_conflict" in response:
        print(f"冲突标志: {response['has_conflict']}")
    print(f"{'='*60}\n")

def test_conflict_handling():
    """完整测试流程"""
    print("🚀 开始测试冲突处理功能")
    print("⚠️ 请确保数据库中没有与其他任务冲突的时间段任务")
    input("按 Enter 继续...")

    # 1. 创建一个基础任务（14:00-15:00）作为冲突源
    print("\n📝 步骤1: 创建一个任务（14:00-15:00）")
    resp1 = send_message("添加任务：下午2点到3点 基础会议")
    print_result("创建基础任务", resp1)
    if not resp1.get("success"):
        print("❌ 基础任务创建失败，测试终止")
        return

    # 2. 尝试创建冲突任务（14:30-15:30，重叠）
    print("\n📝 步骤2: 创建冲突任务（14:30-15:30 代码审查）")
    resp2 = send_message("添加任务：下午2点半到3点半 代码审查")
    print_result("冲突检测", resp2)

    # 检查是否返回冲突标志
    if resp2.get("has_conflict") is not True:
        print("❌ 未检测到冲突！请检查 detect_conflict 逻辑")
        return
    assert "请选择" in resp2.get("reply", ""), "回复应包含冲突解决选项"

    # 3. 发送「调整」指令
    print("\n📝 步骤3: 发送「调整」指令")
    resp3 = send_message("调整")
    print_result("自动调整", resp3)
    assert resp3.get("success") is True, "自动调整应成功"
    assert "已为您自动调整时间" in resp3.get("reply", ""), "回复应包含调整成功"

    # 4. 再次创建冲突任务（需要先清空之前自动调整产生的任务？这一步简化：手动清理或重新运行整个测试；这里只演示前半部分）
    print("\n⚠️ 为测试「忽略」指令，请手动删除上一步自动创建的任务（或重新运行整个脚本）")
    input("按 Enter 继续测试「忽略」分支...")

    # 重新创建基础冲突任务（假设已手动清理，重新创建）
    print("\n📝 步骤4: 重新创建冲突场景")
    send_message("添加任务：下午2点到3点 基础会议")  # 可能冲突，如果未删除会报冲突？简化处理
    resp4 = send_message("添加任务：下午2点半到3点半 强制任务")
    print_result("冲突检测", resp4)

    print("\n📝 步骤5: 发送「忽略」指令")
    resp5 = send_message("忽略")
    print_result("强制忽略", resp5)
    assert "强制添加" in resp5.get("reply", ""), "回复应包含强制添加提示"

    # 5. 测试取消
    print("\n⚠️ 再次重新创建冲突场景（测试取消）")
    input("按 Enter 继续...")
    send_message("添加任务：下午2点到3点 基础会议")
    send_message("添加任务：下午2点半到3点半 取消任务")
    print("\n📝 步骤6: 发送「取消」指令")
    resp6 = send_message("取消")
    print_result("取消任务", resp6)
    assert "已取消" in resp6.get("reply", ""), "应提示取消"

    print("\n✅ 所有测试完成！")

def test_context_persistence():
    """测试 Redis 上下文恢复（需手动重启服务）"""
    print("\n🧪 测试 Redis 上下文持久性")
    print("步骤：")
    print("1. 运行此脚本前，先手动创建一个冲突任务（如发送「添加任务：下午2点半到3点半 测试」）")
    print("2. 看到冲突提示后，重启 FastAPI 服务（这会导致内存缓存清空）")
    print("3. 再次发送任意消息（如「你好」），观察回复是否仍提示冲突。")
    input("按 Enter 开始验证...")
    resp = send_message("你好")
    print_result("重启后发送任意消息", resp)
    if "请选择" in resp.get("reply", ""):
        print("✅ 成功从 Redis 恢复冲突上下文")
    else:
        print("❌ 冲突上下文丢失，请检查 get_task_creation_context 中从 Redis 加载后是否补全 has_conflict 字段")

if __name__ == "__main__":
    mode = input("选择测试模式: 1-完整自动测试（会创建/删除任务） 2-仅测试上下文持久性（需手动重启服务）: ")
    if mode == "1":
        test_conflict_handling()
    elif mode == "2":
        test_context_persistence()
    else:
        print("无效选择")