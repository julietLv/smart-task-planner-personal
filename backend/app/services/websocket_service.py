"""WebSocket 推送服务 - 实时通知"""
from typing import List, Dict, Any, Optional
import json
import time
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime


class ConnectionManager:
    """WebSocket 连接管理器 - 支持用户ID映射"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        # ✅ 新增：用户ID到WebSocket连接的映射
        self.user_connections: Dict[int, List[WebSocket]] = {}
        # ✅ 新增：连接时间戳，用于防抖
        self.connection_timestamps: Dict[int, float] = {}
        # ✅ 防抖间隔：5秒内不允许同一用户重复连接
        self.debounce_interval = 5.0

    async def connect(self, websocket: WebSocket, user_id: int):
        # ✅ 防抖检查：如果用户在短时间内重复连接，拒绝新连接
        current_time = time.time()
        if user_id in self.connection_timestamps:
            time_since_last_connection = current_time - self.connection_timestamps[user_id]
            if time_since_last_connection < self.debounce_interval:
                print(f"⚠️ 用户 {user_id} 连接过于频繁（{time_since_last_connection:.1f}秒），拒绝新连接")
                await websocket.close(code=1008, reason="Connection too frequent, please wait")
                return
        
        # ✅ 如果该用户已有连接，先关闭旧连接
        if user_id in self.user_connections and len(self.user_connections[user_id]) > 0:
            print(f"⚠️ 用户 {user_id} 已有活跃连接，关闭旧连接并建立新连接")
            
            # 关闭所有旧连接
            for old_ws in self.user_connections[user_id]:
                try:
                    await old_ws.close(code=1001, reason="New connection established")
                except:
                    pass
                
                if old_ws in self.active_connections:
                    self.active_connections.remove(old_ws)
            
            # 清空旧连接列表
            self.user_connections[user_id] = []
        
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # ✅ 注册新连接
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        
        # ✅ 记录连接时间戳
        self.connection_timestamps[user_id] = current_time
        
        print(f"✅ WebSocket 连接已建立 (user_id={user_id}), 当前连接数: {len(self.active_connections)}")

        # ✅ 检查是否有待推送的报告（如周报在断开期间生成）
        await self._send_pending_report(websocket, user_id)

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # ✅ 清理用户连接映射
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # ✅ 清理时间戳
                if user_id in self.connection_timestamps:
                    del self.connection_timestamps[user_id]
        
        print(f"❌ WebSocket 连接已断开, 当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: Dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"⚠️ 发送消息失败: {str(e)}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

    # ✅ 新增：向指定用户推送消息
    async def send_to_user(self, user_id: int, message: Dict):
        """向特定用户的所有连接推送消息"""
        if user_id not in self.user_connections:
            print(f"⚠️ 用户 {user_id} 无活跃连接")
            return False
        
        disconnected = []
        success_count = 0
        
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
                success_count += 1
            except Exception as e:
                print(f"⚠️ 发送消息给用户 {user_id} 失败: {str(e)}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn, user_id)
        
        if success_count > 0:
            print(f"📤 已向用户 {user_id} 推送消息 ({success_count} 个连接)")
            return True
        return False

    def get_active_connections_count(self) -> int:
        return len(self.active_connections)

    def get_user_connection_count(self, user_id: int) -> int:
        """获取指定用户的连接数"""
        return len(self.user_connections.get(user_id, []))

    async def _send_pending_report(self, websocket: WebSocket, user_id: int):
        """检查 Redis 中是否有待推送的报告，有则发送给新连接"""
        try:
            from app.services.cache_service import redis_cache
            if not redis_cache.enabled:
                return
            
            pending_key = f"pending_report:{user_id}"
            pending_data = redis_cache.get(pending_key)
            if pending_data:
                print(f"📤 发现待推送的报告，正在推送给用户 {user_id} 的新连接")
                await websocket.send_json(pending_data)
                redis_cache.delete(pending_key)
                print(f"✅ 待推送报告已成功发送并清理")
        except Exception as e:
            print(f"⚠️ 检查待推送报告时出错: {e}")


# 全局 WebSocket 管理器
manager = ConnectionManager()


async def push_daily_summary(summary: Dict, user_id: int = 1):
    """
    推送每日日程摘要
    """
    message = {
        "type": "daily_summary",
        "data": summary,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }

    from app.models.notification_model import save_notification
    
    from app.models.database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # ✅ 修复：使用摘要中的实际日期进行去重，而不是推送时间
        summary_date = summary.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # ✅ 修复：查询是否已经为该日期保存过摘要
        cursor.execute("""
            SELECT id FROM notifications 
            WHERE user_id = %s 
            AND type = 'daily_summary'
            AND title LIKE %s
            LIMIT 1
        """, (user_id, f"%{summary_date}%"))
        
        existing = cursor.fetchone()
        
        # 只有该日期的摘要不存在时才保存
        if not existing:
            save_notification(
                user_id=user_id,
                notif_type="daily_summary",
                title=f"📅 {summary_date}日程摘要",
                message=summary.get('summary', ''),
                notification_type="info"
            )
            print(f"✅ 已保存 {summary_date} 的日程摘要")
        else:
            print(f"⚠️ {summary_date} 的摘要已存在，跳过重复保存 (ID: {existing[0] if isinstance(existing, tuple) else existing['id']})")
    except Exception as e:
        print(f"❌ 检查摘要重复时出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

    print(f" 推送每日摘要给用户 {user_id}: {summary.get('date', 'unknown')}")
    await manager.send_to_user(user_id, message)


async def push_notification(notification: Dict, user_id: int = 1):
    """
    推送通用通知
    """
    message = {
        "type": "notification",
        "data": notification,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }

    # ✅ 保存到数据库
    from app.models.notification_model import save_notification
    save_notification(
        user_id=user_id,
        notif_type="general",
        title=notification.get("title", "系统通知"),
        message=notification.get("message", ""),
        notification_type="info"
    )

    await manager.send_to_user(user_id, message)


async def push_deadline_reminder(reminder: Dict, user_id: int = 1):
    """
    推送截止时间提醒（紧急通知）
    """
    message = {
        "type": "deadline_reminder",
        "data": reminder,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }

    # ✅ 保存到数据库
    from app.models.notification_model import save_notification
    save_notification(
        user_id=user_id,
        notif_type="deadline_reminder",
        title=reminder.get("title", ""),
        message=reminder.get("message", ""),
        notification_type=reminder.get("notification_type", "info"),
        task_id=reminder.get("task_id")
    )

    print(f"🔔 推送截止提醒给用户 {user_id}: {reminder.get('title', '未知任务')}")
    await manager.send_to_user(user_id, message)


# ✅ 新增：推送冲突通知
async def push_conflict_notification(conflict: Dict, user_id: int = 1):
    """
    推送任务冲突通知
    """
    message = {
        "type": "conflict_notification",
        "data": conflict,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }
    
    # ✅ 保存到数据库
    from app.models.notification_model import save_notification
    save_notification(
        user_id=user_id,
        notif_type="conflict_notification",
        title="检测到任务冲突",
        message=conflict.get("message", f"发现{conflict.get('conflict_count', 0)}个时间冲突"),
        notification_type="warning"
    )
    
    print(f"⚠️ 推送冲突通知给用户 {user_id}")
    await manager.send_to_user(user_id, message)


# ✅ 新增：推送日程变更通知
async def push_schedule_change(change: Dict, user_id: int = 1):
    """
    推送日程变更通知
    """
    message = {
        "type": "schedule_change",
        "data": change,
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id
    }
    
    # ✅ 保存到数据库
    from app.models.notification_model import save_notification
    save_notification(
        user_id=user_id,
        notif_type="schedule_change",
        title="日程变更",
        message=change.get("message", "您的日程安排已更新"),
        notification_type="info"
    )
    
    print(f"📋 推送日程变更给用户 {user_id}")
    await manager.send_to_user(user_id, message)
