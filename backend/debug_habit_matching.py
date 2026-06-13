"""
调试习惯匹配问题 - 简化版
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.or_tools_scheduler import ORToolsScheduler
from app.services.scheduler_service import remember_user_preference


def debug_habit_matching():
    """调试习惯匹配"""
    
    print("\n" + "=" * 70)
    print("🐞 调试：习惯匹配分数偏低问题")
    print("=" * 70)
    
    user_id = 1
    
    # ==================== 步骤1: 确认学习习惯 ====================
    print("\n📚 步骤1: 确认用户学习习惯\n")
    
    # 学习"学习"任务的习惯
    print("   1. 学习『学习』任务的偏好...")
    for i in range(4):  # ⭐ time_slot 需要4次才能达到阈值
        remember_user_preference(
            task_title="学习",
            adjustment_type="time_slot",  # ⭐ 修正：使用 time_slot 而非 time_period
            old_value="",
            new_value="evening"
        )
    
    for i in range(3):
        remember_user_preference(
            task_title="学习",
            adjustment_type="duration",
            old_value=0,
            new_value=90
        )
    
    for i in range(5):
        remember_user_preference(
            task_title="学习",
            adjustment_type="priority",
            old_value="",
            new_value="high"
        )
    
    print("       ✅ 时间段偏好: evening (晚上)")
    print("       ✅ 时长偏好: 90分钟")
    print("       ✅ 优先级偏好: high")
    
    # ==================== 步骤2: 运行排程（观察调试日志）====================
    print("\n" + "=" * 70)
    print("🧪 步骤2: 运行智能排程（观察详细调试日志）")
    print("=" * 70)
    
    scheduler = ORToolsScheduler()
    
    # 测试用例：明天晚上学习
    result = scheduler.schedule_task(
        new_task={
            "title": "学习",
            "duration": 90,
            "priority": "high",
            "start_time": "2026-05-23T18:00:00",  # 晚上6点，符合 evening 习惯
            "user_id": user_id  # ⭐ user_id 应该在 new_task 中传递
        },
        existing_tasks=[],
        preferences={},
        return_top_k=1
    )
    
    if result["success"]:
        best = result["best_solution"]
        print(f"\n✅ 排程成功！")
        print(f"   推荐时间: {best['start_time']} - {best['end_time']}")
        print(f"   总评分: {best['score']}")
        
        # 查看习惯匹配分
        if "dimension_details" in best:
            habit_detail = best["dimension_details"].get("habit_match", {})
            print(f"\n📊 习惯匹配维度详情:")
            print(f"   原始分: {habit_detail.get('raw', 'N/A')}")
            print(f"   归一化: {habit_detail.get('normalized', 'N/A')}")
            print(f"   加权分: {habit_detail.get('weighted', 'N/A')}")
            print(f"   权重: {habit_detail.get('weight', 'N/A')}")
    
    print("\n" + "=" * 70)
    print("🔍 请查看上方的 [DEBUG] 日志，定位问题：")
    print("   1. preferred_time_slot 是否正确设置为 'evening'？")
    print("   2. hour 的值是否在 evening 范围内（18-22）？")
    print("   3. 各维度得分是否符合预期？")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    debug_habit_matching()
