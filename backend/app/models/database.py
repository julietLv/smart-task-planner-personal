import os
import sqlite3
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# 数据库类型配置
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "mysql").lower()

if DATABASE_TYPE == "mysql":
    import pymysql
    from pymysql.cursors import DictCursor
    from app.services.cache_service import db_pool
    
    MYSQL_CONFIG = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "task_planner"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False
    }
else:
    DATABASE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
        "data", 
        "schedule.db"
    )


def get_connection():
    """获取数据库连接（支持 SQLite 和 MySQL，MySQL 使用连接池）"""
    if DATABASE_TYPE == "mysql":
        # 使用连接池获取连接
        return db_pool.get_connection()
    else:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    """初始化数据库，创建所需的表和索引"""
    if DATABASE_TYPE == "mysql":
        _init_mysql_db()
    else:
        _init_sqlite_db()


def _init_sqlite_db():
    """初始化 SQLite 数据库"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 创建tasks表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT,
                end_time TEXT,
                deadline TEXT,
                duration INTEGER,
                priority TEXT CHECK(priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
                status TEXT CHECK(status IN ('pending', 'done', 'cancelled', 'overdue')) DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                user_text TEXT
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_status 
            ON tasks(user_id, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deadline 
            ON tasks(deadline)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_start_time 
            ON tasks(start_time)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_created 
            ON tasks(user_id, created_at DESC)
        """)
        
        # 创建user_preferences表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                blocked_time_start TEXT DEFAULT '22:00',
                blocked_time_end TEXT DEFAULT '08:00',
                default_priority TEXT CHECK(default_priority IN ('high', 'medium', 'low')) DEFAULT 'medium',
                remembered_habits TEXT DEFAULT '{}',
                assistant_nickname TEXT DEFAULT '',
                user_nickname TEXT DEFAULT '',
                task_buffer_minutes INTEGER DEFAULT 15,
                user_city TEXT DEFAULT '北京',
                user_type TEXT DEFAULT 'worker',
                workday_hours REAL DEFAULT 8.0,
                preferred_time_slot TEXT DEFAULT 'morning',
                time_slot_offset INTEGER DEFAULT 0
            )
        """)
        
        # 创建notifications表（通知持久化）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT,
                notification_type VARCHAR(20) DEFAULT 'info',
                task_id INTEGER,
                is_read BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                read_at DATETIME
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notif_user_id 
            ON notifications(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notif_is_read 
            ON notifications(is_read)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_notif_created_at 
            ON notifications(created_at DESC)
        """)
        
        # 为已存在的表添加新字段
        for column, default in [
            ("remembered_habits", "'{}'"),
            ("assistant_nickname", "''"),
            ("user_nickname", "''"),
            ("task_buffer_minutes", "15"),
            ("user_city", "'北京'"),
            ("user_type", "'worker'"),
            ("workday_hours", "8.0"),
            ("preferred_time_slot", "'morning'"),
            ("time_slot_offset", "0")
        ]:
            try:
                if column == "task_buffer_minutes" or column == "time_slot_offset":
                    cursor.execute(f"ALTER TABLE user_preferences ADD COLUMN {column} INTEGER DEFAULT {default}")
                elif column == "workday_hours":
                    cursor.execute(f"ALTER TABLE user_preferences ADD COLUMN {column} REAL DEFAULT {default}")
                else:
                    cursor.execute(f"ALTER TABLE user_preferences ADD COLUMN {column} TEXT DEFAULT {default}")
            except sqlite3.OperationalError:
                pass
        
        conn.commit()
        print("SQLite 数据库表结构和索引初始化完成")
    finally:
        conn.close()


def _init_mysql_db():
    """初始化 MySQL 数据库（含优化索引）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 创建tasks表（含索引）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT DEFAULT 1,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                start_time DATETIME,
                end_time DATETIME,
                deadline DATETIME,
                duration INT,
                priority ENUM('high', 'medium', 'low') DEFAULT 'medium',
                status ENUM('pending', 'done', 'cancelled', 'overdue') DEFAULT 'pending',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                user_text TEXT COMMENT '智能排程时用户的原始输入',
                INDEX idx_user_status (user_id, status),
                INDEX idx_deadline (deadline),
                INDEX idx_start_time (start_time),
                INDEX idx_user_created (user_id, created_at DESC),
                INDEX idx_time_range (start_time, end_time)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建user_preferences表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INT PRIMARY KEY,
                blocked_time_start VARCHAR(10) DEFAULT '22:00',
                blocked_time_end VARCHAR(10) DEFAULT '08:00',
                default_priority ENUM('high', 'medium', 'low') DEFAULT 'medium',
                remembered_habits JSON,
                assistant_nickname VARCHAR(50) DEFAULT '',
                user_nickname VARCHAR(50) DEFAULT '',
                task_buffer_minutes INT DEFAULT 15 COMMENT '任务间缓冲时间（分钟）',
                user_city VARCHAR(100) DEFAULT '北京' COMMENT '用户所在城市',
                user_type VARCHAR(20) DEFAULT 'worker' COMMENT '用户类型 (student/worker/elderly)',
                workday_hours DECIMAL(4,1) DEFAULT 8.0 COMMENT '工作日时长（小时）',
                preferred_time_slot VARCHAR(20) DEFAULT 'morning' COMMENT '偏好时段 (morning/noon/afternoon/evening/night)',
                time_slot_offset INT DEFAULT 0 COMMENT '时间段偏移（小时）'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建notifications表（通知持久化）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                type VARCHAR(50) NOT NULL COMMENT '通知类型',
                title VARCHAR(200) NOT NULL COMMENT '通知标题',
                message TEXT COMMENT '通知内容',
                notification_type VARCHAR(20) DEFAULT 'info' COMMENT '通知级别',
                task_id INT COMMENT '关联任务ID',
                is_read BOOLEAN DEFAULT FALSE COMMENT '是否已读',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                read_at DATETIME COMMENT '阅读时间',
                INDEX idx_notif_user_id (user_id),
                INDEX idx_notif_is_read (is_read),
                INDEX idx_notif_created_at (created_at DESC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 迁移：user_text
        try:
            cursor.execute("SHOW COLUMNS FROM tasks LIKE 'user_text'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE tasks ADD COLUMN user_text TEXT COMMENT '智能排程时用户的原始输入'")
                conn.commit()
                print("user_text 字段已添加")
        except Exception:
            pass
        
        # 迁移：status overdue
        try:
            print("开始检查 status 字段定义...")
            
            cursor.execute("SHOW COLUMNS FROM tasks LIKE 'status'")
            result = cursor.fetchone()
            
            if result:
                column_type = result.get('Type', '') if isinstance(result, dict) else result[1]
                print(f"当前 status 字段类型: {column_type}")
                
                if 'overdue' not in column_type.lower():
                    print("检测到 status 字段缺少 'overdue' 枚举值，正在更新表结构...")
                    cursor.execute("""
                        ALTER TABLE tasks 
                        MODIFY COLUMN status ENUM('pending', 'done', 'cancelled', 'overdue') 
                        DEFAULT 'pending'
                    """)
                    conn.commit()
                    print("status 字段已更新，新增 'overdue' 枚举值")
                else:
                    print("status 字段已包含 'overdue' 枚举值，无需更新")
            else:
                print("未找到 status 字段，可能表结构异常")
        except Exception as e:
            import traceback
            print(f"检查/更新 status 字段时出错: {e}")
            print(traceback.format_exc())
            
            try:
                print("尝试直接更新 status 字段...")
                cursor.execute("""
                    ALTER TABLE tasks 
                    MODIFY COLUMN status ENUM('pending', 'done', 'cancelled', 'overdue') 
                    DEFAULT 'pending'
                """)
                conn.commit()
                print("直接更新 status 字段成功")
            except Exception as alter_error:
                print(f"直接更新也失败: {alter_error}")
        
        conn.commit()
        print("MySQL 数据库表结构和索引初始化完成")
    except Exception as e:
        print(f"MySQL 初始化失败: {e}")
        raise
    finally:
        conn.close()


# 在模块加载时自动初始化数据库
init_db()