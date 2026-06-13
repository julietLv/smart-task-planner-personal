<template>
  <div class="home-container">
    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 左侧：日历视图 (70%) -->
      <div class="left-panel">
        <CalendarView />
      </div>

      <!-- 右侧：天气 + 聊天 + 任务输入 (30%) -->
      <div class="right-panel">
        <!-- 整合的天气任务面板 -->
        <div class="weather-section">
          <WeatherWidget
            @view-tasks="showTaskRecord"
          />
        </div>

        <!-- 任务快速输入 -->
        <div class="task-input-section">
          <TaskInput />
        </div>

        <!-- 聊天窗口 -->
        <div class="chat-section">
          <ChatWindow />
        </div>
      </div>
    </main>

    <!-- ✅ 助手精灵 -->
    <AssistantSprite />

    <!-- 任务记录对话框 -->
    <TaskRecordView ref="taskRecordRef" />

    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="⚙️ 用户偏好设置"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 基本设置标签页 -->
        <el-tab-pane label="基本设置" name="basic">
          <el-form
            ref="settingsFormRef"
            :model="settingsForm"
            label-width="140px"
            v-loading="loading"
          >
            <el-divider content-position="left">🕐 工作时间设置</el-divider>

            <el-form-item label="工作开始时间">
              <el-time-picker
                v-model="settingsForm.work_start_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="工作结束时间">
              <el-time-picker
                v-model="settingsForm.work_end_time"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 100%"
              />
            </el-form-item>

            <el-divider content-position="left">🌙 免安排时段</el-divider>

            <el-form-item label="免安排开始">
              <el-time-picker
                v-model="settingsForm.blocked_time_start"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="免安排结束">
              <el-time-picker
                v-model="settingsForm.blocked_time_end"
                format="HH:mm"
                value-format="HH:mm"
                placeholder="选择时间"
                style="width: 100%"
              />
            </el-form-item>

            <el-divider content-position="left">📋 默认设置</el-divider>

            <el-form-item label="默认任务时长">
              <el-input-number
                v-model="settingsForm.default_task_duration"
                :min="15"
                :max="480"
                :step="15"
                style="width: 100%"
              >
                <template #suffix>分钟</template>
              </el-input-number>
            </el-form-item>

            <el-form-item label="默认优先级">
              <el-select v-model="settingsForm.default_priority" style="width: 100%">
                <el-option label="高优先级" value="high">
                  <span style="color: #f56c6c">● 高优先级</span>
                </el-option>
                <el-option label="中优先级" value="medium">
                  <span style="color: #e6a23c">● 中优先级</span>
                </el-option>
                <el-option label="低优先级" value="low">
                  <span style="color: #67c23a">● 低优先级</span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="通知设置">
              <el-switch
                v-model="settingsForm.notification_enabled"
                active-text="开启通知"
                inactive-text="关闭通知"
              />
            </el-form-item>

            <el-divider />

            <el-form-item label="助手称谓">
              <el-input
                v-model="settingsForm.assistant_nickname"
                placeholder="给你的助手起个名字吧，例如：小智、Jarvis"
                maxlength="20"
                show-word-limit
                clearable
              >
                <template #append>
                  <el-button @click="saveAssistantNickname">保存</el-button>
                </template>
              </el-input>
              <div v-if="currentAssistantNickname" style="margin-top: 8px">
                <el-tag type="success" size="small">当前助手称谓：{{ currentAssistantNickname }}</el-tag>
                <el-button
                  type="danger"
                  size="small"
                  text
                  @click="clearAssistantNickname"
                  style="margin-left: 8px"
                >
                  清除
                </el-button>
              </div>
            </el-form-item>

            <el-form-item label="用户称谓">
              <el-input
                v-model="settingsForm.user_nickname"
                placeholder="助手如何称呼你，例如：主人、老板、小明"
                maxlength="20"
                show-word-limit
                clearable
              >
                <template #append>
                  <el-button @click="saveUserNickname">保存</el-button>
                </template>
              </el-input>
              <div v-if="currentUserNickname" style="margin-top: 8px">
                <el-tag type="primary" size="small">助手会称呼你：{{ currentUserNickname }}</el-tag>
                <el-button
                  type="danger"
                  size="small"
                  text
                  @click="clearUserNickname"
                  style="margin-left: 8px"
                >
                  清除
                </el-button>
              </div>
            </el-form-item>

          </el-form>
        </el-tab-pane>

        <!-- 学习习惯标签页 -->
        <el-tab-pane label="🧠 学习习惯" name="habits">
          <div v-loading="habitsLoading" class="habits-container">
            <div v-if="!habitsData || habitsData.active_habits === 0" class="empty-habits">
              <el-empty description="还没有学习的习惯">
                <template #image>
                  <el-icon :size="80" color="#dcdfe6"><Star /></el-icon>
                </template>
                <p style="color: #909399; margin-top: 10px;">
                  系统会自动学习您的调整习惯<br/>
                  当同一类任务调整达到一定次数后，会自动应用偏好
                </p>
              </el-empty>
            </div>

            <div v-else>
              <div class="habits-summary">
                <el-statistic title="总分类数" :value="habitsData.total_categories" />
                <el-statistic title="活跃习惯" :value="habitsData.active_habits" />
              </div>

              <el-divider>已学习的习惯</el-divider>

              <div v-for="habit in habitsData.learned_habits" :key="habit.keyword" class="habit-card">
                <div class="habit-header">
                  <div class="habit-info">
                    <h4>{{ habit.keyword }}</h4>
                    <el-tag size="small" :type="getConfidenceType(habit.confidence)">
                      置信度: {{ (habit.confidence * 100).toFixed(0) }}%
                    </el-tag>
                  </div>
                  <el-button
                    type="danger"
                    size="small"
                    text
                    @click="handleDeleteHabit(habit.keyword)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>

                <div class="habit-preferences">
                  <div v-for="(value, key) in habit.preferences" :key="key" class="pref-item">
                    <span class="pref-label">{{ getPreferenceLabel(key) }}:</span>
                    <span class="pref-value">{{ getPreferenceValue(key, value) }}</span>
                  </div>
                </div>

                <div class="habit-meta">
                  <span>学习次数: {{ habit.count }}</span>
                  <span v-if="habit.last_used">最后使用: {{ formatDate(habit.last_used) }}</span>
                </div>
              </div>

              <el-divider />

              <div class="habits-actions">
                <el-button type="warning" @click="handleResetHabits" :loading="resettingHabits">
                  <el-icon><Refresh /></el-icon>
                  重置所有习惯
                </el-button>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 自定义关键词标签页 -->
        <el-tab-pane label="🏷️ 自定义关键词" name="keywords">
          <div class="custom-keywords">
            <el-alert
              title="添加自定义关键词映射"
              description="您可以添加特定的词汇到某个分类，让系统更准确地识别任务类型"
              type="info"
              :closable="false"
              show-icon
            />

            <el-form :model="keywordForm" label-width="100px" style="margin-top: 20px">
              <el-form-item label="关键词">
                <el-input
                  v-model="keywordForm.keyword"
                  placeholder="例如: LeetCode、健身房"
                  clearable
                />
              </el-form-item>

              <el-form-item label="分类">
                <el-select v-model="keywordForm.category" placeholder="选择分类" style="width: 100%">
                  <el-option label="运动" value="运动" />
                  <el-option label="学习" value="学习" />
                  <el-option label="工作" value="工作" />
                  <el-option label="生活" value="生活" />
                  <el-option label="创作" value="创作" />
                  <el-option label="社交" value="社交" />
                  <el-option label="健康" value="健康" />
                </el-select>
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="handleAddKeyword" :loading="addingKeyword">
                  添加关键词
                </el-button>
              </el-form-item>
            </el-form>

            <el-divider>已添加的自定义关键词</el-divider>

            <div v-if="customKeywordsList.length === 0" class="empty-keywords">
              <el-empty description="暂无自定义关键词" :image-size="80" />
            </div>

            <el-tag
              v-for="[keyword, category] in customKeywordsList"
              :key="keyword"
              closable
              @close="handleRemoveCustomKeyword(keyword)"
              style="margin: 5px"
            >
              {{ keyword }} → {{ category }}
            </el-tag>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showSettings = false">关闭</el-button>
          <el-button v-if="activeTab === 'basic'" type="primary" @click="saveSettings" :loading="saving">
            保存设置
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Star, Delete, Refresh, Document } from '@element-plus/icons-vue'
import { taskApi, preferenceApi } from '../api/taskApi'
import { useTaskStore } from '../stores/taskStore'
import { useNotificationStore } from '../stores/notificationStore'
import CalendarView from '../components/CalendarView.vue'
import TaskInput from '../components/TaskInput.vue'
import ChatWindow from '../components/ChatWindow.vue'
import TaskRecordView from '../components/TaskRecordView.vue'
import AssistantSprite from '../components/AssistantSprite.vue'
import WeatherWidget from '../components/WeatherWidget.vue'

const taskStore = useTaskStore()
const notifStore = useNotificationStore()
const taskRecordRef = ref(null)
const isWeatherHovered = ref(false)

const showSettings = ref(false)
const activeTab = ref('basic')
const loading = ref(false)
const saving = ref(false)
const settingsFormRef = ref(null)

const habitsLoading = ref(false)
const resettingHabits = ref(false)
const habitsData = ref(null)

const addingKeyword = ref(false)
const keywordForm = ref({
  keyword: '',
  category: ''
})

const settingsForm = ref({
  work_start_time: '09:00',
  work_end_time: '18:00',
  blocked_time_start: '22:00',
  blocked_time_end: '08:00',
  default_task_duration: 60,
  default_priority: 'medium',
  notification_enabled: true,
  assistant_nickname: '',
  user_nickname: ''
})

const userInitial = computed(() => {
  return taskStore.currentUser.name?.charAt(0) || 'U'
})

const customKeywords = computed(() => {
  if (!taskStore.preferences?.remembered_habits) return {}
  return taskStore.preferences.remembered_habits._custom_keywords || {}
})

const customKeywordsList = computed(() => {
  return Object.entries(customKeywords.value)
})

const currentAssistantNickname = computed(() => {
  return taskStore.preferences?.assistant_nickname || ''
})

const currentUserNickname = computed(() => {
  return taskStore.preferences?.user_nickname || ''
})

function showTaskRecord() {
  if (taskRecordRef.value) {
    taskRecordRef.value.open()
  } else {
    console.error('任务记录组件未正确加载')
  }
}

// ✅ 已禁用：统一使用 websocketService 单例，避免重复连接导致 "no close frame received" 错误
// function initWebSocket() {
//   const userId = 1
//   const wsUrl = `ws://localhost:8080/ws/${userId}`

//   try {
//     ws = new WebSocket(wsUrl)

//     ws.onopen = () => {
//       console.log('✅ WebSocket 连接成功')
//       wsConnected.value = true
//       ElMessage.success('实时通知已连接')
//     }

//     ws.onmessage = (event) => {
//       try {
//         const data = JSON.parse(event.data)
//         console.log('📨 收到WebSocket消息:', data.type, data)

//         switch (data.type) {
//           case 'welcome':
//             handleWelcomeMessage(data)
//             break

//           case 'daily_summary':
//             handleDailySummary(data)
//             break

//           case 'deadline_reminder':
//             handleDeadlineReminder(data)
//             break

//           case 'notification':
//             handleNotification(data)
//             break

//           case 'heartbeat_ack':
//             console.log('💓 心跳响应')
//             break

//           default:
//             console.warn('⚠️ 未知消息类型:', data.type)
//         }
//       } catch (error) {
//         console.error('❌ 解析WebSocket消息失败:', error)
//       }
//     }

//     ws.onerror = (error) => {
//       console.error('❌ WebSocket 错误:', error)
//       wsConnected.value = false
//       ElMessage.error('实时通知连接异常')
//     }

//     ws.onclose = () => {
//       console.log('❌ WebSocket 连接关闭')
//       wsConnected.value = false

//       setTimeout(() => {
//         if (!wsConnected.value) {
//           console.log('🔄 尝试重新连接...')
//           initWebSocket()
//         }
//       }, 5000)
//     }
//   } catch (error) {
//     console.error('❌ WebSocket 连接失败:', error)
//     ElMessage.error('实时通知连接失败')
//   }
// }

function handleWelcomeMessage(data) {
  console.log('👋 欢迎消息:', data.data.message)
  if (data.data.available_types) {
    console.log('📋 支持的消息类型:', data.data.available_types.join(', '))
  }
}

function handleDailySummary(data) {
  const summary = data.data

  if (!summary || !summary.success) {
    console.warn('⚠️ 每日摘要生成失败')
    return
  }

  // ✅ 普通通知：推送到通知中心，不弹窗
  notifStore.addNotification({
    type: 'info',
    title: ' 今日日程摘要',
    message: createSummaryNotification(summary)
  })

  console.log(' 每日摘要详情:')
  console.log(summary.summary)

  taskStore.todaySummary = summary
}

function createSummaryNotification(summary) {
  const stats = summary.stats || {}
  const lines = [
    `日期: ${summary.date}`,
    `任务总数: ${stats.total_tasks || 0}`,
    `待完成: ${stats.pending_tasks || 0}`,
    `已完成: ${stats.done_tasks || 0}`,
    `预计工作时长: ${stats.total_duration_minutes || 0}分钟`
  ]

  return lines.join('\n')
}

function handleDeadlineReminder(data) {
  const reminder = data.data

  if (!reminder) {
    return
  }

  // ✅ 紧急通知：保留弹窗提醒
  let notificationType = 'warning'
  let title = '⏰ 任务提醒'

  if (reminder.status === 'overdue') {
    notificationType = 'error'
    title = '⚠️ 任务已过期'
    ElNotification({
      title: title,
      message: reminder.message || formatReminderMessage(reminder),
      type: notificationType,
      duration: 0,
      position: 'bottom-right'
    })
  } else if (reminder.remaining_hours < 1) {
    notificationType = 'warning'
    title = '🚨 紧急提醒'
    ElNotification({
      title: title,
      message: reminder.message || formatReminderMessage(reminder),
      type: notificationType,
      duration: 10000,
      position: 'bottom-right'
    })
  }

  // ✅ 同时存入通知中心
  notifStore.addNotification({
    type: notificationType,
    title: title,
    message: reminder.message || formatReminderMessage(reminder)
  })

  console.log(`⏰ 截止提醒: ${reminder.title} - ${reminder.message}`)
}

function formatReminderMessage(reminder) {
  if (reminder.status === 'overdue') {
    return `任务「${reminder.title}」已过期 ${Math.round(reminder.overdue_hours)} 小时`
  }

  const hours = Math.round(reminder.remaining_hours)
  if (hours < 1) {
    const minutes = Math.round(reminder.remaining_hours * 60)
    return `任务「${reminder.title}」将在 ${minutes} 分钟后到期`
  }

  return `任务「${reminder.title}」将在 ${hours} 小时后到期`
}

function handleNotification(data) {
  const notification = data.data

  // ✅ 普通通知：推送到通知中心，不弹窗
  notifStore.addNotification({
    type: notification.notification_type || data.notification_type || 'info',
    title: notification.title || data.title || '通知',
    message: notification.message || data.message || '您有一条新消息'
  })

  console.log('🔔 通知:', notification.message || data.message)
}

// ✅ 已禁用：统一使用 websocketService 单例
// function sendHeartbeat() {
//   if (ws && ws.readyState === WebSocket.OPEN) {
//     ws.send(JSON.stringify({ type: 'heartbeat' }))
//   }
// }

async function loadSettings() {
  loading.value = true
  try {
    const promises = [taskStore.fetchPreferences()]

    if (activeTab.value === 'habits') {
      promises.push(taskStore.fetchLearnedHabits())
    }

    await Promise.all(promises)

    if (taskStore.preferences) {
      settingsForm.value = {
        work_start_time: taskStore.preferences.work_start_time || '09:00',
        work_end_time: taskStore.preferences.work_end_time || '18:00',
        blocked_time_start: taskStore.preferences.blocked_time_start || '22:00',
        blocked_time_end: taskStore.preferences.blocked_time_end || '08:00',
        default_task_duration: taskStore.preferences.default_task_duration || 60,
        default_priority: taskStore.preferences.default_priority || 'medium',
        notification_enabled: taskStore.preferences.notification_enabled !== false,
        assistant_nickname: taskStore.preferences.assistant_nickname || '',
        user_nickname: taskStore.preferences.user_nickname || ''
      }
    }

    if (activeTab.value === 'habits' && taskStore.learnedHabits) {
      habitsData.value = taskStore.learnedHabits
    }
  } catch (error) {
    console.error('加载偏好设置失败:', error)
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true
  try {
    const updateData = {
      blocked_time_start: settingsForm.value.blocked_time_start,
      blocked_time_end: settingsForm.value.blocked_time_end,
      default_priority: settingsForm.value.default_priority,
      assistant_nickname: settingsForm.value.assistant_nickname,
      user_nickname: settingsForm.value.user_nickname
    }

    await taskStore.updatePreferences(updateData)
    ElMessage.success('✅ 设置已保存')
    showSettings.value = false
  } catch (error) {
    console.error('保存设置失败:', error)
    ElMessage.error('保存设置失败')
  } finally {
    saving.value = false
  }
}

async function loadHabits() {
  habitsLoading.value = true
  try {
    await taskStore.fetchLearnedHabits()
    habitsData.value = taskStore.learnedHabits
  } catch (error) {
    console.error('加载习惯失败:', error)
  } finally {
    habitsLoading.value = false
  }
}

async function handleDeleteHabit(keyword) {
  try {
    await ElMessageBox.confirm(
      `确定要删除"${keyword}"的学习习惯吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await taskStore.deleteHabit(keyword)
    ElMessage.success('已删除习惯')
    await loadHabits()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除习惯失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

async function handleResetHabits() {
  try {
    await ElMessageBox.confirm(
      '确定要重置所有学习习惯吗？此操作不可恢复！',
      '确认重置',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    resettingHabits.value = true
    await taskStore.resetHabits()
    ElMessage.success('已重置所有习惯')
    habitsData.value = null
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置习惯失败:', error)
      ElMessage.error('重置失败')
    }
  } finally {
    resettingHabits.value = false
  }
}

async function saveAssistantNickname() {
  try {
    const nickname = settingsForm.value.assistant_nickname.trim()
    if (!nickname) {
      ElMessage.warning('请输入助手称谓')
      return
    }

    const response = await preferenceApi.setAssistantNickname(nickname)
    ElMessage.success(response.message || '助手称谓已保存')
    await taskStore.fetchPreferences()
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function clearAssistantNickname() {
  try {
    await preferenceApi.setAssistantNickname('')
    settingsForm.value.assistant_nickname = ''
    ElMessage.success('助手称谓已清除')
    await taskStore.fetchPreferences()
  } catch (error) {
    ElMessage.error('清除失败')
  }
}

async function saveUserNickname() {
  try {
    const nickname = settingsForm.value.user_nickname.trim()
    if (!nickname) {
      ElMessage.warning('请输入用户称谓')
      return
    }

    const response = await preferenceApi.setUserNickname(nickname)
    ElMessage.success(response.message || '用户称谓已保存')
    await taskStore.fetchPreferences()
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  }
}

async function clearUserNickname() {
  try {
    await preferenceApi.setUserNickname('')
    settingsForm.value.user_nickname = ''
    ElMessage.success('用户称谓已清除')
    await taskStore.fetchPreferences()
  } catch (error) {
    ElMessage.error('清除失败')
  }
}

async function handleAddKeyword() {
  if (!keywordForm.value.keyword || !keywordForm.value.category) {
    ElMessage.warning('请填写关键词和分类')
    return
  }

  addingKeyword.value = true
  try {
    await taskStore.addCustomKeyword(
      keywordForm.value.keyword,
      keywordForm.value.category
    )
    ElMessage.success('已添加自定义关键词')
    keywordForm.value.keyword = ''
    keywordForm.value.category = ''
    await taskStore.fetchPreferences()
  } catch (error) {
    console.error('添加关键词失败:', error)
    ElMessage.error('添加失败')
  } finally {
    addingKeyword.value = false
  }
}

async function handleRemoveCustomKeyword(keyword) {
  try {
    await ElMessageBox.confirm(
      `确定要删除自定义关键词"${keyword}"吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const habits = taskStore.preferences?.remembered_habits || {}
    if (habits._custom_keywords) {
      delete habits._custom_keywords[keyword]
      await taskStore.updatePreferences({ remembered_habits: habits })
      ElMessage.success('已删除自定义关键词')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除关键词失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

function getConfidenceType(confidence) {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.5) return 'warning'
  return 'info'
}

function getPreferenceLabel(key) {
  const labels = {
    priority: '优先级',
    duration: '时长',
    time_slot: '时间段'
  }
  return labels[key] || key
}

function getPreferenceValue(key, value) {
  if (key === 'priority') {
    const map = { high: '高', medium: '中', low: '低' }
    return map[value] || value
  }
  if (key === 'duration') {
    return `${value}分钟`
  }
  return value
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

watch(showSettings, (newVal) => {
  if (newVal) {
    loadSettings()
    if (activeTab.value === 'habits') {
      loadHabits()
    }
  }
})

watch(activeTab, (newTab) => {
  if (newTab === 'habits' && showSettings.value) {
    loadHabits()
  }
})

onMounted(async () => {
  await loadSettings()

  // ✅ WebSocket 连接已由 App.vue 中的 websocketService 处理，无需重复连接

  // ✅ 启动时检查一次冲突（可选）
  // checkConflicts()
})

onUnmounted(() => {
  // ✅ WebSocket 清理已由 websocketService 处理
})
</script>

<style scoped>
.home-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.top-header {
  height: 60px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-left .app-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 20px;
  padding: 20px;
  overflow: hidden;
}

.left-panel {
  flex: 7;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.right-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  max-height: calc(100vh - 100px);
}

.weather-section {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.task-record-section {
  display: none; /* 隐藏原来的任务记录按钮 */
}

.task-input-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 16px;
}

.chat-section {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.habits-container {
  min-height: 400px;
  max-height: 500px;
  overflow-y: auto;
}

.empty-habits {
  padding: 40px 20px;
  text-align: center;
}

.habits-summary {
  display: flex;
  justify-content: space-around;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.habit-card {
  background: #f9fafb;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  transition: all 0.3s;
}

.habit-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.habit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.habit-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.habit-info h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.habit-preferences {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}

.pref-item {
  display: flex;
  gap: 6px;
  font-size: 14px;
}

.pref-label {
  color: #909399;
}

.pref-value {
  color: #303133;
  font-weight: 500;
}

.habit-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #c0c4cc;
}

.habits-actions {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.custom-keywords {
  padding: 10px;
}

.empty-keywords {
  padding: 30px 0;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>

