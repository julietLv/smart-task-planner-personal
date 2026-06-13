<template>
  <div class="profile-container">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <span>加载中...</span>
    </div>

    <!-- 用户信息卡片固定顶部 -->
    <el-card class="user-card" shadow="hover">
      <div class="user-header">
        <div class="user-avatar-section">
          <el-upload
            class="avatar-uploader"
            :show-file-list="false"
            :before-upload="beforeAvatarUpload"
            :http-request="handleAvatarUpload"
          >
            <el-avatar :size="80" class="user-avatar" :src="avatarUrl">
              <span v-if="!avatarUrl">{{ userNickname.charAt(0) }}</span>
            </el-avatar>
            <div class="avatar-overlay">
              <el-icon :size="20"><Upload /></el-icon>
              <span>更换头像</span>
            </div>
          </el-upload>
        </div>

        <div class="user-info">
          <h2>{{ userNickname }}</h2>
          <p class="user-subtitle" v-if="usageDays > 0">
            <el-icon><Clock /></el-icon>
            已使用 {{ usageDays }} 天
          </p>
          <p class="user-subtitle" v-else>
            <el-icon><Clock /></el-icon>
            欢迎使用智能任务规划
          </p>

          <div class="user-city">
            <el-icon><Location /></el-icon>
            <span>{{ userCity }}</span>
            <el-button
              type="primary"
              size="small"
              text
              @click="showCitySelector = true"
              class="change-city-link"
            >
              切换城市
            </el-button>
          </div>
        </div>

        <div class="quick-stats">
          <div class="stat-item">
            <el-icon :size="20" color="#409eff"><CircleCheck /></el-icon>
            <div class="stat-content">
              <div class="stat-value">{{ stats.completedTasks }}</div>
              <div class="stat-label">已完成任务</div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 主内容区整体滚动卡片自适应高度 -->
    <div class="main-content">
      <!-- 左侧栏 -->
      <div class="left-column">
        <!-- 学到的习惯 -->
        <el-card class="habits-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">
                <el-icon><MagicStick /></el-icon>
                学到的习惯
              </span>
              <el-button
                type="danger"
                size="small"
                :disabled="!habits.length"
                @click="handleResetAllHabits"
              >
                重置全部
              </el-button>
            </div>
          </template>

          <el-empty
            v-if="!habits.length"
            description="系统还没有学习到你的习惯哦"
            :image-size="100"
          >
            <template #description>
              <p style="font-size: 13px;">多使用几次任务管理系统会自动学习你的偏好</p>
            </template>
          </el-empty>

          <div v-else class="habits-pagination-wrapper">
            <div class="habits-list-container">
              <transition name="slide" mode="out-in">
                <div :key="currentPage" class="habits-page">
                  <div
                    v-for="habit in paginatedHabits"
                    :key="habit.keyword"
                    class="habit-item"
                  >
                    <div class="habit-main">
                      <div class="habit-header">
                        <el-tag :type="getHabitType(habit)" effect="dark">
                          {{ habit.keyword }}
                        </el-tag>
                        <el-tag
                          v-if="habit.learned"
                          type="success"
                          size="small"
                        >
                          已学习
                        </el-tag>
                      </div>

                      <p class="habit-description">{{ habit.description }}</p>

                      <div class="habit-confidence">
                        <span class="confidence-label">置信度</span>
                        <el-progress
                          :percentage="Math.round(habit.confidence * 100)"
                          :color="getConfidenceColor(habit.confidence)"
                          :stroke-width="6"
                          style="flex: 1; margin: 0 12px;"
                          :show-text="false"
                        />
                        <span class="confidence-value">{{ Math.round(habit.confidence * 100) }}%</span>
                      </div>

                      <div class="habit-meta">
                        <span>调整 {{ habit.count }} 次</span>
                        <span v-if="habit.last_used"> 最后使用{{ formatDate(habit.last_used) }}</span>
                      </div>
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
                </div>
              </transition>
            </div>

            <div class="habits-pagination">
              <div class="pagination-info">
                <span class="info-text">
                  共 {{ habits.length }} 个习惯{{ totalPages }} 页
                </span>
                <span class="current-page-indicator">
                  第 {{ currentPage }} / {{ totalPages }} 页
                </span>
              </div>

              <div class="pagination-controls">
                <el-button
                  :disabled="currentPage === 1"
                  @click="handlePrevPage"
                  size="small"
                  circle
                >
                  <el-icon><ArrowLeft /></el-icon>
                </el-button>

                <div class="page-dots">
                  <span
                    v-for="page in totalPages"
                    :key="page"
                    class="page-dot"
                    :class="{ active: page === currentPage }"
                    @click="handleGoToPage(page)"
                  />
                </div>

                <el-button
                  :disabled="currentPage === totalPages"
                  @click="handleNextPage"
                  size="small"
                  circle
                >
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 自定义关键词 -->
        <el-card class="custom-keywords-card" shadow="hover">
          <template #header>
            <span class="card-title">
              <el-icon><PriceTag /></el-icon>
              自定义关键词
            </span>
          </template>

          <el-alert
            title="添加自定义关键词映射"
            description="让系统更准确地识别你的任务类型"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 16px;"
          />

          <el-form :model="keywordForm" label-width="80px" class="keyword-form">
            <el-form-item label="关键词">
              <el-input
                v-model="keywordForm.keyword"
                placeholder="例如: LeetCode健身房"
                clearable
                @keyup.enter="handleAddKeyword"
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
                <el-icon><Plus /></el-icon>
                添加关键词
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider v-if="customKeywordsList.length > 0">已添加的关键词</el-divider>

          <el-empty
            v-if="customKeywordsList.length === 0"
            description="暂无自定义关键词"
            :image-size="60"
          />

          <div v-else class="keywords-list">
            <el-tag
              v-for="[keyword, category] in customKeywordsList"
              :key="keyword"
              closable
              @close="handleRemoveKeyword(keyword)"
              type="info"
              effect="plain"
              style="margin: 4px;"
            >
              {{ keyword }}  {{ category }}
            </el-tag>
          </div>
        </el-card>

        <!-- 数据管理 -->
        <el-card class="data-card" shadow="hover">
          <template #header>
            <span class="card-title">
              <el-icon><FolderOpened /></el-icon>
              数据管理
            </span>
          </template>

          <div class="data-actions">
            <el-button type="primary" @click="handleExportData">
              <el-icon><Download /></el-icon>
              导出数据
            </el-button>

            <el-popconfirm
              title="确定要清除所有数据吗此操作不可恢复"
              confirm-button-text="确定清除"
              cancel-button-text="取消"
              icon-color="#f56c6c"
              @confirm="handleClearAllData"
            >
              <template #reference>
                <el-button type="danger">
                  <el-icon><Delete /></el-icon>
                  清除数据
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-card>
      </div>

      <!-- 右侧栏 -->
      <div class="right-column">
        <!-- 偏好设置 -->
        <el-card class="preferences-card" shadow="hover">
          <template #header>
            <span class="card-title">
              <el-icon><Setting /></el-icon>
              偏好设置
            </span>
          </template>

          <el-form
            :model="preferences"
            label-width="120px"
            class="preferences-form"
          >
            <el-form-item label="工作时间">
              <el-time-picker
                v-model="preferences.work_hours"
                is-range
                format="HH:mm"
                value-format="HH:mm"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="免打扰时段">
              <el-time-picker
                v-model="preferences.blocked_hours"
                is-range
                format="HH:mm"
                value-format="HH:mm"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="任务缓冲时间">
              <el-slider
                v-model="preferences.buffer_minutes"
                :min="0"
                :max="60"
                :step="5"
                show-input
              />
              <div class="form-tip">任务之间的缓冲时间避免安排过紧</div>
            </el-form-item>

            <el-form-item label="默认任务时长">
              <el-input-number
                v-model="preferences.default_duration"
                :min="15"
                :max="480"
                :step="15"
                style="width: 100%"
              />
              <span class="form-unit">分钟</span>
            </el-form-item>

            <el-form-item label="通知提醒">
              <el-switch
                v-model="preferences.notification_enabled"
                active-text="开启"
                inactive-text="关闭"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                @click="handleSavePreferences"
                :loading="saving"
              >
                <el-icon><Check /></el-icon>
                保存设置
              </el-button>
              <el-button @click="handleResetPreferences">
                恢复默认
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 个性化设置 -->
        <el-card class="personalization-card" shadow="hover">
          <template #header>
            <span class="card-title">
              <el-icon><Brush /></el-icon>
              个性化设置
            </span>
          </template>

          <el-form label-width="120px">
            <el-form-item label="助手昵称">
              <el-input
                v-model="personalization.assistant_name"
                placeholder="给助手起个名字"
                maxlength="20"
                show-word-limit
              />
            </el-form-item>

            <el-form-item label="你的昵称">
              <el-input
                v-model="personalization.user_nickname"
                placeholder="你希望怎么称呼你"
                maxlength="20"
                show-word-limit
              />
            </el-form-item>

            <el-form-item label="主题色">
              <div class="theme-colors">
                <div
                  v-for="color in themeColors"
                  :key="color.value"
                  class="color-option"
                  :class="{ active: personalization.theme_color === color.value }"
                  :style="{ backgroundColor: color.hex }"
                  @click="personalization.theme_color = color.value"
                >
                  <el-icon v-if="personalization.theme_color === color.value" color="white" :size="16">
                    <Check />
                  </el-icon>
                </div>
              </div>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                @click="handleSavePersonalization"
                :loading="saving"
              >
                保存设置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- ⭐ Phase 3: 用户画像设置 -->
        <el-card class="user-profile-card" shadow="hover">
          <template #header>
            <span class="card-title">
              <el-icon><User /></el-icon>
              用户画像
            </span>
          </template>

          <!-- 用户类型选择 -->
          <div class="user-type-section">
            <h4 class="section-title">选择您的身份类型</h4>
            <div class="user-type-cards">
              <div
                v-for="type in userTypes"
                :key="type.value"
                class="user-type-card"
                :class="{ active: userProfile.user_type === type.value }"
                @click="selectUserType(type.value)"
              >
                <div class="type-icon">{{ type.icon }}</div>
                <div class="type-name">{{ type.name }}</div>
                <div class="type-desc">{{ type.description }}</div>
              </div>
            </div>
          </div>

          <el-divider />

          <!-- 标准作息对比 -->
          <div class="schedule-comparison">
            <h4 class="section-title">标准作息参考</h4>
            <div v-if="selectedProfile" class="profile-detail">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="起床时间">
                  {{ selectedProfile.typical_schedule.wake_up }}
                </el-descriptions-item>
                <el-descriptions-item label="睡觉时间">
                  {{ selectedProfile.typical_schedule.sleep }}
                </el-descriptions-item>
                <el-descriptions-item label="高效时段" :span="2">
                  {{ selectedProfile.typical_schedule.productive_hours.join('、') }}
                </el-descriptions-item>
                <el-descriptions-item label="容量" :span="2">
                  {{ getCapacityText(selectedProfile) }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </div>

          <el-divider />

          <!-- 个性化参数 -->
          <div class="personal-params-section">
            <h4 class="section-title">个性化调整</h4>
            <el-form :model="personalParams" label-width="120px" size="small">
              <el-form-item label="工作日时长">
                <el-slider
                  v-model="personalParams.workday_hours"
                  :min="4"
                  :max="12"
                  :step="0.5"
                  show-input
                  @change="validateWorkdayHours"
                />
                <div class="param-tip">建议范围：4-12小时</div>
              </el-form-item>

              <el-form-item label="偏好时段">
                <el-select v-model="personalParams.preferred_time_slot" style="width: 100%">
                  <el-option label="早晨 (6-9点)" value="morning" />
                  <el-option label="上午 (9-12点)" value="noon" />
                  <el-option label="下午 (14-18点)" value="afternoon" />
                  <el-option label="晚上 (18-22点)" value="evening" />
                  <el-option label="深夜 (22-24点)" value="night" />
                </el-select>
              </el-form-item>

              <el-form-item label="时间段偏移">
                <el-slider
                  v-model="personalParams.time_slot_offset"
                  :min="-2"
                  :max="3"
                  :step="1"
                  show-input
                />
                <div class="param-tip">提前或推迟高效时段（-2~+3小时）</div>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  @click="saveUserProfile"
                  :loading="savingProfile"
                >
                  保存画像设置
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 城市选择器对话框 -->
    <el-dialog
      v-model="showCitySelector"
      title="选择城市"
      width="400px"
      teleport="body"
      class="city-selector-dialog"
    >
      <div class="selector-content">
        <el-input
          v-model="searchCity"
          placeholder="搜索城市..."
          prefix-icon="Search"
          clearable
          class="city-search-input"
        />

        <div class="city-list">
          <div
            v-for="cityItem in filteredCities"
            :key="cityItem"
            class="city-option"
            :class="{ 'is-current': cityItem === userCity }"
            @click="selectCity(cityItem)"
          >
            <span class="option-icon">{{ cityItem === userCity ? '' : '' }}</span>
            <span class="option-text">{{ cityItem }}</span>
            <el-tag v-if="cityItem === userCity" type="primary" size="small">当前</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Loading, Edit, Clock, CircleCheck, Timer, Trophy,
  MagicStick, Setting, Brush, FolderOpened, Download,
  Delete, Check, Upload, PriceTag, Plus, ArrowLeft, ArrowRight, Location, User
} from '@element-plus/icons-vue'
import { getUserCity, updateUserCity } from '@/api/weatherApi'

const taskStore = useTaskStore()
const loading = ref(false)
const saving = ref(false)

// 用户信息从后端或 Store 获取
const userNickname = ref('')
const joinDate = ref(null)

// 统计数据
const stats = ref({
  completedTasks: 0,
  focusHours: 0,
  streakDays: 0
})

// 学到的习惯
const habits = ref([])

// 分页相关状态
const currentPage = ref(1)
const pageSize = 5

const totalPages = computed(() => Math.ceil(habits.value.length / pageSize))

const paginatedHabits = computed(() => {
  const sortedHabits = [...habits.value].sort((a, b) => {
    if (!a.last_used) return 1
    if (!b.last_used) return -1
    return new Date(b.last_used) - new Date(a.last_used)
  })
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return sortedHabits.slice(start, end)
})

function handleNextPage() {
  if (currentPage.value < totalPages.value) currentPage.value++
}

function handlePrevPage() {
  if (currentPage.value > 1) currentPage.value--
}

function handleGoToPage(page) {
  currentPage.value = page
}

// 自定义关键词
const addingKeyword = ref(false)
const keywordForm = ref({ keyword: '', category: '' })

const customKeywordsList = computed(() => {
  if (!taskStore.preferences?.remembered_habits) return []
  const customKeywords = taskStore.preferences.remembered_habits._custom_keywords || {}
  return Object.entries(customKeywords)
})

// 偏好设置
const preferences = ref({
  work_hours: ['09:00', '18:00'],
  blocked_hours: ['22:00', '08:00'],
  buffer_minutes: 15,
  default_duration: 60,
  notification_enabled: true
})

// 个性化设置
const personalization = ref({
  assistant_name: '',
  user_nickname: '',
  theme_color: 'purple'
})

const themeColors = [
  { value: 'blue', hex: '#409eff' },
  { value: 'purple', hex: '#764ba2' },
  { value: 'green', hex: '#67c23a' },
  { value: 'orange', hex: '#e6a23c' },
  { value: 'red', hex: '#f56c6c' }
]

const avatarUrl = ref('')
const userCity = ref('北京')
const showCitySelector = ref(false)
const searchCity = ref('')
const commonCities = [
  '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安',
  '南京', '重庆', '天津', '苏州', '长沙', '郑州', '东莞', '青岛',
  '宁波', '昆明', '厦门', '福州', '合肥', '济南', '哈尔滨', '沈阳'
]

// ⭐ Phase 3: 用户画像相关
const savingProfile = ref(false)
const standardProfiles = ref({})
const userProfile = ref({
  user_type: 'worker',
  workday_hours: 8,
  preferred_time_slot: 'morning',
  time_slot_offset: 0
})

const userTypes = [
  { value: 'student', name: '学生', icon: '🎓', description: '注重学习效率和课程安排' },
  { value: 'worker', name: '工作者', icon: '💼', description: '注重工作效率和会议安排' },
  { value: 'elderly', name: '老年人', icon: '🌅', description: '注重健康和生活节奏' }
]

const selectedProfile = computed(() => {
  return standardProfiles.value[userProfile.value.user_type] || null
})

const filteredCities = computed(() => {
  if (!searchCity.value) return commonCities
  return commonCities.filter(c => c.includes(searchCity.value))
})

const usageDays = computed(() => {
  if (!joinDate.value) return 0
  const now = new Date()
  const diff = now - new Date(joinDate.value)
  return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)))
})

function getHabitType(habit) {
  if (habit.learned) return 'success'
  if (habit.confidence > 0.7) return 'warning'
  return 'info'
}

function getConfidenceColor(confidence) {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.5) return '#e6a23c'
  return '#f56c6c'
}

function formatDate(dateStr) {
  if (!dateStr) return '未知'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    // ⭐ 并行加载所有数据，减少等待时间
    const [habitsResponse, prefsResponse] = await Promise.all([
      taskStore.fetchLearnedHabits(),
      taskStore.fetchPreferences()
    ])

    if (habitsResponse && taskStore.learnedHabits) {
      habits.value = parseHabits(taskStore.learnedHabits)
    }

    if (prefsResponse && taskStore.preferences) {
      const prefs = taskStore.preferences
      preferences.value = {
        work_hours: [prefs.work_start_time || '09:00', prefs.work_end_time || '18:00'],
        blocked_hours: [prefs.blocked_time_start || '22:00', prefs.blocked_time_end || '08:00'],
        buffer_minutes: prefs.task_buffer_minutes || 15,
        default_duration: prefs.default_task_duration || 60,
        notification_enabled: prefs.notification_enabled !== false
      }
      personalization.value = {
        assistant_name: prefs.assistant_nickname || '',
        user_nickname: prefs.user_nickname || '',
        theme_color: 'purple'
      }
      userNickname.value = prefs.user_nickname || '用户'
      
      // ⭐ Phase 3: 加载用户画像数据（优先使用localStorage，保证刷新后状态一致）
      const savedUserType = localStorage.getItem('user_profile_type')
      if (savedUserType) {
        // 如果localStorage有值，优先使用，并同步到后端
        userProfile.value.user_type = savedUserType
        console.log(' 从 localStorage 恢复用户类型:', savedUserType)
      } else if (prefs.user_type) {
        userProfile.value.user_type = prefs.user_type
      }
      
      const savedWorkdayHours = localStorage.getItem('user_profile_workday_hours')
      if (savedWorkdayHours) {
        userProfile.value.workday_hours = parseFloat(savedWorkdayHours)
      } else if (prefs.workday_hours) {
        userProfile.value.workday_hours = prefs.workday_hours
      }
      
      const savedPreferredTimeSlot = localStorage.getItem('user_profile_preferred_time_slot')
      if (savedPreferredTimeSlot) {
        userProfile.value.preferred_time_slot = savedPreferredTimeSlot
      } else if (prefs.preferred_time_slot) {
        userProfile.value.preferred_time_slot = prefs.preferred_time_slot
      }
      
      const savedTimeSlotOffset = localStorage.getItem('user_profile_time_slot_offset')
      if (savedTimeSlotOffset !== null) {
        userProfile.value.time_slot_offset = parseInt(savedTimeSlotOffset)
      } else if (prefs.time_slot_offset !== undefined) {
        userProfile.value.time_slot_offset = prefs.time_slot_offset
      }
    }
    calculateStats()
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function parseHabits(habitsData) {
  if (!habitsData) return []
  const habitsList = habitsData.learned_habits || []
  if (!Array.isArray(habitsList)) return []
  return habitsList.map(habit => ({
    keyword: habit.keyword || '未知习惯',
    count: habit.count || 0,
    learned: habit.learned || false,
    confidence: habit.confidence || 0.5,
    description: generateHabitDescription(habit.keyword, habit),
    last_used: habit.last_used,
    preferred_priority: habit.preferences?.priority,
    preferred_duration: habit.preferences?.duration
  }))
}

function generateHabitDescription(keyword, data) {
  const parts = []
  if (data.preferred_priority || data.preferences?.priority) {
    const priority = data.preferred_priority || data.preferences.priority
    const priorityMap = { high: '高', medium: '中', low: '低' }
    parts.push(`偏好${priorityMap[priority] || priority}优先级`)
  }
  if (data.preferred_duration || data.preferences?.duration) {
    parts.push(`偏好时长${data.preferred_duration || data.preferences.duration}分钟`)
  }
  return parts.length > 0 ? parts.join('') : `已调整 ${data.count || 0} 次`
}

function calculateStats() {
  stats.value.completedTasks = taskStore.tasks.filter(t => t.status === 'done').length
  stats.value.focusHours = 0
  stats.value.streakDays = 0
}

async function handleSavePreferences() {
  saving.value = true
  try {
    const data = {
      work_start_time: preferences.value.work_hours[0],
      work_end_time: preferences.value.work_hours[1],
      blocked_time_start: preferences.value.blocked_hours[0],
      blocked_time_end: preferences.value.blocked_hours[1],
      task_buffer_minutes: preferences.value.buffer_minutes,
      default_task_duration: preferences.value.default_duration,
      notification_enabled: preferences.value.notification_enabled
    }
    await taskStore.updatePreferences(data)

    // ⭐ 清除缓存，下次强制刷新
    taskStore.invalidateCache('preferences')

    ElMessage.success('偏好设置已保存')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

function handleResetPreferences() {
  preferences.value = {
    work_hours: ['09:00', '18:00'],
    blocked_hours: ['22:00', '08:00'],
    buffer_minutes: 15,
    default_duration: 60,
    notification_enabled: true
  }
  ElMessage.info('已恢复默认设置')
}

async function handleDeleteHabit(keyword) {
  try {
    await ElMessageBox.confirm(`确定要忘记关于"${keyword}"的习惯吗`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await taskStore.deleteHabit(keyword)
    habits.value = habits.value.filter(h => h.keyword !== keyword)

    // ⭐ 清除习惯缓存
    taskStore.invalidateCache('habits')

    ElMessage.success('已删除该习惯')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handleResetAllHabits() {
  try {
    await ElMessageBox.confirm('确定要重置所有学习习惯吗此操作不可恢复', '危险操作', {
      confirmButtonText: '确定重置',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await taskStore.resetHabits()
    habits.value = []

    // ⭐ 清除习惯缓存
    taskStore.invalidateCache('habits')

    ElMessage.success('已重置所有习惯')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('重置失败')
  }
}

async function handleAddKeyword() {
  if (!keywordForm.value.keyword || !keywordForm.value.category) {
    ElMessage.warning('请填写关键词和分类')
    return
  }
  addingKeyword.value = true
  try {
    const response = await taskStore.addCustomKeyword(keywordForm.value.keyword, keywordForm.value.category)
    if (response.success) {
      ElMessage.success(`已添加关键词: ${keywordForm.value.keyword}  ${keywordForm.value.category}`)
      keywordForm.value = { keyword: '', category: '' }
      await taskStore.fetchPreferences()

      // ⭐ 清除偏好缓存
      taskStore.invalidateCache('preferences')
    } else {
      ElMessage.error('添加失败')
    }
  } catch (error) {
    console.error('添加关键词失败:', error)
    ElMessage.error('添加失败: ' + error.message)
  } finally {
    addingKeyword.value = false
  }
}

async function handleRemoveKeyword(keyword) {
  try {
    await ElMessageBox.confirm(`确定要删除关键词"${keyword}"吗`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    const response = await fetch(`/api/preferences/keywords/${encodeURIComponent(keyword)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: 1 })
    })
    if (response.ok) {
      ElMessage.success(`已删除关键词: ${keyword}`)
      await taskStore.fetchPreferences()
    } else {
      ElMessage.error('删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

watch(() => personalization.value.theme_color, (newColor) => {
  applyThemeColor(newColor)
})

function applyThemeColor(color) {
  const colorMap = {
    blue: 'linear-gradient(135deg, #409eff 0%, #66b1ff 100%)',
    purple: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    green: 'linear-gradient(135deg, #67c23a 0%, #85ce61 100%)',
    orange: 'linear-gradient(135deg, #e6a23c 0%, #f0b04e 100%)',
    red: 'linear-gradient(135deg, #f56c6c 0%, #f89898 100%)'
  }
  const gradient = colorMap[color] || colorMap.purple
  const nav = document.querySelector('.app-nav')
  const userCard = document.querySelector('.user-card')
  if (nav) nav.style.background = gradient
  if (userCard) userCard.style.background = gradient
  localStorage.setItem('theme_color', color)
}

function beforeAvatarUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isImage) ElMessage.error('只能上传图片文件!')
  if (!isLt2M) ElMessage.error('图片大小不能超过 2MB!')
  return isImage && isLt2M
}

function handleAvatarUpload(options) {
  const { file } = options
  const reader = new FileReader()
  reader.onload = (e) => {
    avatarUrl.value = e.target.result
    localStorage.setItem('user_avatar', e.target.result)
    ElMessage.success('头像已更新')
  }
  reader.readAsDataURL(file)
}

async function handleSavePersonalization() {
  saving.value = true
  try {
    await taskStore.updatePreferences({
      assistant_nickname: personalization.value.assistant_name,
      user_nickname: personalization.value.user_nickname
    })
    userNickname.value = personalization.value.user_nickname || '用户'

    // ⭐ 清除偏好缓存
    taskStore.invalidateCache('preferences')

    ElMessage.success('个性化设置已保存')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

async function loadUserCity() {
  try {
    const response = await getUserCity()
    if (response.data.success) {
      userCity.value = response.data.city
      localStorage.setItem('user_city', response.data.city)
    }
  } catch (error) {
    const savedCity = localStorage.getItem('user_city')
    if (savedCity) userCity.value = savedCity
  }
}

async function selectCity(newCity) {
  try {
    await updateUserCity(1, newCity)
    userCity.value = newCity
    localStorage.setItem('user_city', newCity)
    showCitySelector.value = false
    ElMessage.success(`已切换到${newCity}`)
    window.dispatchEvent(new CustomEvent('city-changed', { detail: { city: newCity } }))
  } catch (error) {
    console.error('切换城市失败:', error)
    ElMessage.error('切换城市失败')
  }
}

function handleExportData() {
  const data = {
    preferences: preferences.value,
    habits: habits.value,
    personalization: personalization.value,
    exportDate: new Date().toISOString()
  }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `my-profile-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('数据已导出')
}

async function handleClearAllData() {
  try {
    ElMessage.warning('数据清除功能开发中')
  } catch (error) {
    ElMessage.error('清除失败')
  }
}

// ⭐ Phase 3: 用户画像相关方法
const personalParams = computed({
  get: () => userProfile.value,
  set: (val) => { userProfile.value = val }
})

function getCapacityText(profile) {
  if (!profile) return ''
  const capacity = profile.capacity
  if (capacity.workday_study_hours) {
    return `工作日学习${capacity.workday_study_hours}小时`
  } else if (capacity.workday_work_hours) {
    return `工作日工作${capacity.workday_work_hours}小时`
  } else if (capacity.daily_active_hours) {
    return `每日活动${capacity.daily_active_hours}小时`
  }
  return ''
}

async function selectUserType(type) {
  userProfile.value.user_type = type
  // 自动加载对应类型的默认参数
  const profile = standardProfiles.value[type]
  if (profile) {
    const capacity = profile.capacity
    if (capacity.workday_study_hours) {
      userProfile.value.workday_hours = capacity.workday_study_hours
    } else if (capacity.workday_work_hours) {
      userProfile.value.workday_hours = capacity.workday_work_hours
    } else if (capacity.daily_active_hours) {
      userProfile.value.workday_hours = capacity.daily_active_hours
    }
  }
}

function validateWorkdayHours(value) {
  if (value < 4) {
    ElMessage.warning('工作时长不能少于4小时，已自动校正')
    userProfile.value.workday_hours = 4
  } else if (value > 12) {
    ElMessage.warning('工作时长不能超过12小时，已自动校正')
    userProfile.value.workday_hours = 12
  }
}

async function loadStandardProfiles() {
  try {
    const response = await fetch('/api/preferences/standard-profiles')
    const data = await response.json()
    if (data.success) {
      standardProfiles.value = data.profiles
    }
  } catch (error) {
    console.error('加载标准模板失败:', error)
  }
}

async function saveUserProfile() {
  savingProfile.value = true
  try {
    // 1. 保存用户类型到后端
    const typeResponse = await fetch('/api/preferences/user-type', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_type: userProfile.value.user_type,
        user_id: 1
      })
    })
    
    if (!typeResponse.ok) {
      throw new Error('设置用户类型失败')
    }

    // 2. 保存个性化参数到后端
    const paramsResponse = await fetch('/api/preferences/personalization-params', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workday_hours: userProfile.value.workday_hours,
        preferred_time_slot: userProfile.value.preferred_time_slot,
        time_slot_offset: userProfile.value.time_slot_offset,
        user_id: 1
      })
    })

    const paramsData = await paramsResponse.json()
    
    if (paramsData.validation_errors && paramsData.validation_errors.length > 0) {
      // 有校正信息，显示提示
      paramsData.validation_errors.forEach(err => {
        ElMessage.warning(`${err.param}: ${err.error}，已校正为${err.corrected_value}`)
      })
    }

    // 3. ⭐ 成功后保存到localStorage（确保刷新后能恢复）
    localStorage.setItem('user_profile_type', userProfile.value.user_type)
    localStorage.setItem('user_profile_workday_hours', userProfile.value.workday_hours.toString())
    localStorage.setItem('user_profile_preferred_time_slot', userProfile.value.preferred_time_slot)
    localStorage.setItem('user_profile_time_slot_offset', userProfile.value.time_slot_offset.toString())
    
    console.log(' 用户画像已保存到 localStorage:', {
      type: userProfile.value.user_type,
      workday_hours: userProfile.value.workday_hours,
      preferred_time_slot: userProfile.value.preferred_time_slot,
      time_slot_offset: userProfile.value.time_slot_offset
    })

    ElMessage.success('用户画像设置已保存')
  } catch (error) {
    console.error('保存用户画像失败:', error)
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    savingProfile.value = false
  }
}

onMounted(() => {
  //  优先从本地缓存恢复UI，让用户立即看到内容
  const savedTheme = localStorage.getItem('theme_color')
  if (savedTheme) {
    personalization.value.theme_color = savedTheme
    applyThemeColor(savedTheme)
  }
  const savedAvatar = localStorage.getItem('user_avatar')
  if (savedAvatar) avatarUrl.value = savedAvatar

  const savedCity = localStorage.getItem('user_city')
  if (savedCity) userCity.value = savedCity

  // ⭐ Phase 3: 从localStorage恢复用户画像设置（立即恢复，让用户看到最新状态）
  const savedUserType = localStorage.getItem('user_profile_type')
  if (savedUserType) {
    userProfile.value.user_type = savedUserType
    console.log(' 立即从 localStorage 恢复用户类型:', savedUserType)
  }
  const savedWorkdayHours = localStorage.getItem('user_profile_workday_hours')
  if (savedWorkdayHours) {
    userProfile.value.workday_hours = parseFloat(savedWorkdayHours)
  }
  const savedPreferredTimeSlot = localStorage.getItem('user_profile_preferred_time_slot')
  if (savedPreferredTimeSlot) {
    userProfile.value.preferred_time_slot = savedPreferredTimeSlot
  }
  const savedTimeSlotOffset = localStorage.getItem('user_profile_time_slot_offset')
  if (savedTimeSlotOffset !== null) {
    userProfile.value.time_slot_offset = parseInt(savedTimeSlotOffset)
  }

  //  异步加载数据，不阻塞页面渲染
  loadData().then(() => {
    // 数据加载完成后刷新城市信息（如果后端有更新）
    loadUserCity()
  })
  
  // ⭐ Phase 3: 加载标准作息模板
  loadStandardProfiles()
})
</script>

<style scoped>
.profile-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  z-index: 1000;
  font-size: 16px;
  color: #606266;
}

.user-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  flex-shrink: 0;
}

.user-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-avatar-section {
  flex-shrink: 0;
}

.avatar-uploader {
  position: relative;
  cursor: pointer;
  display: inline-block;
}

.avatar-uploader :deep(.el-upload) {
  border: none;
  border-radius: 50%;
  overflow: hidden;
  transition: all 0.3s;
}

.avatar-uploader:hover .avatar-overlay {
  opacity: 1;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s;
  border-radius: 50%;
  gap: 4px;
  font-size: 12px;
}

.user-avatar {
  border: 3px solid rgba(255, 255, 255, 0.3);
}

.user-info {
  flex: 1;
}

.user-info h2 {
  margin: 0 0 6px 0;
  font-size: 24px;
  font-weight: 600;
}

.user-subtitle {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0.9;
  font-size: 14px;
}

.user-city {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
  font-size: 13px;
  backdrop-filter: blur(10px);
  width: fit-content;
}

.change-city-link {
  color: white;
  font-size: 12px;
  padding: 0;
  margin-left: 4px;
}

.change-city-link:hover {
  color: #ffd700;
}

.selector-content {
  padding: 10px 0;
}

.city-search-input {
  margin-bottom: 16px;
}

.city-list {
  max-height: 400px;
  overflow-y: auto;
}

.city-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.city-option:hover {
  background: #f5f7fa;
}

.city-option.is-current {
  background: #ecf5ff;
  border: 1px solid #409eff;
}

.option-icon {
  font-size: 18px;
}

.option-text {
  flex: 1;
  font-size: 15px;
  color: #333;
}

.quick-stats {
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  backdrop-filter: blur(10px);
  min-width: 120px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
  margin-top: 3px;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.left-column,
.right-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: visible;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.habits-pagination-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.habits-list-container {
  position: relative;
  min-height: 350px;
  overflow: hidden;
}

.habits-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.slide-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}

.slide-reverse-enter-from {
  transform: translateX(-100%);
  opacity: 0;
}

.slide-reverse-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.habits-pagination {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid #e4e7ed;
}

.pagination-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-text {
  font-size: 13px;
  color: #909399;
}

.current-page-indicator {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.page-dots {
  display: flex;
  gap: 8px;
}

.page-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dcdfe6;
  cursor: pointer;
  transition: all 0.3s ease;
}

.page-dot:hover {
  background: #c0c4cc;
  transform: scale(1.2);
}

.page-dot.active {
  background: #409eff;
  width: 24px;
  border-radius: 4px;
}

.habit-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.habit-item:hover {
  background: #e8ebf0;
  transform: translateX(3px);
}

.habit-main {
  flex: 1;
}

.habit-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.habit-description {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 13px;
}

.habit-confidence {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.confidence-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.confidence-value {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  min-width: 36px;
}

.habit-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

.keyword-form {
  margin-bottom: 16px;
}

.keywords-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
}

.keywords-list :deep(.el-tag) {
  transition: all 0.3s ease;
}

.keywords-list :deep(.el-tag:hover) {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.preferences-form {
  max-width: 100%;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.form-unit {
  margin-left: 8px;
  color: #606266;
}

.theme-colors {
  display: flex;
  gap: 10px;
}

.color-option {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  border: 3px solid transparent;
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.active {
  border-color: #303133;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
}

.data-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* ⭐ Phase 3: 用户画像卡片样式 */
.user-profile-card {
  margin-top: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}

.user-type-section {
  margin-bottom: 20px;
}

.user-type-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.user-type-card {
  padding: 16px;
  border: 2px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
  background: white;
}

.user-type-card:hover {
  border-color: #409eff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}

.user-type-card.active {
  border-color: #409eff;
  background: linear-gradient(135deg, #ecf5ff 0%, #f0f9ff 100%);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.type-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.type-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.type-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.schedule-comparison {
  margin-bottom: 20px;
}

.profile-detail {
  margin-top: 12px;
}

.personal-params-section {
  margin-bottom: 0;
}

.param-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
  }
  .quick-stats {
    display: none;
  }
  .user-type-cards {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .profile-container {
    padding: 12px;
    gap: 12px;
  }
  .user-header {
    flex-direction: column;
    text-align: center;
  }
  .preferences-form {
    label-width: 100px !important;
  }
}

.profile-container::-webkit-scrollbar {
  width: 8px;
}
.profile-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}
.profile-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}
.profile-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>