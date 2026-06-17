"""
测试三层约束评分系统
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.three_layer_scoring import three_layer_scoring


def test_objective_constraints():
    """测试Layer 1: 客观约束"""
    
    print("\n" + "=" * 70)
    print("测试1: Layer 1 - 客观约束检查")
    print("=" * 70)
    
    # 测试1.1: 正常时间（应该通过）
    print("\n[OK] 测试1.1: 正常工作时间安排")
    slot = datetime(2026, 5, 23, 10, 0)  # 上午10点
    task = {"title": "学习", "duration": 60, "type": "study"}
    
    result = three_layer_scoring._check_objective_constraints(slot, task, "student")
    print(f"    blocked: {result['blocked']}")
    print(f"   penalty: {result['penalty']}")
    print(f"   violations: {result['violations']}")
    
    # 测试1.2: 睡眠时间（应该被阻止）
    print("\n[FAIL] 测试1.2: 睡眠时间安排任务")
    slot = datetime(2026, 5, 23, 2, 0)  # 凌晨2点
    
    result = three_layer_scoring._check_objective_constraints(slot, task, "student")
    print(f"   blocked: {result['blocked']}")
    print(f"   penalty: {result['penalty']}")
    print(f"   violations: {result['violations']}")
    
    # 测试1.3: 连续工作超时
    print("\n[WARN] 测试1.3: 连续工作超过4小时")
    slot = datetime(2026, 5, 23, 9, 0)
    task = {"title": "深度学习", "duration": 300, "type": "study"}  # 5小时
    
    result = three_layer_scoring._check_objective_constraints(slot, task, "worker")
    print(f"   blocked: {result['blocked']}")
    print(f"   penalty: {result['penalty']}")
    print(f"   violations: {result['violations']}")


def test_standard_score():
    """测试Layer 2: 人群标准评分"""
    
    print("\n" + "=" * 70)
    print("测试2: Layer 2 - 人群标准评分")
    print("=" * 70)
    
    profile = three_layer_scoring.profile_service.get_profile("student")
    
    # 测试2.1: 高效时段
    print("\n[OK] 测试2.1: 学生在高效时段学习")
    slot = datetime(2026, 5, 23, 10, 0)  # 上午10点（在09:00-11:30内）
    task = {"title": "复习数学", "duration": 90, "type": "study"}
    
    score = three_layer_scoring._calculate_standard_score(slot, task, profile, [])
    print(f"   标准评分: {score}")
    print(f"   预期: 高分（在高效时段）")
    
    # 测试2.2: 非高效时段
    print("\n[WARN] 测试2.2: 学生在非高效时段学习")
    slot = datetime(2026, 5, 23, 22, 0)  # 晚上10点
    
    score = three_layer_scoring._calculate_standard_score(slot, task, profile, [])
    print(f"   标准评分: {score}")
    print(f"   预期: 较低分（在非高效时段）")


def test_personal_adjustment():
    """测试Layer 3: 个性化调整"""
    
    print("\n" + "=" * 70)
    print("测试3: Layer 3 - 个性化微调")
    print("=" * 70)
    
    profile = three_layer_scoring.profile_service.get_profile("worker")
    
    # 模拟用户习惯：偏好晚上工作
    user_habits = {
        "preferred_time_slot": "evening",
        "preferred_duration": 90,
        "preferred_priority": "high"
    }
    
    # 测试3.1: 符合个人偏好
    print("\n[OK] 测试3.1: 安排在晚上（符合个人偏好）")
    slot = datetime(2026, 5, 23, 19, 0)  # 晚上7点
    task = {"title": "项目工作", "duration": 90, "priority": "high", "type": "work"}
    
    adjustment = three_layer_scoring._calculate_personal_adjustment(
        slot, task, profile, user_habits
    )
    print(f"   个性化调整: {adjustment}")
    print(f"   预期: 正分（符合偏好）")
    
    # 测试3.2: 不符合个人偏好
    print("\n[FAIL] 测试3.2: 安排在上午（不符合个人偏好）")
    slot = datetime(2026, 5, 23, 9, 0)  # 上午9点
    
    adjustment = three_layer_scoring._calculate_personal_adjustment(
        slot, task, profile, user_habits
    )
    print(f"   个性化调整: {adjustment}")
    print(f"   预期: 负分或零分（不符合偏好）")


def test_full_scoring():
    """测试完整的三层约束评分"""
    
    print("\n" + "=" * 70)
    print("测试4: 完整三层约束评分")
    print("=" * 70)
    
    # 测试4.1: 标准用户（无个性化）
    print("\n[INFO] 测试4.1: 标准学生用户")
    slot = datetime(2026, 5, 23, 10, 0)
    task = {
        "title": "复习考试",
        "duration": 90,
        "priority": "high",
        "type": "study",
        "user_type": "student"
    }
    
    result = three_layer_scoring.calculate_constrained_score(
        slot, task, user_id=1, user_type="student"
    )
    
    print(f"   最终评分: {result['final_score']}")
    print(f"   客观约束惩罚: {result['breakdown']['objective_penalty']}")
    print(f"   人群标准分: {result['breakdown']['standard_score']}")
    print(f"   个性化调整: {result['breakdown']['personal_adjustment']}")
    print(f"   违反约束: {result['violations']}")
    
    # 测试4.2: 个性化用户
    print("\n[INFO] 测试4.2: 个性化工作者用户（偏好晚上）")
    slot = datetime(2026, 5, 23, 19, 0)
    task = {
        "title": "项目开发",
        "duration": 120,
        "priority": "high",
        "type": "work",
        "user_type": "worker"
    }
    
    result = three_layer_scoring.calculate_constrained_score(
        slot, task, user_id=1, user_type="worker"
    )
    
    print(f"   最终评分: {result['final_score']}")
    print(f"   客观约束惩罚: {result['breakdown']['objective_penalty']}")
    print(f"   人群标准分: {result['breakdown']['standard_score']}")
    print(f"   个性化调整: {result['breakdown']['personal_adjustment']}")
    print(f"   违反约束: {result['violations']}")
    
    # 测试4.3: 违反客观约束
    print("\n[BLOCKED] 测试4.3: 睡眠时间排程（应被阻止）")
    slot = datetime(2026, 5, 23, 2, 0)  # 凌晨2点
    
    result = three_layer_scoring.calculate_constrained_score(
        slot, task, user_id=1, user_type="worker"
    )
    
    print(f"   最终评分: {result['final_score']}")
    print(f"   是否被阻止: {'是' if result['final_score'] == -float('inf') else '否'}")
    print(f"   违反约束: {result['violations']}")


if __name__ == "__main__":
    print("\n开始测试三层约束评分系统...\n")
    
    test_objective_constraints()
    test_standard_score()
    test_personal_adjustment()
    test_full_scoring()
    
    print("\n" + "=" * 70)
    print("所有测试完成！")
    print("=" * 70 + "\n")
