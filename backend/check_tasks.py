import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.models.task_model import get_all_tasks


def check_tasks():
    """检查数据库中的任务"""
    print("=" * 80)
    print("📊 任务数据库检查工具")
    print("=" * 80)

    try:
        # 获取所有任务
        tasks = get_all_tasks(user_id=1)

        print(f"\n✅ 数据库中共有 {len(tasks)} 个任务\n")

        if len(tasks) == 0:
            print("⚠️ 数据库中没有任何任务！")
            print("\n💡 提示：你可以通过以下方式添加任务：")
            print("   1. 在聊天窗口输入自然语言，例如：'明天下午3点开会'")
            print("   2. 点击日历上的时间段直接添加任务")
            print("   3. 使用右侧的任务快速输入框")
            return

        # 显示所有任务
        print("=" * 100)
        print(f"{'ID':<5} {'标题':<25} {'开始时间':<22} {'结束时间':<22} {'优先级':<10} {'状态':<10}")
        print("=" * 100)

        for task in tasks:
            start = task.start_time[:19] if task.start_time else 'N/A'
            end = task.end_time[:19] if task.end_time else 'N/A'
            title = task.title[:23] if len(task.title) > 23 else task.title

            print(f"{task.id:<5} {title:<25} {start:<22} {end:<22} {task.priority:<10} {task.status:<10}")

        print("=" * 100)

        # 统计信息
        print("\n📈 任务统计:")
        pending = sum(1 for t in tasks if t.status == 'pending')
        done = sum(1 for t in tasks if t.status == 'done')
        cancelled = sum(1 for t in tasks if t.status == 'cancelled')
        overdue = sum(1 for t in tasks if t.status == 'overdue')

        print(f"  待完成 (pending): {pending}")
        print(f"  已完成 (done): {done}")
        print(f"  已取消 (cancelled): {cancelled}")
        print(f"  已超时 (overdue): {overdue}")
        print(f"  总计: {len(tasks)}")

        # 检查是否有时间字段
        print("\n🔍 时间字段检查:")
        has_start_time = sum(1 for t in tasks if t.start_time)
        has_end_time = sum(1 for t in tasks if t.end_time)

        print(f"  有开始时间的任务: {has_start_time}/{len(tasks)}")
        print(f"  有结束时间的任务: {has_end_time}/{len(tasks)}")

        if has_start_time == 0:
            print("\n⚠️ 警告：所有任务都没有开始时间！这会导致日历无法显示任务。")

        print("\n💡 如果任务数量大于0但日历不显示，请检查：")
        print("   1. 浏览器控制台是否有错误")
        print("   2. Network 面板中 /api/tasks/ 请求的响应")
        print("   3. 任务的 start_time 和 end_time 字段是否有值")

    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_tasks()
