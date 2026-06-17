"""测试 Tasks 表 CRUD 操作"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.task_model import (
    create_task, get_task_by_id, get_all_tasks, update_task, delete_task,
    get_tasks_by_date_range, get_tasks_today, get_tasks_this_week,
    search_tasks, get_task_statistics, get_tasks_by_deadline
)


def test_crud_operations():
    """测试基础 CRUD 操作"""
    print("\n" + "=" * 70)
    print("🧪 测试 Tasks 表 CRUD 操作")
    print("=" * 70)

    user_id = 1

    # ==================== 1. Create - 创建任务 ====================
    print("\n📝 测试1: 创建任务 (Create)")
    print("-" * 70)

    task1 = create_task(
        title="完成项目报告",
        user_id=user_id,
        description="需要完成Q2季度项目总结报告",
        start_time=(datetime.now() + timedelta(days=1, hours=2)).isoformat(),
        end_time=(datetime.now() + timedelta(days=1, hours=4)).isoformat(),
        deadline=(datetime.now() + timedelta(days=3)).isoformat(),
        duration=120,
        priority="high",
        status="pending"
    )
    print(f"✅ 创建任务1: ID={task1.id}, 标题={task1.title}")

    task2 = create_task(
        title="团队会议",
        user_id=user_id,
        start_time=(datetime.now() + timedelta(hours=1)).isoformat(),
        end_time=(datetime.now() + timedelta(hours=2)).isoformat(),
        duration=60,
        priority="medium"
    )
    print(f"✅ 创建任务2: ID={task2.id}, 标题={task2.title}")

    task3 = create_task(
        title="阅读技术文档",
        user_id=user_id,
        duration=90,
        priority="low",
        deadline=(datetime.now() + timedelta(days=5)).isoformat()
    )
    print(f"✅ 创建任务3: ID={task3.id}, 标题={task3.title}")

    # ==================== 2. Read - 读取任务 ====================
    print("\n📖 测试2: 读取任务 (Read)")
    print("-" * 70)

    # 根据ID查询
    fetched_task = get_task_by_id(task1.id, user_id)
    print(f"✅ 根据ID查询: {fetched_task.title} (ID={fetched_task.id})")

    # 获取所有任务
    all_tasks = get_all_tasks(user_id)
    print(f"✅ 获取所有任务: 共 {len(all_tasks)} 个")

    # 按状态过滤
    pending_tasks = get_all_tasks(user_id, status="pending")
    print(f"✅ 待完成任务: {len(pending_tasks)} 个")

    # ==================== 3. Update - 更新任务 ====================
    print("\n✏️  测试3: 更新任务 (Update)")
    print("-" * 70)

    # 更新任务标题和优先级
    updated_task = update_task(
        task1.id,
        user_id,
        title="完成项目报告（修订版）",
        priority="high"
    )
    print(f"✅ 更新任务: {updated_task.title}, 优先级={updated_task.priority}")

    # 更新任务状态
    completed_task = update_task(task2.id, user_id, status="done")
    print(f"✅ 标记完成: {completed_task.title}, 状态={completed_task.status}")

    # ==================== 4. Delete - 删除任务 ====================
    print("\n🗑️  测试4: 删除任务 (Delete)")
    print("-" * 70)

    deleted = delete_task(task3.id, user_id)
    print(f"✅ 删除任务3: {'成功' if deleted else '失败'}")

    # 验证删除
    remaining_tasks = get_all_tasks(user_id)
    print(f"✅ 剩余任务数: {len(remaining_tasks)}")

    # ==================== 5. 高级查询 ====================
    print("\n🔍 测试5: 高级查询")
    print("-" * 70)

    # 日期范围查询
    today = datetime.now()
    week_later = today + timedelta(days=7)
    date_range_tasks = get_tasks_by_date_range(
        user_id,
        today.isoformat(),
        week_later.isoformat()
    )
    print(f"✅ 未来7天任务: {len(date_range_tasks)} 个")

    # 今日任务
    today_tasks = get_tasks_today(user_id)
    print(f"✅ 今日任务: {len(today_tasks)} 个")

    # 本周任务
    week_tasks = get_tasks_this_week(user_id)
    print(f"✅ 本周任务: {len(week_tasks)} 个")

    # 搜索任务
    search_results = search_tasks(user_id, keyword="项目", status="pending")
    print(f"✅ 搜索'项目': 找到 {len(search_results)} 个结果")

    # 即将到期任务
    due_soon = get_tasks_by_deadline(user_id, days=5)
    print(f"✅ 5天内到期: {len(due_soon)} 个")

    # ==================== 6. 统计信息 ====================
    print("\n📊 测试6: 任务统计")
    print("-" * 70)

    stats = get_task_statistics(user_id)
    print(f"✅ 总任务数: {stats['total_tasks']}")
    print(f"✅ 待完成: {stats['by_status']['pending']}")
    print(f"✅ 已完成: {stats['by_status']['done']}")
    print(f"✅ 高优先级: {stats['by_priority']['high']}")
    print(f"✅ 今日任务: {stats['today_count']}")
    print(f"✅ 即将到期: {stats['due_soon_count']}")

    print("\n" + "=" * 70)
    print("✅ 所有 CRUD 测试完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        test_crud_operations()
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
