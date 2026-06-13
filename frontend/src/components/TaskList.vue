<template>
  <div class="task-list">
    <el-empty v-if="tasks.length === 0" description="暂无任务记录" />

    <div v-else class="task-items">
      <el-card
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        shadow="hover"
      >
        <div class="task-card-content">
          <!-- 左侧：状态指示 -->
          <div class="task-status-indicator">
            <div
              class="status-dot"
              :class="task.status"
              :style="{ backgroundColor: getStatusColor(task.status) }"
            ></div>
          </div>

          <!-- 中间：任务信息 -->
          <div class="task-info">
            <div class="task-title">{{ task.title }}</div>
            <div class="task-meta">
              <span v-if="task.start_time" class="meta-item">
                🕐 {{ formatTime(task.start_time) }}
              </span>
              <span v-if="task.priority" class="meta-item">
                🎯 {{ getPriorityText(task.priority) }}
              </span>
              <span v-if="task.duration" class="meta-item">
                ⏱️ {{ task.duration }}分钟
              </span>
            </div>
            <div v-if="task.description" class="task-description">
              {{ task.description }}
            </div>
          </div>

          <!-- 右侧：操作按钮 -->
          <div class="task-actions">
            <el-tag
              :type="getStatusType(task.status)"
              size="small"
            >
              {{ getStatusText(task.status) }}
            </el-tag>

            <el-dropdown trigger="click" @command="handleAction($event, task)">
              <el-button size="small" text>
                ⋮
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-if="task.status === 'pending'"
                    command="done"
                  >
                    ✅ 标记完成
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="task.status === 'done'"
                    command="pending"
                  >
                    ↩️ 恢复待完成
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    🗑️ 删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()

defineProps({
  tasks: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['refresh'])

// 格式化时间
function formatTime(datetime) {
  if (!datetime) return ''
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 获取优先级文本
function getPriorityText(priority) {
  const texts = {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级'
  }
  return texts[priority] || priority
}

// 获取状态文本
function getStatusText(status) {
  const texts = {
    pending: '待完成',
    done: '已完成',
    cancelled: '已取消',
    overdue: '已超时'
  }
  return texts[status] || status
}

// 获取状态类型
function getStatusType(status) {
  const types = {
    pending: 'warning',
    done: 'success',
    cancelled: 'danger',
    overdue: 'info'
  }
  return types[status] || 'info'
}

// 获取状态颜色
function getStatusColor(status) {
  const colors = {
    pending: '#e6a23c',
    done: '#67c23a',
    cancelled: '#f56c6c',
    overdue: '#909399'
  }
  return colors[status] || '#909399'
}

// 处理操作
async function handleAction(command, task) {
  if (command === 'done') {
    await taskStore.updateTask(task.id, { status: 'done' })
    ElMessage.success('已标记为完成')
    emit('refresh')
  } else if (command === 'pending') {
    await taskStore.updateTask(task.id, { status: 'pending' })
    ElMessage.success('已恢复为待完成')
    emit('refresh')
  } else if (command === 'delete') {
    try {
      await ElMessageBox.confirm('确定要删除这个任务吗？', '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await taskStore.removeTask(task.id)
      ElMessage.success('任务已删除')
      emit('refresh')
    } catch {
      // 用户取消
    }
  }
}
</script>

<style scoped>
.task-list {
  width: 100%;
}

.task-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-card {
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

.task-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.1);
}

.task-card :deep(.el-card__body) {
  padding: 16px;
}

.task-card-content {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.task-status-indicator {
  flex-shrink: 0;
  padding-top: 4px;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
  line-height: 1.4;
}

.task-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 13px;
  color: #606266;
}

.task-description {
  font-size: 13px;
  color: #909399;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.task-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}
</style>
