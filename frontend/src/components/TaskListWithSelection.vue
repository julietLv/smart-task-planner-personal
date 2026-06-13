<template>
  <div class="task-list">
    <el-empty v-if="tasks.length === 0" description="暂无任务记录" />

    <div v-else class="task-items">
      <transition-group name="task-slide" tag="div">
        <el-card
          v-for="task in tasks"
          :key="task.id"
          class="task-card"
          shadow="hover"
          :class="{ 'selected': isSelected(task.id) }"
        >
          <div class="task-card-content">
            <el-checkbox
              :model-value="isSelected(task.id)"
              @change="toggleSelect(task.id)"
              class="task-checkbox"
            />

            <div class="task-status-indicator">
              <div
                class="status-dot"
                :style="{ backgroundColor: getStatusColor(task.status) }"
              ></div>
            </div>

            <div class="task-info">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-meta">
                <span v-if="task.start_time" class="meta-item">
                  🕐 {{ formatTime(task.start_time) }}
                </span>
                <span v-if="task.priority" class="meta-item priority-tag" :class="task.priority">
                  {{ getPriorityText(task.priority) }}
                </span>
                <span v-if="task.duration" class="meta-item">
                  ⏱️ {{ task.duration }}分钟
                </span>
              </div>
              <div v-if="task.description" class="task-description">
                {{ task.description }}
              </div>
            </div>

            <div class="task-actions">
              <el-tag
                :type="getStatusType(task.status)"
                size="small"
                effect="plain"
              >
                {{ getStatusText(task.status) }}
              </el-tag>

              <el-dropdown trigger="click" @command="handleAction($event, task)">
                <el-button size="small" text circle>
                  <el-icon><MoreFilled /></el-icon>
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
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { MoreFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()

const props = defineProps({
  tasks: {
    type: Array,
    default: () => []
  },
  selectedTasks: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select', 'refresh'])

function isSelected(taskId) {
  return props.selectedTasks.includes(taskId)
}

function toggleSelect(taskId) {
  emit('select', taskId)
}

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

function getPriorityText(priority) {
  const texts = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return texts[priority] || priority
}

function getStatusText(status) {
  const texts = {
    pending: '待完成',
    done: '已完成',
    cancelled: '已取消',
    overdue: '已超时'
  }
  return texts[status] || status
}

function getStatusType(status) {
  const types = {
    pending: 'warning',
    done: 'success',
    cancelled: 'danger',
    overdue: 'info'
  }
  return types[status] || 'info'
}

function getStatusColor(status) {
  const colors = {
    pending: '#e6a23c',
    done: '#67c23a',
    cancelled: '#f56c6c',
    overdue: '#909399'
  }
  return colors[status] || '#909399'
}

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
      await taskStore.deleteTask(task.id)
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
  gap: 10px;
}

.task-card {
  border: 1.5px solid #ebeef5;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.task-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.12);
  transform: translateY(-2px);
}

.task-card.selected {
  border-color: #f56c6c;
  background: linear-gradient(135deg, #fef0f0 0%, #fff 100%);
  box-shadow: 0 4px 16px rgba(245, 108, 108, 0.15);
}

.task-card :deep(.el-card__body) {
  padding: 14px 16px;
}

.task-card-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-checkbox {
  flex-shrink: 0;
}

.task-checkbox :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

.task-status-indicator {
  flex-shrink: 0;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8);
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
  flex-wrap: wrap;
  align-items: center;
}

.meta-item {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
}

.priority-tag {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.priority-tag.high {
  background: #fef0f0;
  color: #f56c6c;
}

.priority-tag.medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.priority-tag.low {
  background: #f0f9eb;
  color: #67c23a;
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
  margin-top: 4px;
}

.task-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 丝滑的动画效果 */
.task-slide-enter-active,
.task-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.task-slide-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.task-slide-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.task-slide-move {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
