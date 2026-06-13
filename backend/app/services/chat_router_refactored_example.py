# backend/app/routers/chat_router_refactored_example.py
from app.services.task_queue import task_queue


@router.post("/send")
async def send_message(request: ChatRequest):
    # ... 前面的意图识别逻辑不变

    if action_name == "generate_report":
        # 异步提交任务
        task_id = task_queue.enqueue("generate_report", {
            "user_id": user_id,
            "time_range": params.get('time_range', 'this_week')
        })

        return {
            "reply": f"{user_nickname}，周报生成任务已提交（任务ID: {task_id}）\n"
                     f"生成完成后会通过 WebSocket 推送给你～",
            "intent": "generate_report",
            "success": True,
            "task_id": task_id
        }
