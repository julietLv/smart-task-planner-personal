"""
直接测试数据库更新操作
"""
import sys
sys.path.insert(0, 'D:/demo_plan/backend')

from app.models.task_model import get_user_preferences, update_user_preferences

print("=" * 70)
print("直接测试数据库更新")
print("=" * 70)

# 1. 查询当前值
print("\n1. 查询当前user_type...")
prefs = get_user_preferences(user_id=1)
print(f"   当前 user_type: {prefs.user_type}")

# 2. 更新为student
print("\n2. 更新user_type为student...")
try:
    updated_prefs = update_user_preferences(1, user_type="student")
    print(f"   更新后 user_type: {updated_prefs.user_type}")
    print("   ✅ 更新成功！")
except Exception as e:
    print(f"   ❌ 更新失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 再次查询确认
print("\n3. 再次查询确认...")
prefs = get_user_preferences(user_id=1)
print(f"   数据库中 user_type: {prefs.user_type}")

# 4. 测试设置回worker
print("\n4. 测试设置回worker...")
try:
    updated_prefs = update_user_preferences(1, user_type="worker")
    print(f"   更新后 user_type: {updated_prefs.user_type}")
    print("   ✅ 更新成功！")
except Exception as e:
    print(f"   ❌ 更新失败: {e}")

# 5. 最终查询
print("\n5. 最终查询...")
prefs = get_user_preferences(user_id=1)
print(f"   数据库中 user_type: {prefs.user_type}")

print("\n" + "=" * 70)
print("如果上面的更新都成功了，说明数据库操作没问题")
print("问题可能出在前端API调用或后端路由处理上")
print("=" * 70)
