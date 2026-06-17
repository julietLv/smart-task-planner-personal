"""
测试 Phase 3: 用户画像管理功能
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.models.task_model import get_user_preferences, update_user_preferences
from app.services.standard_profile_service import standard_profile_service


def test_user_type_field():
    """测试1: user_type 字段是否存在"""
    
    print("\n" + "=" * 70)
    print("测试1: user_type 字段")
    print("=" * 70)
    
    prefs = get_user_preferences(user_id=1)
    
    if prefs:
        print(f"\n✅ 用户偏好记录存在")
        print(f"   user_id: {prefs.user_id}")
        print(f"   user_type: {prefs.user_type}")
        print(f"   user_city: {prefs.user_city}")
    else:
        print("\n❌ 用户偏好记录不存在")


def test_update_user_type():
    """测试2: 更新用户类型"""
    
    print("\n" + "=" * 70)
    print("测试2: 更新用户类型")
    print("=" * 70)
    
    user_id = 1
    
    # 测试2.1: 设置为学生
    print("\n[INFO] 测试2.1: 设置为用户类型为学生")
    prefs = update_user_preferences(user_id, user_type="student")
    print(f"   ✅ 更新成功: user_type={prefs.user_type}")
    
    # 测试2.2: 设置为工作者
    print("\n[INFO] 测试2.2: 设置为用户类型为工作者")
    prefs = update_user_preferences(user_id, user_type="worker")
    print(f"   ✅ 更新成功: user_type={prefs.user_type}")
    
    # 测试2.3: 设置为老年人
    print("\n[INFO] 测试2.3: 设置为用户类型为老年人")
    prefs = update_user_preferences(user_id, user_type="elderly")
    print(f"   ✅ 更新成功: user_type={prefs.user_type}")
    
    # 恢复默认
    update_user_preferences(user_id, user_type="worker")


def test_standard_profiles():
    """测试3: 获取标准作息模板"""
    
    print("\n" + "=" * 70)
    print("测试3: 标准作息模板")
    print("=" * 70)
    
    for profile_type in ["student", "worker", "elderly"]:
        profile = standard_profile_service.get_profile(profile_type)
        
        if profile:
            print(f"\n✅ {profile['name']} 模板:")
            print(f"   描述: {profile['description']}")
            schedule = profile['typical_schedule']
            print(f"   起床时间: {schedule['wake_up']}")
            print(f"   睡觉时间: {schedule['sleep']}")
            print(f"   高效时段: {', '.join(schedule['productive_hours'])}")
            
            capacity = profile['capacity']
            if 'workday_study_hours' in capacity:
                print(f"   工作日学习时长: {capacity['workday_study_hours']}小时")
            elif 'workday_work_hours' in capacity:
                print(f"   工作日工作时长: {capacity['workday_work_hours']}小时")
            else:
                print(f"   每日活动时长: {capacity.get('daily_active_hours', 'N/A')}小时")


def test_personalization_validation():
    """测试4: 个性化参数校验"""
    
    print("\n" + "=" * 70)
    print("测试4: 个性化参数校验")
    print("=" * 70)
    
    # 测试4.1: 工作时长校验
    print("\n[INFO] 测试4.1: 工作时长校验")
    
    test_cases = [
        ("正常值", 8, True),
        ("过短", 2, False),  # 应该校正为4
        ("过长", 15, False),  # 应该校正为12
    ]
    
    for name, value, should_pass in test_cases:
        is_valid, message, corrected_value = standard_profile_service.validate_personalization(
            "workday_hours", value
        )
        
        status = "✅" if is_valid == should_pass else "❌"
        print(f"   {status} {name}: {value}小时")
        print(f"      valid={is_valid}")
        print(f"      message={message}")
        if not is_valid:
            print(f"      corrected_value={corrected_value}")
    
    # 测试4.2: 时间段偏移校验
    print("\n[INFO] 测试4.2: 时间段偏移校验")
    
    offset_cases = [
        ("正常提前", -1, True),
        ("正常推迟", 2, True),
        ("过度提前", -3, False),  # 应该校正为-2
        ("过度推迟", 4, False),  # 应该校正为3
    ]
    
    for name, value, should_pass in offset_cases:
        # ⚠️ 注意：validate_personalization 使用 time_slot_shift 作为参数名
        is_valid, message, corrected_value = standard_profile_service.validate_personalization(
            "time_slot_shift", value
        )
        
        status = "✅" if is_valid == should_pass else "❌"
        print(f"   {status} {name}: {value}小时")
        print(f"      valid={is_valid}")
        print(f"      message={message}")
        if not is_valid:
            print(f"      corrected_value={corrected_value}")


def test_api_endpoints():
    """测试5: API端点（需要启动服务器）"""
    
    print("\n" + "=" * 70)
    print("测试5: API端点检查")
    print("=" * 70)
    
    print("\n📋 新增的API端点:")
    print("   POST /api/preferences/user-type")
    print("      - 设置用户类型 (student/worker/elderly)")
    print("")
    print("   GET  /api/preferences/standard-profiles")
    print("      - 获取所有标准作息模板")
    print("")
    print("   POST /api/preferences/personalization-params")
    print("      - 设置个性化参数（带自动校验）")
    print("         * workday_hours: 工作日时长")
    print("         * preferred_time_slot: 偏好时段")
    print("         * max_continuous_work: 最大连续工作时长")
    print("         * min_break_minutes: 最小休息间隔")
    print("         * time_slot_offset: 时间段偏移")
    
    print("\n💡 提示: 启动后端服务后，可以使用以下命令测试:")
    print("   curl -X POST http://localhost:8000/api/preferences/user-type \\")
    print("        -H 'Content-Type: application/json' \\")
    print("        -d '{\"user_type\": \"student\", \"user_id\": 1}'")


if __name__ == "__main__":
    print("\n开始测试 Phase 3: 用户画像管理...\n")
    
    test_user_type_field()
    test_update_user_type()
    test_standard_profiles()
    test_personalization_validation()
    test_api_endpoints()
    
    print("\n" + "=" * 70)
    print("所有测试完成！")
    print("=" * 70 + "\n")
