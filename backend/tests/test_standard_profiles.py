"""
测试标准作息模板服务
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.standard_profile_service import standard_profile_service


def test_standard_profiles():
    """测试标准模板加载"""
    
    print("\n" + "=" * 70)
    print("🧪 测试1: 标准模板加载")
    print("=" * 70)
    
    # 测试1.1: 获取所有用户类型
    print("\n📋 可用的用户类型:")
    profile_types = standard_profile_service.get_all_profile_types()
    for ptype in profile_types:
        print(f"   - {ptype}")
    
    # 测试1.2: 获取学生模板
    print("\n🎓 学生模板详情:")
    student_profile = standard_profile_service.get_profile("student")
    if student_profile:
        print(f"   名称: {student_profile['name']}")
        print(f"   描述: {student_profile['description']}")
        print(f"   起床时间: {student_profile['typical_schedule']['wake_up']}")
        print(f"   睡觉时间: {student_profile['typical_schedule']['sleep']}")
        print(f"   高效时段: {student_profile['typical_schedule']['productive_hours']}")
        print(f"   工作日学习时长: {student_profile['capacity']['workday_study_hours']}小时")
    
    # 测试1.3: 获取工作者模板
    print("\n💼 工作者模板详情:")
    worker_profile = standard_profile_service.get_profile("worker")
    if worker_profile:
        print(f"   名称: {worker_profile['name']}")
        print(f"   工作日工作时长: {worker_profile['capacity']['workday_work_hours']}小时")
        print(f"   偏好时段: {worker_profile['preferences']['preferred_time_slot']}")
    
    # 测试1.4: 获取老年人模板
    print("\n👴 老年人模板详情:")
    elderly_profile = standard_profile_service.get_profile("elderly")
    if elderly_profile:
        print(f"   名称: {elderly_profile['name']}")
        print(f"   每日活动时长: {elderly_profile['capacity']['daily_active_hours']}小时")
        print(f"   休息时段: {elderly_profile['typical_schedule'].get('rest_periods', 'N/A')}")


def test_objective_constraints():
    """测试客观约束"""
    
    print("\n" + "=" * 70)
    print("🧪 测试2: 客观约束检查")
    print("=" * 70)
    
    # 测试2.1: 天气约束
    print("\n🌧️ 天气影响规则:")
    rain_impact = standard_profile_service.check_objective_constraint("weather_impact", "rain")
    if rain_impact:
        print(f"   下雨天户外运动: {rain_impact['outdoor_activity']}分")
        print(f"   下雨天所有户外活动: {rain_impact['all_outdoor']}分")
    
    # 测试2.2: 节假日约束
    print("\n🎊 节假日规则:")
    spring_festival = standard_profile_service.check_objective_constraint("holiday_rules", "spring_festival")
    if spring_festival:
        print(f"   春节工作: {spring_festival['work']}分")
        print(f"   春节学习: {spring_festival['study']}分")
    
    # 测试2.3: 时间限制
    print("\n⏰ 时间物理限制:")
    time_limits = standard_profile_service.check_objective_constraint("time_limits")
    if time_limits:
        print(f"   最少睡眠: {time_limits['min_sleep_hours']}小时")
        print(f"   最多连续工作: {time_limits['max_continuous_work']}小时")


def test_personalization_rules():
    """测试个性化调整规则"""
    
    print("\n" + "=" * 70)
    print("🧪 测试3: 个性化参数验证")
    print("=" * 70)
    
    # 测试3.1: 工作时长验证
    print("\n⏱️ 工作时长验证:")
    test_cases = [
        ("workday_hours", 6, "正常"),
        ("workday_hours", 3, "过短"),
        ("workday_hours", 14, "过长"),
    ]
    
    for param, value, desc in test_cases:
        is_valid, message, corrected = standard_profile_service.validate_personalization(param, value)
        status = "✅" if is_valid else "❌"
        print(f"   {status} {param}={value} ({desc}): {message}")
        if not is_valid:
            print(f"      校正值: {corrected}")
    
    # 测试3.2: 时间段偏移验证
    print("\n🕐 时间段偏移验证:")
    shift_cases = [
        ("time_slot_shift", -1, "提前1小时"),
        ("time_slot_shift", -3, "提前3小时（超限）"),
        ("time_slot_shift", 2, "推迟2小时"),
        ("time_slot_shift", 4, "推迟4小时（超限）"),
    ]
    
    for param, value, desc in shift_cases:
        is_valid, message, corrected = standard_profile_service.validate_personalization(param, value)
        status = "✅" if is_valid else "❌"
        print(f"   {status} {desc}: {message}")
        if not is_valid:
            print(f"      校正值: {corrected}")


def test_display_format():
    """测试格式化显示"""
    
    print("\n" + "=" * 70)
    print("🧪 测试4: 格式化显示")
    print("=" * 70)
    
    for user_type in ["student", "worker", "elderly"]:
        print()
        formatted = standard_profile_service.format_schedule_for_display(user_type)
        print(formatted)


def test_default_weights():
    """测试默认权重"""
    
    print("\n" + "=" * 70)
    print("🧪 测试5: 默认评分权重")
    print("=" * 70)
    
    weights = standard_profile_service.get_default_weights()
    print("\n📊 8维度评分权重:")
    total = 0
    for dim, weight in weights.items():
        print(f"   - {dim}: {weight:.0%}")
        total += weight
    
    print(f"\n   总计: {total:.0%} {'✅' if abs(total - 1.0) < 0.01 else '❌'}")


if __name__ == "__main__":
    print("\n开始测试标准作息模板服务...\n")
    
    test_standard_profiles()
    test_objective_constraints()
    test_personalization_rules()
    test_display_format()
    test_default_weights()
    
    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70 + "\n")
