import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
# 测试指令三用
print("开始测试...")

try:
    from app.models.database import init_db, get_connection
    print("✅ 数据库模块导入成功")

    # 检查数据库文件是否存在
    from app.models.database import DATABASE_PATH
    print(f"数据库路径: {DATABASE_PATH}")
    print(f"数据库文件存在: {os.path.exists(DATABASE_PATH)}")

    # 测试连接
    conn = get_connection()
    print("✅ 数据库连接成功")

    # 检查表是否存在
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"数据库中的表: {[t['name'] for t in tables]}")
    conn.close()

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.models.task_model import create_task, get_all_tasks
    print("\n✅ 任务模型模块导入成功")

    # 创建测试任务
    print("\n创建测试任务...")
    task = create_task(title="测试任务", duration=30)
    print(f"✅ 任务创建成功! ID: {task.id}, 标题: {task.title}")

    # 获取所有任务
    tasks = get_all_tasks()
    print(f"✅ 当前共有 {len(tasks)} 个任务")

except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n测试完成!")
