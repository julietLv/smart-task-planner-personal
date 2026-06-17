"""
调试脚本：验证前端应该显示的数据
"""
import requests
import json

base_url = "http://localhost:8080"

print("=" * 70)
print("验证前端应该显示的用户画像数据")
print("=" * 70)

# 获取完整的preferences
response = requests.get(f"{base_url}/api/preferences/?user_id=1")
if response.status_code == 200:
    data = response.json()
    prefs = data.get('preferences', {})
    
    print("\n前端应该显示的数据:")
    print(f"  user_type: {prefs.get('user_type', 'MISSING')}")
    print(f"  workday_hours: {prefs.get('workday_hours', 'MISSING')}")
    print(f"  preferred_time_slot: {prefs.get('preferred_time_slot', 'MISSING')}")
    print(f"  time_slot_offset: {prefs.get('time_slot_offset', 'MISSING')}")
    
    # 转换为用户友好的显示文本
    user_type = prefs.get('user_type', 'worker')
    type_names = {
        'student': '学生',
        'worker': '工作者',
        'elderly': '老年人'
    }
    
    print("\n前端应该显示的中文:")
    print(f"  用户类型: {type_names.get(user_type, user_type)}")
    
    # 获取标准作息
    response = requests.get(f"{base_url}/api/preferences/standard-profiles")
    if response.status_code == 200:
        profiles_data = response.json()
        profiles = profiles_data.get('profiles', {})
        if user_type in profiles:
            profile = profiles[user_type]
            print(f"\n标准作息模板（{type_names.get(user_type, user_type)}）:")
            print(f"  典型作息: {profile.get('typical_schedule', {})}")
            print(f"  容量描述: {profile.get('capacity_description', 'N/A')}")
else:
    print(f"请求失败: {response.status_code}")

print("\n" + "=" * 70)
print("前端调试建议:")
print("=" * 70)
print("""
1. 打开浏览器开发者工具（F12）
2. 切换到 Console（控制台）
3. 运行以下代码：

// 检查API数据
fetch('/api/preferences/?user_id=1')
  .then(r => r.json())
  .then(data => {
    console.log('✅ API返回的user_type:', data.preferences.user_type)
    console.log('✅ 完整的preferences:', data.preferences)
  })

// 检查Vue组件数据（如果使用了Vue Devtools）
// 或者检查taskStore
console.log('taskStore.preferences:', window.__VUE_DEVTOOLS_GLOBAL_HOOK__)

4. 如果API返回正确但页面没显示，说明是数据绑定问题
""")
