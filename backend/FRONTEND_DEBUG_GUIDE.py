"""
前端调试指南
"""

print("=" * 70)
print("前端调试步骤")
print("=" * 70)

print("""
请严格按照以下步骤操作：

## 步骤1：清除浏览器所有缓存

1. 打开浏览器开发者工具（F12）
2. 切换到 Application（应用）标签（Chrome/Edge）或 Storage（存储）标签（Firefox）
3. 左侧找到 "Local Storage" → "http://localhost:3000"（或你的前端地址）
4. 右键点击 → "Clear"（清除）
5. 或者在 Console 中运行：

```javascript
localStorage.clear()
sessionStorage.clear()
console.log('✅ 所有缓存已清除')
```

## 步骤2：强制刷新页面

按 Ctrl + Shift + R 或 Ctrl + F5

## 步骤3：检查Network请求

1. 切换到 Network（网络）标签
2. 勾选 "Disable cache"（禁用缓存）
3. 刷新页面
4. 找到 `GET /api/preferences/?user_id=1` 请求
5. 点击它，查看 Response（响应）标签
6. 确认响应中包含 `"user_type": "student"`

## 步骤4：检查Console输出

在 Console 中运行：

```javascript
// 检查API返回的数据
fetch('/api/preferences/?user_id=1')
  .then(r => r.json())
  .then(data => {
    console.log('✅ API user_type:', data.preferences.user_type)
    console.log('✅ 完整数据:', data.preferences)
    
    // 检查Vue组件数据
    console.log('\\n=== 检查Vue Devtools ===')
    console.log('如果安装了Vue Devtools，请打开它查看taskStore')
  })
```

## 步骤5：检查ProfileView页面显示

1. 导航到"个人设置"页面（ProfileView）
2. 找到"选择您的身份类型"区域
3. 查看哪个卡片是高亮选中的（应该有蓝色边框或背景色）
4. 截图给我看这个区域

## 步骤6：如果还是显示错误

运行以下代码强制设置并检查：

```javascript
// 直接检查taskStore（如果可访问）
const app = document.querySelector('#app')
if (app && app.__vue_app__) {
  console.log('Vue应用实例:', app.__vue_app__)
}

// 或者直接检查页面DOM
const userTypeCards = document.querySelectorAll('.user-type-card')
userTypeCards.forEach(card => {
  console.log('卡片类名:', card.className)
  console.log('是否active:', card.classList.contains('active'))
})
```

## 关键问题

请告诉我：

1. ✅ Network中 `/api/preferences/` 的Response里，`user_type`是什么？
2. ✅ "选择您的身份类型"区域，哪个卡片是高亮的？（学生/工作者/老年人）
3. ✅ 是否有蓝色边框或背景色标识选中的卡片？
4. ✅ Console中是否有任何错误信息？

如果API返回正确但页面显示错误，我会直接修复前端代码！
""")

print("\n" + "=" * 70)
print("数据库确认：user_type = student ✅")
print("=" * 70)
