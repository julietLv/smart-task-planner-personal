"""通知数据模型 - 使用原生SQL"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def save_notification(user_id: int, notif_type: str, title: str, 
                     message: str, notification_type: str = "info",
                     task_id: int = None):
    """保存通知到数据库"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO notifications (user_id, type, title, message, notification_type, task_id, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, NOW())
        """, (user_id, notif_type, title, message, notification_type, task_id))
        
        conn.commit()
        notification_id = cursor.lastrowid
        
        print(f"💾 通知已保存: [{notif_type}] {title} (ID: {notification_id})")
        return {"id": notification_id}
    except Exception as e:
        conn.rollback()
        print(f"❌ 保存通知失败: {e}")
        return None
    finally:
        conn.close()


def get_user_notifications(user_id: int, limit: int = 100, unread_only: bool = False) -> List[Dict]:
    """获取用户通知列表（仅返回最近7天的通知）"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if unread_only:
            cursor.execute("""
                SELECT id, user_id, type, title, message, notification_type, task_id, 
                       is_read, created_at, read_at
                FROM notifications 
                WHERE user_id = %s 
                AND is_read = FALSE
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT id, user_id, type, title, message, notification_type, task_id, 
                       is_read, created_at, read_at
                FROM notifications 
                WHERE user_id = %s
                AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                ORDER BY created_at DESC
                LIMIT %s
            """, (user_id, limit))
        
        columns = [desc[0] for desc in cursor.description]
        notifications = []
        
        for row in cursor.fetchall():
            if isinstance(row, dict):
                notif = row
            else:
                notif = {}
                for i, col in enumerate(columns):
                    notif[col] = row[i]
            
            if notif.get('created_at'):
                notif['created_at'] = notif['created_at'].isoformat() if hasattr(notif['created_at'], 'isoformat') else str(notif['created_at'])
            if notif.get('read_at'):
                notif['read_at'] = notif['read_at'].isoformat() if hasattr(notif['read_at'], 'isoformat') else str(notif['read_at'])
            
            if 'is_read' in notif:
                notif['is_read'] = bool(notif['is_read'])
            
            notifications.append(notif)
        
        print(f"✅ 查询到 {len(notifications)} 条通知（最近7天）")
        if notifications:
            print(f"📋 示例通知: {notifications[0]}")
        
        return notifications
    except Exception as e:
        print(f"❌ 获取通知列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()


def mark_notification_as_read(notification_id: int, user_id: int) -> bool:
    """标记单个通知为已读"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE notifications 
            SET is_read = TRUE, read_at = NOW()
            WHERE id = %s AND user_id = %s
        """, (notification_id, user_id))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ 通知 {notification_id} 已标记为已读")
            return True
        else:
            print(f"⚠️ 通知 {notification_id} 不存在或不属于用户 {user_id}")
            return False
    except Exception as e:
        conn.rollback()
        print(f"❌ 标记通知失败: {e}")
        return False
    finally:
        conn.close()


def mark_all_notifications_as_read(user_id: int) -> int:
    """标记所有通知为已读"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE notifications 
            SET is_read = TRUE, read_at = NOW()
            WHERE user_id = %s AND is_read = FALSE
        """, (user_id,))
        
        conn.commit()
        count = cursor.rowcount
        
        print(f"✅ 用户 {user_id} 的 {count} 条通知已标记为已读")
        return count
    except Exception as e:
        conn.rollback()
        print(f" 批量标记失败: {e}")
        return 0
    finally:
        conn.close()


def delete_notification(notification_id: int, user_id: int) -> bool:
    """删除单个通知"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM notifications 
            WHERE id = %s AND user_id = %s
        """, (notification_id, user_id))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ 通知 {notification_id} 已删除")
            return True
        else:
            print(f"⚠️ 通知 {notification_id} 不存在或不属于用户 {user_id}")
            return False
    except Exception as e:
        conn.rollback()
        print(f"❌ 删除通知失败: {e}")
        return False
    finally:
        conn.close()


def clear_user_notifications(user_id: int) -> int:
    """清空用户的所有通知（7天内的）"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM notifications 
            WHERE user_id = %s
            AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (user_id,))
        
        conn.commit()
        count = cursor.rowcount
        
        print(f"✅ 用户 {user_id} 的 {count} 条通知已清空")
        return count
    except Exception as e:
        conn.rollback()
        print(f"❌ 清空通知失败: {e}")
        return 0
    finally:
        conn.close()


def delete_old_notifications(days: int = 30) -> int:
    """清理过期通知（保留最近N天）"""
    from app.models.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM notifications 
            WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        
        conn.commit()
        count = cursor.rowcount
        
        print(f"🗑️ 已清理 {count} 条过期通知（>{days}天）")
        return count
    except Exception as e:
        conn.rollback()
        print(f"❌ 清理失败: {e}")
        return 0
    finally:
        conn.close()
