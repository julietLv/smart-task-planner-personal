<template>
  <div class="task-input-container">
    <el-card class="input-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title">⚡ 快速添加任务</span>
          <el-tag size="small" type="info">自然语言输入</el-tag>
        </div>
      </template>

      <!-- 输入区域 -->
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="3"
        placeholder="用自然语言描述任务，例如：&#10;• 周三前完成数学作业，预计2小时，优先级高&#10;• 明天下午3点开会&#10;• 本周五之前写完项目报告"
        @input="handleInput"
        @keydown.enter.ctrl="confirmTask"
        :disabled="loading"
        class="task-textarea"
      />

      <!-- 解析结果预览 -->
      <div v-if="parsedResult" class="parse-preview">
        <el-divider content-position="left">
          <span class="preview-title">📋 识别结果</span>
        </el-divider>

        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务标题">
            <el-tag type="primary">{{ parsedResult.title }}</el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="优先级">
            <el-tag :type="getPriorityType(parsedResult.priority)">
              {{ getPriorityText(parsedResult.priority) }}
            </el-tag>
          </el-descriptions-item>

          <el-descriptions-item label="截止时间" v-if="parsedResult.deadline">
            {{ formatDateTime(parsedResult.deadline) }}
          </el-descriptions-item>

          <el-descriptions-item label="预估时长" v-if="parsedResult.duration">
            {{ parsedResult.duration }} 分钟
          </el-descriptions-item>
        </el-descriptions>

        <!-- ⭐ Phase 1: 显示已应用的历史习惯 -->
        <div v-if="appliedHabits && appliedHabits.length > 0" class="applied-habits-section">
          <el-alert
            title="🧠 智能增强"
            type="success"
            :closable="false"
            show-icon
          >
            <template #default>
              <div class="habits-list">
                <p class="habits-title">系统已根据您的历史习惯自动补充：</p>
                <ul class="habits-items">
                  <li v-for="(habit, index) in appliedHabits" :key="index" class="habit-item">
                    {{ habit }}
                  </li>
                </ul>
              </div>
            </template>
          </el-alert>
        </div>

        <!-- ⭐ Phase 2A: 智能排程方案卡片 -->
        <div v-if="scheduleOptions && scheduleOptions.length > 0" class="schedule-options-section">
          <el-divider content-position="left">
            <span class="preview-title">🎯 智能排程方案</span>
          </el-divider>

          <div class="options-container">
            <div 
              v-for="option in scheduleOptions" 
              :key="option.rank"
              class="option-card"
              :class="{ 'recommended': option.is_recommended }"
            >
              <!-- 方案头部 -->
              <div class="option-header">
                <span class="option-icon">{{ option.is_recommended ? '⭐' : '📦' }}</span>
                <span class="option-title">
                  方案 {{ option.rank }} - {{ option.type }}
                </span>
                <el-tag v-if="option.is_recommended" type="warning" size="small">推荐</el-tag>
              </div>

              <!-- 一句话总结 -->
              <p class="option-summary">{{ option.summary }}</p>

              <!-- 核心参数 -->
              <div class="option-details">
                <span class="detail-item">
                  🕒 {{ formatTime(option.task_params.start_time) }} - {{ formatTime(option.task_params.end_time) }}
                </span>
                <span class="detail-item">
                  ⏱️ {{ option.task_params.duration }}分钟
                </span>
                <span class="detail-item option-score" :class="getScoreClass(option.score)">
                  💯 {{ option.score }}分
                </span>
              </div>

              <!-- 优势标签 -->
              <div class="option-tags">
                <el-tag 
                  v-for="adv in option.advantages" 
                  :key="adv" 
                  type="success" 
                  size="small"
                  class="tag-advantage"
                >
                  ✓ {{ adv }}
                </el-tag>
                <el-tag 
                  v-for="dis in option.disadvantages" 
                  :key="dis" 
                  type="warning" 
                  size="small"
                  class="tag-disadvantage"
                >
                  ⚠ {{ dis }}
                </el-tag>
              </div>

              <!-- 操作按钮 -->
              <div class="option-actions">
                <el-button 
                  :type="option.is_recommended ? 'primary' : 'default'"
                  size="small"
                  @click="acceptScheduleOption(option)"
                >
                  {{ option.is_recommended ? '✅ 采纳此方案' : '采纳此方案' }}
                </el-button>
              </div>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="options-footer">
            <el-button size="small" @click="clearScheduleOptions">
              ❌ 取消并手动调整
            </el-button>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button
            type="primary"
            @click="confirmTask"
            :loading="loading"
            :disabled="!parsedResult.title"
          >
            ✅ 确认创建
          </el-button>
          <el-button @click="clearInput">
            🔄 重新输入
          </el-button>
        </div>
      </div>

      <!-- 解析中状态 -->
      <div v-else-if="parsing" class="parsing-state">
        <el-skeleton :rows="3" animated />
      </div>

      <!-- 提示信息 -->
      <div v-else class="hint-text">
        <el-alert
          title="💡 使用提示"
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            <p>输入任务描述后会自动识别关键信息</p>
            <p>按 <strong>Ctrl + Enter</strong> 快速创建</p>
          </template>
        </el-alert>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { taskApi } from '../api/taskApi'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()
const inputText = ref('')
const parsedResult = ref(null)
const appliedHabits = ref([])  // ⭐ Phase 1: 存储应用的习惯
const scheduleOptions = ref([])  // ⭐ Phase 2A: 智能排程方案列表
const parsing = ref(false)
const loading = ref(false)

// 防抖定时器
let parseTimer = null

// 处理输入(防抖)
function handleInput() {
  // 清除之前的定时器
  if (parseTimer) {
    clearTimeout(parseTimer)
  }

  // 如果输入为空,清空解析结果
  if (!inputText.value.trim()) {
    parsedResult.value = null
    return
  }

  // 设置防抖,500ms后调用解析
  parsing.value = true
  parseTimer = setTimeout(async () => {
    await parseTaskText()
  }, 500)
}

// 解析任务文本
async function parseTaskText() {
  if (!inputText.value.trim()) return

  try {
    const response = await taskApi.parseTask(inputText.value)

    if (response.success && response.entities) {
      parsedResult.value = response.entities
      // ⭐ Phase 1: 提取并保存应用的习惯
      appliedHabits.value = response.applied_habits || []
      if (appliedHabits.value.length > 0) {
        console.log('✨ [Phase 1] 应用了以下历史习惯:', appliedHabits.value)
      }
      
      // ⭐ Phase 2A: 提取并保存智能排程方案
      scheduleOptions.value = response.schedule_options || []
      if (scheduleOptions.value.length > 0) {
        console.log('🎯 [Phase 2A] 生成以下智能排程方案:', scheduleOptions.value)
      }
    } else {
      parsedResult.value = null
      appliedHabits.value = []
      scheduleOptions.value = []
      ElMessage.warning('未能识别任务信息,请尝试更清晰的描述')
    }
  } catch (error) {
    console.error('解析失败:', error)
    parsedResult.value = null
    appliedHabits.value = []
    scheduleOptions.value = []
  } finally {
    parsing.value = false
  }
}

// 确认创建任务
async function confirmTask() {
  if (!parsedResult.value || !parsedResult.value.title) {
    ElMessage.warning('请先输入任务描述')
    return
  }

  loading.value = true
  try {
    // 构建任务数据
    const taskData = {
      title: parsedResult.value.title,
      description: '',
      deadline: parsedResult.value.deadline,
      duration: parsedResult.value.duration,
      priority: parsedResult.value.priority || 'medium',
      user_id: 1
    }

    // ⭐ 修复：传递 LLM 解析出的 start_time 和 end_time
    if (parsedResult.value.start_time) {
      taskData.start_time = parsedResult.value.start_time
    }
    if (parsedResult.value.end_time) {
      taskData.end_time = parsedResult.value.end_time
    }

    // 创建任务(后端会自动排程)
    const response = await taskApi.createTask(taskData)

    if (response.success) {
      ElMessage.success('✅ 任务创建成功!')

      // 刷新任务列表（跳过缓存，确保日历立即更新）
      await taskStore.fetchTasks(1, null, true)

      // 清空输入
      clearInput()
    } else {
      ElMessage.error(response.message || '任务创建失败')
    }
  } catch (error) {
    console.error('创建任务失败:', error)
    ElMessage.error('创建任务失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 清空输入
function clearInput() {
  inputText.value = ''
  parsedResult.value = null
  appliedHabits.value = []  // ⭐ Phase 1: 清空习惯列表
  scheduleOptions.value = []  // ⭐ Phase 2A: 清空排程方案
  parsing.value = false
}

// ⭐ Phase 2A: 采纳智能排程方案
async function acceptScheduleOption(option) {
  if (!parsedResult.value || !parsedResult.value.title) {
    ElMessage.warning('请先输入任务描述')
    return
  }

  loading.value = true
  try {
    // 构建任务数据，使用方案中的时间
    const taskData = {
      title: parsedResult.value.title,
      description: '',
      start_time: option.task_params.start_time,
      end_time: option.task_params.end_time,
      deadline: parsedResult.value.deadline,
      duration: option.task_params.duration,
      priority: option.task_params.priority,
      user_id: 1
    }

    // 创建任务
    let response = await taskApi.createTask(taskData)

    // ⭐ 修复：如果后端检测到冲突返回了has_conflict，使用confirm接口处理
    if (response.has_conflict) {
      console.log('⚠️ 后端检测到冲突，使用confirm接口处理...')
      const confirmResponse = await taskApi.confirmTask({
        action: 'auto_adjust',
        task_data: taskData,
        user_id: 1
      })
      response = confirmResponse
    }

    if (response.success) {
      // ⭐ 清除localStorage缓存，确保fetchTasks拿到最新数据
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('tasks_')) {
          localStorage.removeItem(key)
        }
      })

      ElMessage.success('✅ 任务创建成功！')

      // 刷新任务列表（跳过缓存，确保日历立即更新）
      await taskStore.fetchTasks(1, null, true)

      // 清空输入
      clearInput()
    } else {
      ElMessage.error(response.message || '任务创建失败')
    }
  } catch (error) {
    console.error('创建任务失败:', error)
    ElMessage.error('创建任务失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// ⭐ Phase 2A: 清除排程方案
function clearScheduleOptions() {
  scheduleOptions.value = []
  ElMessage.info('已取消智能排程，您可以手动调整时间')
}

// ⭐ Phase 2A: 格式化时间（只显示时分）
function formatTime(datetime) {
  if (!datetime) return '--:--'
  const date = new Date(datetime)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// ⭐ Phase 2A: 根据分数获取样式类
function getScoreClass(score) {
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-medium'
  return 'score-low'
}

// 获取优先级类型
function getPriorityType(priority) {
  const types = {
    high: 'danger',
    medium: 'warning',
    low: 'success'
  }
  return types[priority] || 'info'
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

// 格式化日期时间
function formatDateTime(datetime) {
  if (!datetime) return '无'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}
</script>

<style scoped>
.task-input-container {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.input-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.task-textarea {
  margin-bottom: 10px;
}

.task-textarea :deep(.el-textarea__inner) {
  font-size: 14px;
  line-height: 1.6;
}

.parse-preview {
  margin-top: 15px;
  animation: fadeIn 0.3s ease-in;
}

.preview-title {
  font-size: 14px;
  font-weight: bold;
  color: #606266;
}

.action-buttons {
  margin-top: 15px;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.parsing-state {
  margin-top: 15px;
  padding: 10px;
}

.hint-text {
  margin-top: 15px;
}

.hint-text p {
  margin: 5px 0;
  font-size: 13px;
  color: #606266;
}

/* ⭐ Phase 1: 应用习惯的样式 */
.applied-habits-section {
  margin-top: 15px;
}

.habits-list {
  padding: 5px 0;
}

.habits-title {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #67c23a;
  font-weight: 500;
}

.habits-items {
  margin: 0;
  padding-left: 20px;
  list-style-type: disc;
}

.habit-item {
  font-size: 12px;
  color: #606266;
  line-height: 1.8;
  margin-bottom: 4px;
}

/* ⭐ Phase 2A: 智能排程方案卡片样式 */
.schedule-options-section {
  margin-top: 20px;
  animation: fadeIn 0.4s ease-in;
}

.options-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 15px;
}

.option-card {
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  padding: 15px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
  transition: all 0.3s ease;
  cursor: pointer;
}

.option-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #dcdfe6;
}

.option-card.recommended {
  border-color: #e6a23c;
  background: linear-gradient(135deg, #fdf6ec 0%, #ffffff 100%);
  box-shadow: 0 2px 8px rgba(230, 162, 60, 0.2);
}

.option-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.option-icon {
  font-size: 18px;
}

.option-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.option-summary {
  margin: 8px 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  padding-left: 26px;
}

.option-details {
  display: flex;
  gap: 15px;
  margin: 10px 0;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  font-size: 12px;
}

.detail-item {
  color: #606266;
}

.option-score {
  font-weight: 600;
  margin-left: auto;
}

.option-score.score-high {
  color: #67c23a;
}

.option-score.score-medium {
  color: #e6a23c;
}

.option-score.score-low {
  color: #909399;
}

.option-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 10px 0;
}

.tag-advantage {
  font-size: 11px;
}

.tag-disadvantage {
  font-size: 11px;
}

.option-actions {
  margin-top: 10px;
  text-align: right;
}

.options-footer {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
