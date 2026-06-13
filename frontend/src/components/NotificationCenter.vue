<template>
  <div class="notification-center">
    <div class="nc-header">
      <span class="nc-title">通知中心</span>
      <div class="nc-actions">
        <el-button text size="small" @click="store.markAllAsRead(1)">全部已读</el-button>
        <el-button text size="small" type="danger" @click="handleClearAll">清空</el-button>
        <el-button text size="small" @click="handleClose">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <div v-if="store.loading" class="nc-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <div class="nc-list" v-else-if="store.notifications.length > 0">
      <div
        v-for="item in store.notifications"
        :key="item.id"
        class="nc-item"
        :class="{
          'is-read': item.read,
          'is-error': item.type === 'error',
          'is-urgent': item.notificationType === 'urgent'
        }"
        @click="store.markAsRead(item.id)"
      >
        <div class="nc-icon" :class="getIconClass(item)">
          <el-icon v-if="item.type === 'error' || item.notificationType === 'urgent'"><CircleCloseFilled /></el-icon>
          <el-icon v-else-if="item.type === 'warning'"><WarningFilled /></el-icon>
          <el-icon v-else><BellFilled /></el-icon>
        </div>
        <div class="nc-content">
          <div class="nc-main">
            <span class="nc-msg-title">{{ item.title }}</span>
            <span class="nc-time">{{ item.time }}</span>
          </div>
          <p class="nc-msg-body">{{ item.message }}</p>
          <div class="nc-footer">
            <div v-if="item.notificationType" class="nc-badge">
              <el-tag v-if="item.notificationType === 'urgent'" size="small" type="danger">紧急</el-tag>
              <el-tag v-else-if="item.notificationType === 'normal'" size="small" type="warning">普通</el-tag>
              <el-tag v-else-if="item.type === 'daily_summary'" size="small" type="success">摘要</el-tag>
              <el-tag v-else size="small" type="info">信息</el-tag>
            </div>
            <el-button
              class="nc-delete-btn-inline"
              text
              size="small"
              type="danger"
              @click.stop="handleDelete(item.id)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无通知" :image-size="80" class="nc-empty" />

  </div>
</template>

<script setup>
import { useNotificationStore } from '../stores/notificationStore'
import { BellFilled, WarningFilled, CircleCloseFilled, Loading, Delete, Close } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { nextTick } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'close'])

const store = useNotificationStore()

function handleClose() {
  emit('update:visible', false)
  emit('close')
}

function getIconClass(item) {
  if (item.type === 'error' || item.notificationType === 'urgent') {
    return 'icon-error'
  } else if (item.type === 'warning') {
    return 'icon-warning'
  }
  return 'icon-info'
}

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定要删除这条通知吗？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await store.deleteNotification(id)

    // ✅ 如果删除后列表为空，延迟重新加载（可能 WebSocket 推送了新通知）
    if (store.notifications.length === 0) {
      await nextTick()
      setTimeout(async () => {
        await store.loadNotifications()
        console.log('✅ 删除后重新加载通知')
      }, 500)
    }
  } catch {
    // 用户取消
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有通知吗？此操作不可恢复。', '提示', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await store.clearAll()
  } catch {
    // 用户取消
  }
}

</script>

<style scoped>
.notification-center {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.nc-header {
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.nc-title {
  font-weight: 600;
  font-size: 16px;
}

.nc-loading {
  padding: 40px;
  text-align: center;
  color: #909399;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.nc-list {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

/* ✅ 空状态样式 */
.nc-empty {
  padding: 40px 0;
  flex: 1;
}

.nc-item {
  padding: 12px 20px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  gap: 12px;
  border-bottom: 1px solid #f5f7fa;
  position: relative;
}

.nc-item:hover {
  background: #f5f7fa;
}

.nc-item.is-read {
  opacity: 0.7;
}

.nc-item.is-error {
  border-left: 3px solid #f56c6c;
  background: #fef0f0;
}

/* ✅ 紧急通知样式 */
.nc-item.is-urgent {
  border-left: 3px solid #f56c6c;
  background: linear-gradient(to right, #fef0f0, #ffffff);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    background: linear-gradient(to right, #fef0f0, #ffffff);
  }
  50% {
    background: linear-gradient(to right, #fde2e2, #ffffff);
  }
}

.nc-icon {
  margin-top: 2px;
}

.nc-icon.icon-warning {
  color: #e6a23c;
}

.nc-icon.icon-error {
  color: #f56c6c;
}

.nc-icon.icon-info {
  color: #409eff;
}

.nc-content {
  flex: 1;
}

.nc-main {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.nc-msg-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.nc-time {
  font-size: 12px;
  color: #909399;
}

.nc-msg-body {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

/* ✅ 通知类型标签 */
.nc-badge {
  margin-top: 6px;
}

/* ✅ 底部操作区 */
.nc-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.nc-delete-btn-inline {
  padding: 4px 8px;
}

/* ✅ 删除按钮悬浮效果 */
.nc-item:hover .nc-delete-btn-inline {
  background-color: #fef0f0;
}
</style>