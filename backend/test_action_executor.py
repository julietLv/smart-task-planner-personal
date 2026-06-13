"""
测试 ActionExecutor - 纯粹执行者
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.services.action_executor import executor
from datetime import datetime


def test_query_today_tasks():
    """测试查询今日任务"""
    print("\n" + "=" * 60)
    print("🧪 测试: 查询今日任务")
    print("=" * 60)

    result = executor.execute(
        action_name="query_today_tasks",
        params={
            "user_id": 1,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    )

    print(f"✅ 执行结果: {result['success']}")
    if result['success']:
        print(f"📅 日期: {result['date']}")
        print(f"📊 任务数: {result['count']}")
        
        if result['tasks']:
            print(f"\n任务列表:")
            for idx, task in enumerate(result['tasks'][:5], 1):
                print(f"  {idx}. {task['title']} | {task.get('start_time', 'N/A')[:16]}")
    else:
        print(f"❌ 错误: {result.get('error')}")


def test_query_free_time():
    """测试分析空闲时间"""
    print("\n" + "=" * 60)
    print("🧪 测试: 查询空闲时间")
    print("=" * 60)

    result = executor.execute(
        action_name="query_free_time",
        params={
            "user_id": 1,
            "time_range": "tomorrow",
            "activity": "rest"
        }
    )

    print(f"✅ 执行结果: {result['success']}")
    if result['success']:
        analysis = result['analysis']
        print(f"📅 日期: {analysis['day_label']}")
        print(f"⏰ 空闲时间: {analysis['free_hours']:.1f}小时")
        print(f"📊 任务数: {analysis['task_count']}")
    else:
        print(f"❌ 错误: {result.get('error', result.get('message'))}")


def test_analyze_workload():
    """测试分析工作负载"""
    print("\n" + "=" * 60)
    print("🧪 测试: 分析工作负载")
    print("=" * 60)

    result = executor.execute(
        action_name="analyze_workload",
        params={
            "user_id": 1,
            "time_range": "this_week"
        }
    )

    print(f"✅ 执行结果: {result['success']}")
    if result['success']:
        analysis = result['analysis']
        print(f"📅 时间段: {analysis['day_label']}")
        print(f"📊 任务数: {analysis['task_count']}")
        print(f"⏱️ 总时长: {analysis['total_minutes']}分钟")
        print(f"📈 密度: {analysis['density_percent']:.1f}%")
    else:
        print(f"❌ 错误: {result.get('error')}")


def test_unknown_action():
    """测试未知动作"""
    print("\n" + "=" * 60)
    print("🧪 测试: 未知动作")
    print("=" * 60)

    result = executor.execute(
        action_name="non_existent_action",
        params={}
    )

    print(f"✅ 执行结果: {result['success']}")
    print(f"❌ 错误: {result.get('error')}")
    print(f"📦 可用动作: {result.get('available_actions', [])}")


def test_list_available_actions():
    """列出所有可用动作"""
    print("\n" + "=" * 60)
    print("🧪 测试: 列出所有可用动作")
    print("=" * 60)

    actions = executor.get_available_actions()
    print(f"📦 共注册 {len(actions)} 个动作:\n")
    
    for name, metadata in actions.items():
        print(f"  • {name}")
        print(f"    描述: {metadata['description']}")
        if metadata.get('parameters'):
            print(f"    参数: {list(metadata['parameters'].keys())}")
        print()


if __name__ == "__main__":
    print("\n🚀 开始测试 ActionExecutor")

    test_list_available_actions()
    test_query_today_tasks()
    test_query_free_time()
    test_analyze_workload()
    test_unknown_action()

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60 + "\n")
