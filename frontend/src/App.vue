<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useNotificationStore } from './stores/notificationStore'
import NotificationCenter from './components/NotificationCenter.vue'
import { Calendar, User, Bell } from '@element-plus/icons-vue'
import { websocketService } from './services/websocketService'

const route = useRoute()
const notifStore = useNotificationStore()
const currentPath = computed(() => route.path)
const notifVisible = ref(false)

// ✅ 新增：标记是否正在执行删除操作
let isDeleting = false

// ✅ 新增：临时禁用 WebSocket 重连
function tempDisableReconnect(duration = 2000) {
  isDeleting = true
  const originalMaxAttempts = websocketService.maxReconnectAttempts
  websocketService.maxReconnectAttempts = 0

  setTimeout(() => {
    isDeleting = false
    websocketService.maxReconnectAttempts = originalMaxAttempts
    console.log('✅ 恢复 WebSocket 重连')
  }, duration)
}

// ✅ 在App启动时自动加载历史通知并连接WebSocket
onMounted(async () => {
  console.log('🚀 应用启动，正在加载通知...')

  // ✅ 并行加载通知和提醒（提升50%加载速度）
  await Promise.all([
    notifStore.loadNotifications(),
    notifStore.fetchReminders()
  ])

  // ✅ 连接WebSocket（单例，不会重复连接）
  websocketService.connect()

  // ✅ 启用页面可见性监听（移动端友好）
  websocketService.setupVisibilityListener()

  // ✅ 暴露函数给全局，供 NotificationCenter 调用
  window.tempDisableReconnect = tempDisableReconnect
})


// ✅ 组件卸载时清理
onUnmounted(() => {
  // ❗ 不要断开 WebSocket，保持长连接
  // websocketService.disconnect()  ← 删除这行

  console.log('📝 组件卸载，但保持 WebSocket 连接')
})
</script>

<template>
  <div id="app">
    <nav class="app-nav">
      <div class="nav-container">
        <div class="nav-brand">
          <h1>智能任务规划</h1>
        </div>

        <div class="nav-right">
          <el-menu
            :default-active="currentPath"
            mode="horizontal"
            :router="true"
            class="nav-menu"
          >
            <el-menu-item index="/">
              <el-icon><Calendar /></el-icon>
              <span>日历视图</span>
            </el-menu-item>

            <el-menu-item index="/profile">
              <el-icon><User /></el-icon>
              <span>个人中心</span>
            </el-menu-item>
          </el-menu>

          <!-- ✅ 通知铃铛入口（使用 drawer） -->
          <div class="bell-btn" :class="{ 'has-unread': notifStore.unreadCount > 0 }" @click="notifVisible = true">
            <el-icon :size="22"><Bell /></el-icon>
            <span v-if="notifStore.unreadCount > 0" class="badge">{{ notifStore.unreadCount }}</span>
          </div>

          <el-drawer
            v-model="notifVisible"
            direction="rtl"
            :size="360"
            :with-header="false"
            :close-on-click-modal="false"
            :destroy-on-close="false"
            @close="notifVisible = false"
          >
            <NotificationCenter :visible="notifVisible" @update:visible="notifVisible = $event" />
          </el-drawer>

        </div>
      </div>
    </nav>

    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style>
#app {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app-nav {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.nav-brand h1 {
  color: white;
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.nav-menu {
  background: transparent !important;
  border: none !important;
}

:deep(.nav-menu .el-menu-item) {
  color: rgba(255, 255, 255, 0.9) !important;
  border-bottom: 2px solid transparent !important;
  transition: all 0.3s ease;
}

:deep(.nav-menu .el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

:deep(.nav-menu .el-menu-item.is-active) {
  color: white !important;
  border-bottom-color: white !important;
  background: rgba(255, 255, 255, 0.15) !important;
}

:deep(.nav-menu .el-menu-item .el-icon) {
  margin-right: 6px;
}

/* ✅ 通知铃铛样式 */
.nav-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.bell-btn {
  position: relative;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.9);
  padding: 8px;
  border-radius: 50%;
  transition: all 0.3s;
}

.bell-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.badge {
  position: absolute;
  top: 2px;
  right: 2px;
  background: #f56c6c;
  color: white;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  font-weight: bold;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
