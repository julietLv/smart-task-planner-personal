from datetime import datetime, timedelta
from typing import List, Optional
from .database import get_connection, DATABASE_TYPE


class Task:
    """任务模型
    
    状态说明：
    - pending: 待完成（进行中）
    - done: 已完成（用户主动标记）
    - cancelled: 已取消
    - overdue: 超时未完成（系统自动标记）
    """
    
    def __init__(self, id: Optional[int] = None, user_id: int = 1, title: str = "",
                 description: Optional[str] = None, start_time: Optional[str] = None,
                 end_time: Optional[str] = None, deadline: Optional[str] = None,
                 duration: Optional[int] = None, priority: str = "medium",
                 status: str = "pending", created_at: Optional[str] = None,
                 updated_at: Optional[str] = None, user_text: Optional[str] = None):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.deadline = deadline
        self.duration = duration
        self.priority = priority
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.user_text = user_text  # ⭐ 智能排程时用户的原始输入，手动创建时为 None
    
    def to_dict(self) -> dict:
        """将任务对象转换为字典"""
        def format_datetime(dt):
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.isoformat()
            return dt
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "start_time": format_datetime(self.start_time),
            "end_time": format_datetime(self.end_time),
            "deadline": format_datetime(self.deadline),
            "duration": self.duration,
            "priority": self.priority,
            "status": self.status,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
            "user_text": self.user_text
        }
    
    @staticmethod
    def from_row(row) -> 'Task':
        """从数据库行创建任务对象"""
        def format_datetime(dt):
            if dt is None:
                return None
            if isinstance(dt, datetime):
                return dt.isoformat()
            return dt
        
        if DATABASE_TYPE == "mysql":
            return Task(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                description=row["description"],
                start_time=format_datetime(row["start_time"]),
                end_time=format_datetime(row["end_time"]),
                deadline=format_datetime(row["deadline"]),
                duration=row["duration"],
                priority=row["priority"],
                status=row["status"],
                created_at=format_datetime(row["created_at"]),
                updated_at=format_datetime(row["updated_at"]),
                user_text=row.get("user_text")
            )
        else:
            return Task(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                description=row["description"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                deadline=row["deadline"],
                duration=row["duration"],
                priority=row["priority"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                user_text=row["user_text"] if "user_text" in row.keys() else None
            )


class UserPreference:
    """用户偏好设置模型"""
    
    def __init__(self, user_id: int = 1, blocked_time_start: str = "22:00",
                 blocked_time_end: str = "08:00", default_priority: str = "medium",
                 remembered_habits: dict = None, assistant_nickname: str = "",
                 user_nickname: str = "", task_buffer_minutes: int = 15,
                 user_city: str = "北京", user_type: str = "worker",
                 workday_hours: float = 8.0, preferred_time_slot: str = "morning",
                 time_slot_offset: int = 0):
        self.user_id = user_id
        self.blocked_time_start = blocked_time_start
        self.blocked_time_end = blocked_time_end
        self.default_priority = default_priority
        self.remembered_habits = remembered_habits or {}
        self.assistant_nickname = assistant_nickname
        self.user_nickname = user_nickname
        self.task_buffer_minutes = task_buffer_minutes
        self.user_city = user_city
        self.user_type = user_type  # ⭐ Phase 3: 用户类型 (student/worker/elderly)
        self.workday_hours = workday_hours  # ⭐ Phase 3: 工作日时长
        self.preferred_time_slot = preferred_time_slot  # ⭐ Phase 3: 偏好时段
        self.time_slot_offset = time_slot_offset  # ⭐ Phase 3: 时间段偏移
    
    def to_dict(self) -> dict:
        """将用户偏好对象转换为字典"""
        import json
        return {
            "user_id": self.user_id,
            "blocked_time_start": self.blocked_time_start,
            "blocked_time_end": self.blocked_time_end,
            "default_priority": self.default_priority,
            "remembered_habits": self.remembered_habits if isinstance(self.remembered_habits, dict) else json.loads(self.remembered_habits) if isinstance(self.remembered_habits, str) else {},
            "assistant_nickname": self.assistant_nickname,
            "user_nickname": self.user_nickname,
            "task_buffer_minutes": self.task_buffer_minutes,
            "user_city": self.user_city,
            "user_type": self.user_type,  # ⭐ Phase 3: 用户类型
            "workday_hours": self.workday_hours,  # ⭐ Phase 3: 工作日时长
            "preferred_time_slot": self.preferred_time_slot,  # ⭐ Phase 3: 偏好时段
            "time_slot_offset": self.time_slot_offset  # ⭐ Phase 3: 时间段偏移
        }
    
    @staticmethod
    def from_row(row) -> 'UserPreference':
        """从数据库行创建用户偏好对象"""
        import json
        
        if DATABASE_TYPE == "mysql":
            remembered_habits = row.get("remembered_habits") or '{}'
            if isinstance(remembered_habits, str):
                try:
                    remembered_habits = json.loads(remembered_habits)
                except:
                    remembered_habits = {}
            
            assistant_nickname = row.get("assistant_nickname") or ""
            user_nickname = row.get("user_nickname") or ""
            task_buffer_minutes = row.get("task_buffer_minutes") or 15
            user_city = row.get("user_city") or "北京"
            user_type = row.get("user_type") or "worker"  # ⭐ Phase 3: 用户类型
            workday_hours = row.get("workday_hours") or 8.0  # ⭐ Phase 3: 工作日时长
            preferred_time_slot = row.get("preferred_time_slot") or "morning"  # ⭐ Phase 3: 偏好时段
            time_slot_offset = row.get("time_slot_offset") if row.get("time_slot_offset") is not None else 0  # ⭐ Phase 3: 时间段偏移
        else:
            remembered_habits = row["remembered_habits"] if "remembered_habits" in row.keys() else '{}'
            if isinstance(remembered_habits, str):
                try:
                    remembered_habits = json.loads(remembered_habits)
                except:
                    remembered_habits = {}
            
            assistant_nickname = row["assistant_nickname"] if "assistant_nickname" in row.keys() else ""
            if not assistant_nickname:
                assistant_nickname = ""
            
            user_nickname = row["user_nickname"] if "user_nickname" in row.keys() else ""
            if not user_nickname:
                user_nickname = ""
            
            task_buffer_minutes = row["task_buffer_minutes"] if "task_buffer_minutes" in row.keys() else 15
            user_city = row["user_city"] if "user_city" in row.keys() else "北京"
            user_type = row["user_type"] if "user_type" in row.keys() else "worker"  # ⭐ Phase 3: 用户类型
            workday_hours = row["workday_hours"] if "workday_hours" in row.keys() else 8.0  # ⭐ Phase 3: 工作日时长
            preferred_time_slot = row["preferred_time_slot"] if "preferred_time_slot" in row.keys() else "morning"  # ⭐ Phase 3: 偏好时段
            time_slot_offset = row["time_slot_offset"] if "time_slot_offset" in row.keys() else 0  # ⭐ Phase 3: 时间段偏移
        
        return UserPreference(
            user_id=row["user_id"],
            blocked_time_start=row["blocked_time_start"],
            blocked_time_end=row["blocked_time_end"],
            default_priority=row["default_priority"],
            remembered_habits=remembered_habits,
            assistant_nickname=assistant_nickname,
            user_nickname=user_nickname,
            task_buffer_minutes=task_buffer_minutes,
            user_city=user_city,
            user_type=user_type,  # ⭐ Phase 3: 用户类型
            workday_hours=workday_hours,  # ⭐ Phase 3: 工作日时长
            preferred_time_slot=preferred_time_slot,  # ⭐ Phase 3: 偏好时段
            time_slot_offset=time_slot_offset  # ⭐ Phase 3: 时间段偏移
        )


# ==================== 任务 CRUD 操作 ====================

def _get_placeholder():
    """根据数据库类型返回占位符"""
    return "%s" if DATABASE_TYPE == "mysql" else "?"


def create_task(title: str, user_id: int = 1, description: Optional[str] = None,
                start_time: Optional[str] = None, end_time: Optional[str] = None,
                deadline: Optional[str] = None, duration: Optional[int] = None,
                priority: str = "medium", status: str = "pending",
                user_text: Optional[str] = None) -> Task:
    """创建新任务
    
    Args:
        user_text: 智能排程时用户的原始输入，手动创建时为 None
    """
    conn = get_connection()
    cursor = conn.cursor()
    # ✅ 修复：使用 MySQL 兼容的 datetime 格式
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    placeholder = _get_placeholder()
    
    try:
        # ✅ 处理传入的时间参数，确保格式正确
        def format_datetime_for_mysql(dt_str):
            if dt_str is None:
                return None
            if isinstance(dt_str, str):
                # 将 ISO 格式转换为 MySQL 格式
                dt_str = dt_str.replace('T', ' ')
                if '.' in dt_str:
                    dt_str = dt_str.split('.')[0]
            return dt_str
        
        formatted_start = format_datetime_for_mysql(start_time)
        formatted_end = format_datetime_for_mysql(end_time)
        formatted_deadline = format_datetime_for_mysql(deadline)
        
        placeholders = ", ".join([placeholder] * 12)
        cursor.execute(f"""
            INSERT INTO tasks (user_id, title, description, start_time, end_time, 
                             deadline, duration, priority, status, created_at, updated_at, user_text)
            VALUES ({placeholders})
        """, (user_id, title, description, formatted_start, formatted_end, 
              formatted_deadline, duration, priority, status, now, now, user_text))
        
        conn.commit()
        task_id = cursor.lastrowid
        
        return get_task_by_id(task_id, user_id)
    finally:
        conn.close()


def get_task_by_id(task_id: int, user_id: int = 1) -> Optional[Task]:
    """根据ID获取单个任务"""
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        cursor.execute(f"SELECT * FROM tasks WHERE id = {placeholder} AND user_id = {placeholder}", (task_id, user_id))
        row = cursor.fetchone()
        
        if row:
            return Task.from_row(row)
        return None
    finally:
        conn.close()


def get_all_tasks(user_id: int = 1, status: Optional[str] = None) -> List[Task]:
    """获取用户的所有任务"""
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        if status:
            cursor.execute(f"SELECT * FROM tasks WHERE user_id = {placeholder} AND status = {placeholder} ORDER BY created_at DESC", 
                          (user_id, status))
        else:
            cursor.execute(f"SELECT * FROM tasks WHERE user_id = {placeholder} ORDER BY created_at DESC", (user_id,))
        
        rows = cursor.fetchall()
        return [Task.from_row(row) for row in rows]
    finally:
        conn.close()


def update_task(task_id: int, user_id: int = 1, **kwargs) -> Optional[Task]:
    """更新任务"""
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        valid_fields = ['title', 'description', 'start_time', 'end_time', 
                       'deadline', 'duration', 'priority', 'status', 'user_text']
        
        set_clauses = []
        values = []
        
        for field in valid_fields:
            if field in kwargs and kwargs[field] is not None:
                value = kwargs[field]
                
                # ✅ 处理时间字段
                if field in ['start_time', 'end_time', 'deadline']:
                    if isinstance(value, str):
                        value = value.replace('T', ' ').split('.')[0]
                
                set_clauses.append(f"{field} = {placeholder}")
                values.append(value)
        
        if not set_clauses:
            return get_task_by_id(task_id, user_id)
        
        # ✅ 关键修复：使用 CAST 确保类型正确
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # ✅ 为时间字段添加 CAST 转换
        final_set_clauses = []
        for i, clause in enumerate(set_clauses):
            field_name = clause.split(' = ')[0]
            if field_name in ['start_time', 'end_time', 'deadline']:
                final_set_clauses.append(f"{field_name} = CAST({placeholder} AS DATETIME)")
            elif field_name == 'duration':
                final_set_clauses.append(f"{field_name} = CAST({placeholder} AS UNSIGNED)")
            else:
                final_set_clauses.append(clause)
        
        all_values = values + [now, task_id, user_id]
        
        sql = f"""UPDATE tasks 
                 SET {', '.join(final_set_clauses)}, updated_at = {placeholder}
                 WHERE id = {placeholder} AND user_id = {placeholder}"""
        
        cursor.execute(sql, all_values)
        conn.commit()
        
        if cursor.rowcount > 0:
            return get_task_by_id(task_id, user_id)
        return None
        
    except Exception as e:
        print(f"❌ 数据库更新失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise
    finally:
        conn.close()


def delete_task(task_id: int, user_id: int = 1) -> bool:
    """删除任务"""
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        cursor.execute(f"DELETE FROM tasks WHERE id = {placeholder} AND user_id = {placeholder}", (task_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_tasks_by_date_range(user_id: int, start_date: str, end_date: str) -> List[Task]:
    """获取指定日期范围内的任务"""
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.due_date >= start_date,
            Task.due_date <= end_date
        ).all()
        return tasks
    except Exception as e:
        print(f"❌ 获取任务失败: {e}")
        return []
    finally:
        db.close()


def get_tasks_by_date(user_id: int, date: str) -> List[Task]:
    """获取指定日期的所有任务
    
    查询逻辑：
    - 只查询 start_time 在该日期的任务
    - 不再查询 deadline（避免混淆）
    - 按 start_time 升序排列
    """
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        print(f"🔍 查询日期任务: user_id={user_id}, date={date}")
        
        # 只查询该日期开始的任务
        cursor.execute(f"""
            SELECT * FROM tasks 
            WHERE user_id = {placeholder} 
            AND DATE(start_time) = {placeholder}
            ORDER BY start_time ASC
        """, (user_id, date))
        
        rows = cursor.fetchall()
        print(f"✅ 找到 {len(rows)} 个任务")
        
        tasks = [Task.from_row(row) for row in rows]
        
        # 打印任务详情用于调试
        for task in tasks:
            print(f"   - {task.title}: start_time={task.start_time}, deadline={task.deadline}")
        
        return tasks
    except Exception as e:
        print(f"❌ 获取指定日期任务失败: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

# ==================== 用户偏好 CRUD 操作 ====================

def get_user_preferences(user_id: int = 1) -> Optional[UserPreference]:
    """获取用户偏好设置"""
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        cursor.execute(f"SELECT * FROM user_preferences WHERE user_id = {placeholder}", (user_id,))
        row = cursor.fetchone()
        
        if row:
            return UserPreference.from_row(row)
        return None
    finally:
        conn.close()


def create_user_preferences(user_id: int = 1, blocked_time_start: str = "22:00",
                            blocked_time_end: str = "08:00", default_priority: str = "medium",
                            remembered_habits: dict = None, assistant_nickname: str = "",
                            user_nickname: str = "", task_buffer_minutes: int = 15,
                            user_city: str = "北京", user_type: str = "worker",
                            workday_hours: float = 8.0, preferred_time_slot: str = "morning",
                            time_slot_offset: int = 0) -> UserPreference:
    """创建用户偏好设置"""
    conn = get_connection()
    cursor = conn.cursor()
    import json
    placeholder = _get_placeholder()
    
    try:
        habits_json = json.dumps(remembered_habits or {}, ensure_ascii=False)
        placeholders = ", ".join([placeholder] * 13)  # ⭐ Phase 3: 增加到13个字段
        cursor.execute(f"""
            INSERT INTO user_preferences (user_id, blocked_time_start, blocked_time_end, 
                                         default_priority, remembered_habits, 
                                         assistant_nickname, user_nickname, task_buffer_minutes,
                                         user_city, user_type, workday_hours, 
                                         preferred_time_slot, time_slot_offset)
            VALUES ({placeholders})
        """, (user_id, blocked_time_start, blocked_time_end, default_priority, 
              habits_json, assistant_nickname, user_nickname, task_buffer_minutes,
              user_city, user_type, workday_hours, preferred_time_slot, time_slot_offset))  # ⭐ Phase 3: 添加所有新字段
        
        conn.commit()
        return get_user_preferences(user_id)
    finally:
        conn.close()


def update_user_preferences(user_id: int, **kwargs) -> UserPreference:
    """
    更新用户偏好设置
    
    Args:
        user_id: 用户ID
        **kwargs: 要更新的字段
    
    Returns:
        更新后的用户偏好对象
    """
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = _get_placeholder()
    
    try:
        if not kwargs:
            return get_user_preferences(user_id)
        
        set_clauses = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['blocked_time_start', 'blocked_time_end', 'default_priority', 
                      'assistant_nickname', 'user_nickname', 'task_buffer_minutes', 
                      'user_city', 'user_type',  # ⭐ Phase 3: 用户类型
                      'workday_hours', 'preferred_time_slot', 'time_slot_offset']:  # ⭐ Phase 3: 个性化参数
                set_clauses.append(f"{key} = {placeholder}")
                if isinstance(value, dict):
                    import json
                    values.append(json.dumps(value, ensure_ascii=False))
                else:
                    values.append(value)
            elif key == 'remembered_habits':
                set_clauses.append(f"remembered_habits = {placeholder}")
                import json
                values.append(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value)
        
        if not set_clauses:
            return get_user_preferences(user_id)
        
        values.append(user_id)
        update_sql = f"UPDATE user_preferences SET {', '.join(set_clauses)} WHERE user_id = {placeholder}"
        
        cursor.execute(update_sql, values)
        conn.commit()
        
        return get_user_preferences(user_id)
    finally:
        conn.close()

