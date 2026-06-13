"""
测试 MySQL 数据库连接和基本功能
"""
from app.models.database import get_connection, DATABASE_TYPE
from app.models.task_model import create_task, get_all_tasks, get_user_preferences
from datetime import datetime, timedelta
import traceback

def test_mysql_connection():
    """测试 MySQL 连接"""
    print("=" * 60)
    print("🧪 MySQL 数据库功能测试")
    print("=" * 60)
    
    print(f"\n📊 当前数据库类型: {DATABASE_TYPE}")
    
    if DATABASE_TYPE != "mysql":
        print("❌ 错误：当前未使用 MySQL，请检查 .env 配置")
        return False
    
    # 测试 1: 数据库连接
    print("\n[Test 1] 测试数据库连接...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION() as version")
        row = cursor.fetchone()
        # MySQL 使用 DictCursor，返回的是字典
        version = row['version'] if isinstance(row, dict) else row[0]
        print(f"✅ MySQL 版本: {version}")
        conn.close()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        traceback.print_exc()
        return False
    
    # 测试 2: 创建任务
    print("\n[Test 2] 测试创建任务...")
    try:
        task = create_task(
            title="测试任务 - MySQL",
            user_id=1,
            description="这是一个测试任务",
            duration=60,
            priority="medium"
        )
        print(f"✅ 任务创建成功，ID: {task.id}")
    except Exception as e:
        print(f"❌ 创建任务失败: {e}")
        traceback.print_exc()
        return False
    
    # 测试 3: 查询任务
    print("\n[Test 3] 测试查询任务...")
    try:
        tasks = get_all_tasks(user_id=1)
        print(f"✅ 查询成功，共 {len(tasks)} 个任务")
        for t in tasks[:3]:
            print(f"   - [{t.id}] {t.title}")
    except Exception as e:
        print(f"❌ 查询任务失败: {e}")
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！MySQL 配置正确")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_mysql_connection()

