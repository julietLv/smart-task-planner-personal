"""
Phase 3 数据库迁移脚本 - 添加用户画像相关字段

需要添加的字段：
- user_type: 用户类型 (student/worker/elderly)
- workday_hours: 工作日时长（小时）
- preferred_time_slot: 偏好时段 (morning/noon/afternoon/evening/night)
- time_slot_offset: 时间段偏移（小时）
"""
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.database import get_connection, DATABASE_TYPE


def migrate_sqlite():
    """SQLite 数据库迁移"""
    print("\n🔧 开始 SQLite 数据库迁移...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 添加 user_type 字段
        try:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN user_type TEXT DEFAULT 'worker'")
            print("✅ 已添加 user_type 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠️  user_type 字段已存在，跳过")
            else:
                raise
        
        # 添加 workday_hours 字段
        try:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN workday_hours REAL DEFAULT 8.0")
            print("✅ 已添加 workday_hours 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠️  workday_hours 字段已存在，跳过")
            else:
                raise
        
        # 添加 preferred_time_slot 字段
        try:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN preferred_time_slot TEXT DEFAULT 'morning'")
            print("✅ 已添加 preferred_time_slot 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠️  preferred_time_slot 字段已存在，跳过")
            else:
                raise
        
        # 添加 time_slot_offset 字段
        try:
            cursor.execute("ALTER TABLE user_preferences ADD COLUMN time_slot_offset INTEGER DEFAULT 0")
            print("✅ 已添加 time_slot_offset 字段")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("⚠️  time_slot_offset 字段已存在，跳过")
            else:
                raise
        
        conn.commit()
        print("\n✅ SQLite 数据库迁移完成！\n")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ SQLite 迁移失败: {e}\n")
        raise
    finally:
        conn.close()


def migrate_mysql():
    """MySQL 数据库迁移"""
    print("\n🔧 开始 MySQL 数据库迁移...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 检查并添加 user_type 字段
        cursor.execute("SHOW COLUMNS FROM user_preferences LIKE 'user_type'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE user_preferences 
                ADD COLUMN user_type VARCHAR(20) DEFAULT 'worker' 
                COMMENT '用户类型 (student/worker/elderly)'
            """)
            print("✅ 已添加 user_type 字段")
        else:
            print("⚠️  user_type 字段已存在，跳过")
        
        # 检查并添加 workday_hours 字段
        cursor.execute("SHOW COLUMNS FROM user_preferences LIKE 'workday_hours'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE user_preferences 
                ADD COLUMN workday_hours DECIMAL(4,1) DEFAULT 8.0 
                COMMENT '工作日时长（小时）'
            """)
            print("✅ 已添加 workday_hours 字段")
        else:
            print("⚠️  workday_hours 字段已存在，跳过")
        
        # 检查并添加 preferred_time_slot 字段
        cursor.execute("SHOW COLUMNS FROM user_preferences LIKE 'preferred_time_slot'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE user_preferences 
                ADD COLUMN preferred_time_slot VARCHAR(20) DEFAULT 'morning' 
                COMMENT '偏好时段 (morning/noon/afternoon/evening/night)'
            """)
            print("✅ 已添加 preferred_time_slot 字段")
        else:
            print("⚠️  preferred_time_slot 字段已存在，跳过")
        
        # 检查并添加 time_slot_offset 字段
        cursor.execute("SHOW COLUMNS FROM user_preferences LIKE 'time_slot_offset'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE user_preferences 
                ADD COLUMN time_slot_offset INT DEFAULT 0 
                COMMENT '时间段偏移（小时）'
            """)
            print("✅ 已添加 time_slot_offset 字段")
        else:
            print("⚠️  time_slot_offset 字段已存在，跳过")
        
        conn.commit()
        print("\n✅ MySQL 数据库迁移完成！\n")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ MySQL 迁移失败: {e}\n")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 3 数据库迁移工具")
    print("=" * 70)
    print(f"当前数据库类型: {DATABASE_TYPE}")
    
    if DATABASE_TYPE == "mysql":
        migrate_mysql()
    else:
        migrate_sqlite()
    
    print("=" * 70)
    print("迁移完成！请重启后端服务以应用更改。")
    print("=" * 70)
