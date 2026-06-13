"""
数据库迁移脚本：为 user_preferences 表添加 user_type 字段
⭐ Phase 3: 用户画像管理
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.database import get_connection, DATABASE_TYPE


def migrate():
    """执行数据库迁移"""
    
    print("\n" + "=" * 70)
    print("开始数据库迁移：添加 user_type 字段")
    print("=" * 70)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        if DATABASE_TYPE == "mysql":
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'user_preferences'
                AND COLUMN_NAME = 'user_type'
            """)
            result = cursor.fetchone()
            column_exists = result['count'] > 0 if isinstance(result, dict) else result[0] > 0
        else:
            cursor.execute("PRAGMA table_info(user_preferences)")
            columns = [row[1] for row in cursor.fetchall()]
            column_exists = 'user_type' in columns
        
        if column_exists:
            print("\n✅ user_type 字段已存在，无需迁移")
            return
        
        print("\n📝 正在添加 user_type 字段...")
        
        # 添加 user_type 字段
        if DATABASE_TYPE == "mysql":
            cursor.execute("""
                ALTER TABLE user_preferences 
                ADD COLUMN user_type VARCHAR(20) NOT NULL DEFAULT 'worker'
                COMMENT '用户类型: student/worker/elderly'
            """)
        else:
            cursor.execute("""
                ALTER TABLE user_preferences 
                ADD COLUMN user_type TEXT NOT NULL DEFAULT 'worker'
            """)
        
        conn.commit()
        
        print("✅ user_type 字段添加成功")
        print("   - 默认值: worker")
        print("   - 可选值: student, worker, elderly")
        
        # 验证字段
        cursor.execute("SELECT user_id, user_type FROM user_preferences LIMIT 5")
        rows = cursor.fetchall()
        
        if rows:
            print("\n📊 当前用户类型分布:")
            for row in rows:
                # 兼容 MySQL DictCursor 和 SQLite
                if isinstance(row, dict):
                    user_id = row['user_id']
                    user_type = row['user_type']
                else:
                    user_id = row[0]
                    user_type = row[1]
                print(f"   - user_id={user_id}, user_type={user_type}")
        
        print("\n" + "=" * 70)
        print("迁移完成！")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
