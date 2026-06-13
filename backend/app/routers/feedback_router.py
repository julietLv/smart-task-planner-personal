"""用户反馈路由 - 收集用户对推荐方案的反馈"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.database import get_connection, DATABASE_TYPE

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    task_id: Optional[int] = None
    action: str  # "accepted" | "rejected" | "modified" | "ignored"
    feedback_type: str  # "schedule_recommendation" | "conflict_resolution" | "priority_suggestion"
    original_data: Optional[Dict[str, Any]] = None
    modified_data: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    confidence_score: Optional[float] = None
    user_id: Optional[int] = 1


class FeedbackStatsRequest(BaseModel):
    """反馈统计请求"""
    user_id: Optional[int] = 1
    days: Optional[int] = 30


def _get_placeholder():
    """根据数据库类型返回占位符"""
    return "%s" if DATABASE_TYPE == "mysql" else "?"


@router.post("/")
def submit_feedback(request: FeedbackRequest):
    """
    提交用户反馈

    Args:
        request: 反馈数据

    Returns:
        提交结果
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = _get_placeholder()

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 初始化反馈表（如果不存在）
        _init_feedback_table(conn)

        # 插入反馈记录
        placeholders = ", ".join([placeholder] * 10)
        cursor.execute(f"""
            INSERT INTO user_feedback 
            (user_id, task_id, action, feedback_type, original_data, 
             modified_data, reason, confidence_score, created_at, updated_at)
            VALUES ({placeholders})
        """, (
            request.user_id,
            request.task_id,
            request.action,
            request.feedback_type,
            str(request.original_data) if request.original_data else None,
            str(request.modified_data) if request.modified_data else None,
            request.reason,
            request.confidence_score,
            now,
            now
        ))

        conn.commit()
        feedback_id = cursor.lastrowid if DATABASE_TYPE == "mysql" else cursor.lastrowid

        conn.close()

        print(f"✅ 收到用户反馈: {request.action} ({request.feedback_type})")

        # 如果是修改操作，记录到学习习惯
        if request.action == "modified" and request.modified_data:
            _learn_from_modification(request)

        return {
            "success": True,
            "feedback_id": feedback_id,
            "message": "感谢您的反馈！这将帮助我们更好地为您服务"
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"提交反馈失败: {str(e)}")


@router.get("/stats")
def get_feedback_stats(user_id: int = 1, days: int = 30):
    """
    获取用户反馈统计信息

    Args:
        user_id: 用户ID
        days: 统计天数

    Returns:
        反馈统计数据
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = _get_placeholder()

        # 初始化反馈表（如果不存在）
        _init_feedback_table(conn)

        # 计算起始日期
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

        # 总反馈数
        cursor.execute(f"""
            SELECT COUNT(*) as total FROM user_feedback 
            WHERE user_id = {placeholder} AND created_at >= {placeholder}
        """, (user_id, start_date))
        total = cursor.fetchone()["total"] if DATABASE_TYPE == "mysql" else cursor.fetchone()["total"]

        # 按动作类型统计
        cursor.execute(f"""
            SELECT action, COUNT(*) as count 
            FROM user_feedback 
            WHERE user_id = {placeholder} AND created_at >= {placeholder}
            GROUP BY action
        """, (user_id, start_date))
        action_stats = cursor.fetchall()

        # 按反馈类型统计
        cursor.execute(f"""
            SELECT feedback_type, COUNT(*) as count 
            FROM user_feedback 
            WHERE user_id = {placeholder} AND created_at >= {placeholder}
            GROUP BY feedback_type
        """, (user_id, start_date))
        type_stats = cursor.fetchall()

        # 接受率
        cursor.execute(f"""
            SELECT COUNT(*) as accepted 
            FROM user_feedback 
            WHERE user_id = {placeholder} AND action = 'accepted' AND created_at >= {placeholder}
        """, (user_id, start_date))
        accepted = cursor.fetchone()["accepted"] if DATABASE_TYPE == "mysql" else cursor.fetchone()["accepted"]

        acceptance_rate = (accepted / total * 100) if total > 0 else 0

        conn.close()

        return {
            "success": True,
            "period_days": days,
            "total_feedback": total,
            "acceptance_rate": round(acceptance_rate, 2),
            "by_action": {row["action"]: row["count"] for row in action_stats},
            "by_type": {row["feedback_type"]: row["count"] for row in type_stats}
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/history")
def get_feedback_history(user_id: int = 1, limit: int = 50):
    """
    获取用户反馈历史

    Args:
        user_id: 用户ID
        limit: 返回条数限制

    Returns:
        反馈历史记录
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        placeholder = _get_placeholder()

        # 初始化反馈表（如果不存在）
        _init_feedback_table(conn)

        cursor.execute(f"""
            SELECT * FROM user_feedback 
            WHERE user_id = {placeholder}
            ORDER BY created_at DESC
            LIMIT {placeholder}
        """, (user_id, limit))

        rows = cursor.fetchall()

        history = []
        for row in rows:
            history.append({
                "id": row["id"],
                "task_id": row["task_id"],
                "action": row["action"],
                "feedback_type": row["feedback_type"],
                "reason": row["reason"],
                "confidence_score": row["confidence_score"],
                "created_at": row["created_at"]
            })

        conn.close()

        return {
            "success": True,
            "count": len(history),
            "history": history
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


def _init_feedback_table(conn):
    """初始化反馈表"""
    cursor = conn.cursor()

    if DATABASE_TYPE == "mysql":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                task_id INT,
                action VARCHAR(20) NOT NULL,
                feedback_type VARCHAR(50) NOT NULL,
                original_data TEXT,
                modified_data TEXT,
                reason TEXT,
                confidence_score FLOAT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                INDEX idx_user_created (user_id, created_at DESC),
                INDEX idx_action (action)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                task_id INTEGER,
                action TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                original_data TEXT,
                modified_data TEXT,
                reason TEXT,
                confidence_score REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_created ON user_feedback(user_id, created_at DESC)")

    conn.commit()


def _learn_from_modification(request: FeedbackRequest):
    """从用户的修改行为中学习偏好"""
    try:
        from app.services.scheduler_service import remember_user_preference

        if not request.task_id or not request.modified_data:
            return

        # 获取原始任务信息
        from app.models.task_model import get_task_by_id
        task = get_task_by_id(request.task_id, request.user_id)

        if not task:
            return

        # 检测优先级调整
        if "priority" in request.modified_data and request.modified_data["priority"] != task.priority:
            remember_user_preference(
                task_title=task.title,
                adjustment_type="priority",
                old_value=task.priority,
                new_value=request.modified_data["priority"],
                user_id=request.user_id,
                context={"source": "user_feedback"}
            )

        # 检测时长调整
        if "duration" in request.modified_data and request.modified_data.get("duration") != task.duration:
            remember_user_preference(
                task_title=task.title,
                adjustment_type="duration",
                old_value=task.duration,
                new_value=request.modified_data["duration"],
                user_id=request.user_id,
                context={"source": "user_feedback"}
            )

        # 检测时间调整（可以学习用户的时段偏好）
        if "start_time" in request.modified_data:
            # 提取小时信息
            from datetime import datetime
            try:
                new_start = datetime.fromisoformat(request.modified_data["start_time"])
                hour = new_start.hour

                if hour < 12:
                    time_period = "morning"
                elif hour < 18:
                    time_period = "afternoon"
                else:
                    time_period = "evening"

                remember_user_preference(
                    task_title=task.title,
                    adjustment_type="time_period",
                    old_value=None,
                    new_value=time_period,
                    user_id=request.user_id,
                    context={"source": "user_feedback", "hour": hour}
                )
            except:
                pass

    except Exception as e:
        print(f"⚠️ 从反馈中学习失败: {e}")
