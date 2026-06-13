// D:\demo_plan\frontend\debug_notification.js
// 通知中心调试脚本

console.log('🔍 开始调试通知中心...')

// 1. 检查 el-popover 的状态
function checkPopoverState() {
  const popover = document.querySelector('.el-popper')
  if (popover) {
    console.log(' el-popover 存在')
    console.log('   - visible 类:', popover.classList.contains('is-visible'))
    console.log('   - display 样式:', getComputedStyle(popover).display)
    console.log('   - opacity 样式:', getComputedStyle(popover).opacity)
  } else {
    console.log('❌ 找不到 el-popover 元素')
  }
}

// 2. 监听删除操作
function monitorDelete() {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList' || mutation.type === 'attributes') {
        const target = mutation.target
        if (target.classList && target.classList.contains('el-popper')) {
          console.log('🔄 el-popover 状态变化:', {
            visible: target.classList.contains('is-visible'),
            display: getComputedStyle(target).display,
            timestamp: new Date().toISOString()
          })
        }
      }
    })
  })

  // 观察整个 body 的变化
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class', 'style']
  })

  console.log('✅ 已开始监听 DOM 变化')
  return observer
}

// 3. 测试删除功能
async function testDelete() {
  console.log('🧪 开始测试删除功能...')

  // 打开通知中心
  const bellBtn = document.querySelector('.bell-btn')
  if (bellBtn) {
    bellBtn.click()
    console.log('✅ 点击了通知铃铛')

    // 等待 popover 显示
    await new Promise(resolve => setTimeout(resolve, 500))

    // 检查状态
    checkPopoverState()

    // 查找删除按钮
    const deleteBtn = document.querySelector('.nc-delete-btn-inline')
    if (deleteBtn) {
      console.log('✅ 找到删除按钮，准备点击...')

      // 监听删除后的变化
      const observer = monitorDelete()

      // 点击删除
      deleteBtn.click()

      // 等待确认对话框
      await new Promise(resolve => setTimeout(resolve, 1000))

      // 点击确认
      const confirmBtn = document.querySelector('.el-message-box__btns .el-button--primary')
      if (confirmBtn) {
        confirmBtn.click()
        console.log('✅ 点击了确认删除')

        // 等待删除完成
        await new Promise(resolve => setTimeout(resolve, 2000))

        // 最终检查状态
        console.log('📊 最终状态检查:')
        checkPopoverState()

        // 停止监听
        observer.disconnect()
      }
    } else {
      console.log('❌ 未找到删除按钮')
    }
  } else {
    console.log('❌ 未找到通知铃铛')
  }
}

// 导出测试函数
window.debugNotification = {
  checkPopoverState,
  monitorDelete,
  testDelete
}

console.log(' 调试工具已加载，运行 window.debugNotification.testDelete() 开始测试')
