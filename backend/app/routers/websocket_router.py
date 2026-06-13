"""WebSocket 路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_service import manager, push_daily_summary
from app.services.notification_service import generate_daily_summary, check_deadline_reminders
import asyncio

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket 端点 - 实时推送通知

    使用方式（前端）：
    const ws = new WebSocket('ws://localhost:8080/ws/1')

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'daily_summary') {
            // 处理每日摘要
            showDailySummary(data.data)
        } else if (data.type === 'deadline_reminder') {
            // 处理截止提醒
            showReminder(data.data)
        } else if (data.type === 'notification') {
            // 处理通用通知
            showNotification(data.data)
        } else if (data.type === 'conflict_notification') {
            // 处理冲突通知
            showConflict(data.data)
        }
    }
    """
    await manager.connect(websocket, user_id)
    
    # ✅ 检查连接是否被防抖拒绝（正确判断client_state）
    if websocket.client_state.name != "CONNECTED":
        return

    try:
        # 连接成功后，立即发送欢迎消息
        await _safe_send(websocket, {
            "type": "welcome",
            "data": {
                "message": "欢迎连接到智能任务规划系统",
                "user_id": user_id,
                "available_types": [
                    "daily_summary",
                    "deadline_reminder",
                    "notification",
                    "conflict_notification",
                    "schedule_change"
                ]
            },
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })

        # 立即推送当日摘要
        daily_summary = generate_daily_summary(user_id)
        if daily_summary.get('success'):
            await push_daily_summary(daily_summary, user_id)

        # ✅ 心跳检测：30秒无消息则主动发送心跳
        last_message_time = __import__('time').time()
        heartbeat_interval = 30  # 30秒
        
        # 保持连接活跃，监听客户端消息
        while True:
            try:
                # ✅ 使用 asyncio.wait_for 设置超时
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=heartbeat_interval
                )
                last_message_time = __import__('time').time()

                try:
                    client_message = __import__('json').loads(data)

                    # 处理客户端请求
                    if client_message.get("type") == "heartbeat":
                        await _safe_send(websocket, {
                            "type": "heartbeat_ack",
                            "timestamp": __import__('datetime').datetime.now().isoformat()
                        })
                    elif client_message.get("type") == "request_summary":
                        daily_summary = generate_daily_summary(user_id)
                        await _safe_send(websocket, {
                            "type": "daily_summary",
                            "data": daily_summary,
                            "timestamp": __import__('datetime').datetime.now().isoformat()
                        })
                except __import__('json').JSONDecodeError:
                    pass
            
            except asyncio.TimeoutError:
                # ✅ 超时后主动发送心跳包
                current_time = __import__('time').time()
                if current_time - last_message_time >= heartbeat_interval:
                    await _safe_send(websocket, {
                        "type": "heartbeat",
                        "timestamp": __import__('datetime').datetime.now().isoformat()
                    })
                    last_message_time = current_time

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"❌ WebSocket 错误: {str(e)}")
        manager.disconnect(websocket, user_id)


async def _safe_send(websocket: WebSocket, data: dict):
    """安全发送消息，忽略连接已关闭的错误"""
    try:
        await websocket.send_json(data)
    except RuntimeError:
        pass  # 连接已关闭，忽略
