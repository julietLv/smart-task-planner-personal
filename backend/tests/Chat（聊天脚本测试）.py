"""测试完整的聊天处理流程"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from app.services.llm_service import parse_user_intent
from app.models.task_model import get_all_tasks, get_user_preferences
from app.services.scheduler_service import detect_conflict


def test_full_chat_flow():
    print("\n" + "=" * 70)
    print("🧪 测试完整聊天处理流程")
    print("=" * 70)

    message = "明天下午2-3点要开会"
    user_id = 1

    print(f"\n📝 测试消息: {message}")
    print(f"👤 用户ID: {user_id}")

    try:
        # 步骤1: 意图识别
        print("\n1️⃣ 步骤1: 意图识别")
        intent_result = parse_user_intent(message)
        intent = intent_result['intent']
        entities = intent_result['entities']
        print(f"   ✅ 意图: {intent}")
        print(f"   ✅ 实体: {entities}")

        # 步骤2: 获取任务
        print("\n2️⃣ 步骤2: 获取用户任务")
        tasks = get_all_tasks(user_id)
        print(f"   ✅ 获取到 {len(tasks)} 个任务")

        # 步骤3: 获取用户偏好
        print("\n3️⃣ 步骤3: 获取用户偏好")
        preferences = get_user_preferences(user_id)
        if preferences:
            print(f"   ✅ 偏好设置: {preferences.to_dict()}")
        else:
            print(f"   ⚠️ 偏好设置为空")

        # 步骤4: 检测冲突
        print("\n4️⃣ 步骤4: 检测时间冲突")
        if entities.get("start_time") and entities.get("end_time"):
            print(f"   开始时间: {entities['start_time']}")
            print(f"   结束时间: {entities['end_time']}")

            task_dicts = [t.to_dict() for t in tasks]
            print(f"   已有任务数: {len(task_dicts)}")

            prefs_dict = preferences.to_dict() if preferences else {}

            conflict_result = detect_conflict(
                {"start_time": entities["start_time"], "end_time": entities["end_time"]},
                task_dicts,
                prefs_dict
            )

            print(f"   ✅ 冲突检测结果:")
            print(f"      有冲突: {conflict_result['has_conflict']}")
            print(f"      冲突数: {len(conflict_result['conflicts'])}")
            if conflict_result['conflicts']:
                for c in conflict_result['conflicts']:
                    print(f"      - {c.get('type')}: {c.get('message')}")
        else:
            print(f"   ⏭️ 跳过（未提供具体时间）")

        # 步骤5: 生成回复
        print("\n5️⃣ 步骤5: 生成回复")
        reply = f"好的，我为您识别到一个任务：\n\n"
        reply += f"📋 **{entities.get('title', '未命名任务')}**\n"

        from datetime import datetime
        if entities.get("start_time") and entities.get("end_time"):
            start_t = datetime.fromisoformat(entities["start_time"]).strftime("%m-%d %H:%M")
            end_t = datetime.fromisoformat(entities["end_time"]).strftime("%H:%M")
            reply += f"🕐 时间：{start_t} - {end_t}\n"

        print(f"   ✅ 回复内容:")
        for line in reply.split('\n'):
            print(f"      {line}")

        print("\n" + "=" * 70)
        print("✅ 完整流程测试通过!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败!")
        print(f"   错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_full_chat_flow()
