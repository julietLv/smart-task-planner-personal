<template>
  <div class="calendar-container" :class="{ 'is-loading': taskStore.loading }">
    <!-- ✅ 骨架屏 - 替换简单loading -->
    <div v-if="taskStore.loading" class="skeleton-overlay">
      <div class="skeleton-calendar">
        <div class="skeleton-header">
          <SkeletonLoader width="120px" height="32px" />
          <SkeletonLoader width="200px" height="32px" />
          <SkeletonLoader width="120px" height="32px" />
        </div>
        <div class="skeleton-grid">
          <div v-for="i in 35" :key="i" class="skeleton-day">
            <SkeletonLoader width="30px" height="20px" />
          </div>
        </div>
      </div>
    </div>

    <FullCalendar
      ref="calendarRef"
      :options="calendarOptions"
    />

    <!-- ✅ 空状态引导 -->
    <div v-if="taskStore.tasks.length === 0 && !taskStore.loading" class="empty-state">
      <div class="empty-content">
        <el-icon :size="80" color="#c0c4cc"><Calendar /></el-icon>
        <h3>还没有任务哦</h3>
        <p class="empty-hint">点击日历上的日期或时间段，快速添加你的第一个任务</p>
        <el-button
          type="primary"
          size="large"
          @click="handleAddFirstTask"
          class="add-first-task-btn"
        >
          <el-icon style="margin-right: 8px"><Plus /></el-icon>
          添加第一个任务
        </el-button>
      </div>
    </div>

    <!-- 任务详情/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'edit' ? '编辑任务' : '任务详情'"
      width="500px"
      @close="resetForm"
      class="task-dialog"
      :close-on-click-modal="false"
      transition="dialog-bounce"
    >
      <el-form
        v-if="dialogMode === 'edit'"
        ref="formRef"
        :model="taskForm"
        :rules="formRules"
        label-width="100px"
        :scroll-to-error="true"
        class="task-form"
      >
        <el-form-item label="任务标题" prop="title">
          <el-input
            v-model="taskForm.title"
            placeholder="请输入任务标题"
            clearable
            prefix-icon="Document"
          />
        </el-form-item>

        <el-form-item label="任务描述">
          <el-input
            v-model="taskForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入任务描述"
          />
        </el-form-item>

        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker
            v-model="taskForm.start_time"
            type="datetime"
            placeholder="选择开始时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
            :disabled-date="disabledDate"
          />
        </el-form-item>

        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker
            v-model="taskForm.end_time"
            type="datetime"
            placeholder="选择结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="截止时间">
          <el-date-picker
            v-model="taskForm.deadline"
            type="datetime"
            placeholder="选择截止时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
          <div class="deadline-quick-options">
            <el-button 
              size="small" 
              @click="setDeadline('18:00')"
              :type="taskForm.deadline?.includes('18:00') ? 'primary' : ''"
            >
              18:00下班前
            </el-button>
            <el-button 
              size="small" 
              @click="setDeadline('21:00')"
              :type="taskForm.deadline?.includes('21:00') ? 'primary' : ''"
            >
              21:00晚间
            </el-button>
            <el-button 
              size="small" 
              @click="setDeadline('23:59')"
              :type="taskForm.deadline?.includes('23:59') ? 'primary' : ''"
            >
              23:59当日结束
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="优先级" prop="priority">
          <el-select v-model="taskForm.priority" placeholder="选择优先级" style="width: 100%">
            <el-option label="高优先级" value="high">
              <span class="priority-option">
                <el-icon><WarningFilled /></el-icon>
                <span style="color: #f56c6c">高优先级</span>
              </span>
            </el-option>
            <el-option label="中优先级" value="medium">
              <span class="priority-option">
                <el-icon><InfoFilled /></el-icon>
                <span style="color: #e6a23c">中优先级</span>
              </span>
            </el-option>
            <el-option label="低优先级" value="low">
              <span class="priority-option">
                <el-icon><CircleCheckFilled /></el-icon>
                <span style="color: #67c23a">低优先级</span>
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select v-model="taskForm.status" placeholder="选择状态" style="width: 100%">
            <el-option label="待完成" value="pending" />
            <el-option label="已完成" value="done" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="selectedTask && dialogMode === 'view'" class="task-detail" :class="{ 'is-deleting': isDeleting }">
        <h3>{{ selectedTask.title }}</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="描述">
            {{ selectedTask.description || '无' }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(selectedTask.start_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="结束时间">
            {{ formatDateTime(selectedTask.end_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="截止时间">
            {{ selectedTask.deadline ? formatDateTime(selectedTask.deadline) : '无' }}
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="getPriorityType(selectedTask.priority)" effect="dark">
              <el-icon style="margin-right: 4px">
                <component :is="getPriorityIcon(selectedTask.priority)" />
              </el-icon>
              {{ getPriorityText(selectedTask.priority) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedTask.status)" effect="plain">
              {{ getStatusText(selectedTask.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button
            v-if="dialogMode === 'view'"
            type="primary"
            @click="switchToEdit"
          >
            编辑
          </el-button>
          <el-button
            v-if="dialogMode === 'view'"
            type="danger"
            :loading="isDeleting"
            @click="handleDelete"
          >
            删除
          </el-button>
          <el-button
            v-if="dialogMode === 'edit'"
            type="primary"
            @click="handleSubmit"
            :loading="taskStore.loading"
          >
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'

import SkeletonLoader from './SkeletonLoader.vue'

import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { useTaskStore } from '../stores/taskStore'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled, InfoFilled, CircleCheckFilled, Loading, Calendar, Plus } from '@element-plus/icons-vue'
import axios from 'axios'
import { cacheMonitor } from '../utils/cacheMonitor'

const taskStore = useTaskStore()
const calendarRef = ref(null)
const dialogVisible = ref(false)
const dialogMode = ref('view')
const selectedTask = ref(null)
const formRef = ref(null)
const isDeleting = ref(false)
const monthHolidays = ref({})

// ✅ 前端缓存配置
const holidayCache = new Map()  // 内存缓存（最快）
const CACHE_EXPIRY = 30 * 24 * 60 * 60 * 1000  // 30天过期（节日数据很稳定）

// ✅ 缓存统计（开发环境用）
const cacheStats = {
  memoryHit: 0,
  localStorageHit: 0,
  serverRequest: 0
}

// 初始化时从 LocalStorage 恢复缓存
function initHolidayCache() {
  try {
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
      if (key.startsWith('holiday_cache_')) {
        const monthKey = key.replace('holiday_cache_', '')
        const cached = localStorage.getItem(key)
        if (cached) {
          const { data, timestamp } = JSON.parse(cached)
          // 检查是否过期
          if (Date.now() - timestamp < CACHE_EXPIRY) {
            holidayCache.set(monthKey, data)
            console.log('💾 恢复缓存:', monthKey)
          } else {
            localStorage.removeItem(key)
            console.log('🗑️ 清除过期缓存:', monthKey)
          }
        }
      }
    })
    console.log('✅ 缓存初始化完成，已加载', holidayCache.size, '个月份')
  } catch (error) {
    console.error('❌ 恢复节日缓存失败:', error)
  }
}

// 保存到 LocalStorage
function saveToLocalStorage(cacheKey, data) {
  try {
    localStorage.setItem(
      `holiday_cache_${cacheKey}`,
      JSON.stringify({
        data,
        timestamp: Date.now()
      })
    )
  } catch (error) {
    console.error('❌ 保存节日缓存失败:', error)
  }
}

// 表单数据
const taskForm = ref({
  title: '',
  description: '',
  start_time: '',
  end_time: '',
  deadline: null,
  priority: 'medium',
  status: 'pending'
})

// ✅ 禁用过去日期
function disabledDate(time) {
  return time.getTime() < Date.now() - 86400000
}

// 表单验证规则
const formRules = {
  title: [
    { required: true, message: '请输入任务标题', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ],
  start_time: [
    { required: true, message: '请选择开始时间', trigger: 'change' }
  ],
  end_time: [
    { required: true, message: '请选择结束时间', trigger: 'change' }
  ],
  priority: [
    { required: true, message: '请选择优先级', trigger: 'change' }
  ]
}

async function loadMonthHolidays(year, month) {
  const cacheKey = `${year}-${month}`
  const requestStart = Date.now()

  // ✅ 第1级：检查内存缓存（<1ms）
  if (holidayCache.has(cacheKey)) {
    cacheMonitor.recordMemoryHit()
    console.log(`⚡ 内存缓存命中:`, cacheKey)
    monthHolidays.value = holidayCache.get(cacheKey)
    return
  }

  // ✅ 第2级：检查 LocalStorage（~5ms）
  try {
    const localData = localStorage.getItem(`holiday_cache_${cacheKey}`)
    if (localData) {
      const { data, timestamp } = JSON.parse(localData)
      if (Date.now() - timestamp < CACHE_EXPIRY) {
        cacheMonitor.recordLocalStorageHit()
        console.log(`💾 LocalStorage命中:`, cacheKey)

        // 加载到内存缓存
        holidayCache.set(cacheKey, data)
        monthHolidays.value = data
        return
      } else {
        // 过期了，删除
        localStorage.removeItem(`holiday_cache_${cacheKey}`)
      }
    }
  } catch (error) {
    console.error('读取 LocalStorage 失败:', error)
  }

  // ✅ 第3级：从服务器请求（~200ms）
  console.log(`🌐 服务器请求:`, cacheKey)

  try {
    const response = await axios.get('/api/holidays/month', {
      params: { year, month }
    })

    const responseTime = Date.now() - requestStart
    cacheMonitor.recordServerRequest(responseTime)

    const holidayMap = {}
    response.data.holidays.forEach(h => {
      holidayMap[h.date] = h
    })

    // ✅ 存入内存缓存
    holidayCache.set(cacheKey, holidayMap)

    // ✅ 存入 LocalStorage
    saveToLocalStorage(cacheKey, holidayMap)

    monthHolidays.value = holidayMap

    console.log('✅ 加载节日信息:', year, '年', month, '月 -', response.data.count, '个', `(${responseTime}ms)`)

    // ✅ 预加载相邻月份（后台异步，不阻塞当前渲染）
    preloadAdjacentMonths(year, month)
  } catch (error) {
    cacheMonitor.recordError()
    console.error('❌ 加载节日信息失败:', error)
    ElMessage.warning('加载节日信息失败，请刷新页面重试')
  }
}

// ✅ 预加载相邻月份
function preloadAdjacentMonths(year, month) {
  const prevMonth = month === 1 ? 12 : month - 1
  const prevYear = month === 1 ? year - 1 : year

  const nextMonth = month === 12 ? 1 : month + 1
  const nextYear = month === 12 ? year + 1 : year

  console.log('🔄 预加载相邻月份:', `${prevYear}-${prevMonth}`, `${nextYear}-${nextMonth}`)

  // 后台异步加载，不影响当前操作
  Promise.all([
    loadMonthHolidays(prevYear, prevMonth)
      .then(() => cacheMonitor.recordPreload(true))
      .catch(() => cacheMonitor.recordPreload(false)),
    loadMonthHolidays(nextYear, nextMonth)
      .then(() => cacheMonitor.recordPreload(true))
      .catch(() => cacheMonitor.recordPreload(false))
  ])
}

function getHolidayInfo(dateStr) {
  return monthHolidays.value[dateStr] || null
}

// ✅ 日历配置 - 移除 events，改为手动管理
const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'timeGridWeek',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay'
  },
  locale: 'zh-cn',
  editable: true,
  selectable: true,
  selectMirror: true,
  dayMaxEvents: true,
  weekends: true,
  eventDisplay: 'block',
  slotMinTime: '06:00:00',
  slotMaxTime: '23:00:00',

  // ✅ 自定义日期单元格内容（显示节日）
  dayCellContent: (arg) => {
    const dateStr = arg.date.toISOString().split('T')[0]
    const holiday = getHolidayInfo(dateStr)

    if (holiday) {
      return {
        html: `
          <div class="custom-day-cell">
            <span class="day-number">${arg.dayNumberText.replace('日', '')}</span>
            <span class="holiday-badge ${holiday.is_legal_holiday ? 'is-legal' : ''}">
              ${holiday.name}
            </span>
          </div>
        `
      }
    }

    return { html: `<div class="custom-day-cell"><span class="day-number">${arg.dayNumberText.replace('日', '')}</span></div>` }
  },

  // ✅ 监听日期变化，重新加载节日数据
  datesSet: async (dateInfo) => {
    const startYear = dateInfo.start.getFullYear()
    const startMonth = dateInfo.start.getMonth() + 1

    const endYear = dateInfo.end.getFullYear()
    const endMonth = dateInfo.end.getMonth() + 1

    // ✅ 如果跨越了多个月，加载两个月的数据
    if (startYear === endYear && startMonth === endMonth) {
      // 单月视图
      await loadMonthHolidays(startYear, startMonth)
    } else {
      // 跨月视图（如周视图跨越月底）
      await Promise.all([
        loadMonthHolidays(startYear, startMonth),
        loadMonthHolidays(endYear, endMonth)
      ])
    }
  },

  // 点击日期添加任务
  dateClick: (info) => {
    handleDateClick(info)
  },

  // 点击任务查看详情
  eventClick: (info) => {
    handleEventClick(info)
  },

  // ✅ 拖拽调整时间（带冲突检测和回滚机制）
  eventDrop: (info) => {
    handleEventDrop(info)
  },

  // ✅ 调整时长（带冲突检测和回滚机制）
  eventResize: (info) => {
    handleEventResize(info)
  }
}))

// 获取优先级颜色
function getPriorityColor(priority) {
  const colors = {
    high: '#f56c6c',
    medium: '#e6a23c',
    low: '#67c23a'
  }
  return colors[priority] || colors.medium
}

// ✅ 获取优先级图标
function getPriorityIcon(priority) {
  const icons = {
    high: WarningFilled,
    medium: InfoFilled,
    low: CircleCheckFilled
  }
  return icons[priority] || InfoFilled
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

// 获取状态类型
function getStatusType(status) {
  const types = {
    pending: 'info',
    done: 'success',
    cancelled: 'danger',
    overdue: 'warning'
  }
  return types[status] || 'info'
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

// 格式化日期时间
function formatDateTime(datetime) {
  if (!datetime) return '无'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 设置快捷截止时间
function setDeadline(timeStr) {
  // 如果已经有日期，只更新时间；否则使用今天
  let baseDate
  if (taskForm.value.deadline) {
    baseDate = new Date(taskForm.value.deadline)
  } else {
    baseDate = new Date()
  }
  
  const [hours, minutes] = timeStr.split(':')
  baseDate.setHours(parseInt(hours), parseInt(minutes), 0, 0)
  
  taskForm.value.deadline = baseDate.toISOString().slice(0, 19)
}

// ✅ 添加第一个任务的快捷方法
function handleAddFirstTask() {
  const now = new Date()
  const startDate = new Date(now.getTime() + 60 * 60 * 1000) // 1小时后
  const endDate = new Date(startDate.getTime() + 60 * 60 * 1000) // 2小时后

  taskForm.value = {
    title: '',
    description: '',
    start_time: startDate.toISOString().slice(0, 19),
    end_time: endDate.toISOString().slice(0, 19),
    deadline: null,
    priority: 'medium',
    status: 'pending'
  }

  dialogMode.value = 'edit'
  selectedTask.value = null
  dialogVisible.value = true
}

// 点击日期
function handleDateClick(info) {
  dialogMode.value = 'edit'
  selectedTask.value = null

  const startDate = new Date(info.dateStr)
  const endDate = new Date(startDate.getTime() + 60 * 60 * 1000)

  taskForm.value = {
    title: '',
    description: '',
    start_time: startDate.toISOString().slice(0, 19),
    end_time: endDate.toISOString().slice(0, 19),
    deadline: null,
    priority: 'medium',
    status: 'pending'
  }

  dialogVisible.value = true
}

// 点击任务事件
function handleEventClick(info) {
  const taskId = parseInt(info.event.id)
  selectedTask.value = taskStore.getTaskById(taskId)

  if (selectedTask.value) {
    dialogMode.value = 'view'
    dialogVisible.value = true
  }
}

// ✅ 拖拽事件 - 增强版（加入微交互）
async function handleEventDrop(info) {
  const taskId = parseInt(info.event.id)
  const newStart = info.event.start
  const newEnd = info.event.end || new Date(newStart.getTime() + 60 * 60 * 1000)

  const formatDateTime = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`
  }

  try {
    const response = await taskStore.updateTask(taskId, {
      start_time: formatDateTime(newStart),
      end_time: formatDateTime(newEnd)
    })

    if (response && response.has_conflict) {
      // ✅ 冲突时触发抖动动画
      info.event.setProp('classNames', ['shake-animation'])
      setTimeout(() => info.event.setProp('classNames', []), 1000)

      let conflictDetails = ''
      if (response.conflicts && response.conflicts.length > 0) {
        conflictDetails = '\n\n' + response.conflicts.map(c =>
          `• ${c.message || `与「${c.conflicting_task_title}」冲突`}`
        ).join('\n')
      }

      try {
        await ElMessageBox.confirm(
          `⚠️ 检测到时间冲突！${conflictDetails}\n\n请选择处理方式：`,
          '时间冲突',
          {
            confirmButtonText: '🔧 自动调整',
            cancelButtonText: '⚠️ 忽略冲突',
            distinguishCancelAndClose: true,
            type: 'warning'
          }
        )
        ElMessage.info('自动调整功能开发中，请手动调整时间')
        info.revert()
      } catch (action) {
        if (action === 'cancel') {
          const forceResponse = await taskStore.updateTask(taskId, {
            start_time: formatDateTime(newStart),
            end_time: formatDateTime(newEnd),
            force: true
          })

          if (forceResponse && forceResponse.success) {
            ElMessage.warning('⚠️ 已保留调整（存在时间冲突）')
            await taskStore.fetchTasks()
          } else {
            info.revert()
            ElMessage.error('强制更新失败')
          }
        } else {
          info.revert()
          ElMessage.info('已取消时间调整')
        }
      }
    } else if (response && response.success) {
      ElMessage.success({ message: '✅ 任务时间已更新', grouping: true })
    } else {
      ElMessage.error(response?.message || '更新时间失败')
      info.revert()
    }
  } catch (error) {
    ElMessage.error('更新时间失败: ' + (error.response?.data?.detail || error.message))
    info.revert()
  }
}

// ✅ 调整时长事件 - 增强版
async function handleEventResize(info) {
  const taskId = parseInt(info.event.id)
  const newEnd = info.event.end

  const formatDateTime = (date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`
  }

  console.log('🔄 开始调整任务时长:', taskId)
  console.log('新结束时间:', formatDateTime(newEnd))

  try {
    const response = await taskStore.updateTask(taskId, {
      end_time: formatDateTime(newEnd)
    })

    console.log('✅ 调整响应:', response)

    if (response && response.has_conflict) {
      let conflictDetails = ''
      if (response.conflicts && response.conflicts.length > 0) {
        conflictDetails = '\n\n' + response.conflicts.map(c =>
          `• ${c.message || `与「${c.conflicting_task_title}」冲突`}`
        ).join('\n')
      }

      try {
        await ElMessageBox.confirm(
          `⚠️ 检测到时间冲突！${conflictDetails}\n\n是否回滚到原来的时长？`,
          '时间冲突',
          {
            confirmButtonText: '✅ 回滚',
            cancelButtonText: '⚠️ 忽略冲突',
            distinguishCancelAndClose: true,
            type: 'warning'
          }
        )
        info.revert()
        ElMessage.info('已取消时长调整')
      } catch (action) {
        if (action === 'cancel') {
          const forceResponse = await taskStore.updateTask(taskId, {
            end_time: formatDateTime(newEnd),
            force: true
          })

          if (forceResponse && forceResponse.success) {
            ElMessage.warning('⚠️ 已保留调整（存在时间冲突）')
            await taskStore.fetchTasks()
          } else {
            info.revert()
            ElMessage.error('强制更新失败')
          }
        } else {
          info.revert()
        }
      }
    } else if (response && response.success) {
      ElMessage.success('✅ 任务时长已更新')
    } else {
      ElMessage.error(response?.message || '更新时长失败')
      info.revert()
    }
  } catch (error) {
    console.error('❌ 调整时长失败:', error)
    console.error('错误详情:', error.response?.data)
    ElMessage.error('更新时长失败: ' + (error.response?.data?.detail || error.message))
    info.revert()
  }
}

// 切换到编辑模式
function switchToEdit() {
  dialogMode.value = 'edit'
  taskForm.value = { ...selectedTask.value }
}

// 提交表单
async function handleSubmit() {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        console.log('提交表单数据:', taskForm.value)

        // ✅ 计算任务时长（分钟）
        const submitData = { ...taskForm.value }
        if (submitData.start_time && submitData.end_time) {
          const start = new Date(submitData.start_time)
          const end = new Date(submitData.end_time)
          const durationMs = end.getTime() - start.getTime()
          submitData.duration = Math.max(15, Math.round(durationMs / (1000 * 60)))
          console.log('✅ 自动计算时长:', submitData.duration, '分钟')
        } else {
          submitData.duration = 60
        }

        if (selectedTask.value) {
          const response = await taskStore.updateTask(selectedTask.value.id, submitData)

          if (response && response.success) {
            ElMessage.success('任务更新成功')
            dialogVisible.value = false
            await taskStore.fetchTasks()
          } else {
            ElMessage.error(response?.message || '更新失败')
          }
        } else {
          const response = await taskStore.addTask(submitData)

          if (response && response.has_conflict) {
            let conflictDetails = ''
            if (response.conflicts && response.conflicts.length > 0) {
              conflictDetails = '\n\n' + response.conflicts.map(c =>
                `• ${c.message || `与「${c.conflicting_task_title}」冲突`}`
              ).join('\n')
            }

            try {
              await ElMessageBox.confirm(
                `⚠️ 检测到时间冲突！${conflictDetails}\n\n请选择处理方式：`,
                '时间冲突',
                {
                  confirmButtonText: '🔧 自动调整',
                  cancelButtonText: '⚠️ 忽略冲突',
                  distinguishCancelAndClose: true,
                  type: 'warning'
                }
              )

              const adjustResponse = await taskStore.confirmTask({
                action: 'auto_adjust',
                task_data: submitData
              })

              if (adjustResponse && adjustResponse.success) {
                ElMessage.success(`✅ 已自动调整时间: ${adjustResponse.adjusted_time?.start_time?.slice(11, 16)}-${adjustResponse.adjusted_time?.end_time?.slice(11, 16)}`)
                dialogVisible.value = false
                await taskStore.fetchTasks()
              } else {
                ElMessage.error(adjustResponse?.message || '自动调整失败')
              }
            } catch (action) {
              if (action === 'cancel') {
                const ignoreResponse = await taskStore.confirmTask({
                  action: 'ignore',
                  task_data: submitData
                })

                if (ignoreResponse && ignoreResponse.success) {
                  ElMessage.warning('⚠️ 任务已添加（存在时间冲突）')
                  dialogVisible.value = false
                  await taskStore.fetchTasks()
                } else {
                  ElMessage.error(ignoreResponse?.message || '忽略冲突失败')
                }
              } else {
                ElMessage.info('已取消添加任务')
              }
            }
          } else if (response && response.success) {
            ElMessage.success('任务创建成功')
            dialogVisible.value = false
            await taskStore.fetchTasks()
          } else {
            ElMessage.error(response?.message || '创建任务失败')
          }
        }
      } catch (error) {
        console.error('❌ 提交表单失败:', error)
        ElMessage.error('操作失败: ' + (error.response?.data?.detail || error.message))
      }
    }
  })
}

// ✅ 删除任务 - 优化版（去掉延迟，自然动画）
async function handleDelete() {
  try {
    // ✅ 立即触发收缩动画（不再等待）
    isDeleting.value = true

    // ✅ 立即显示确认弹窗（去掉 300ms 延迟）
    await ElMessageBox.confirm(
      '确定要删除这个任务吗？此操作无法恢复。',
      '⚠️ 删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '再想想',
        type: 'warning',
        draggable: true,
        customClass: 'delete-confirm-dialog',
        icon: WarningFilled,
        closeOnClickModal: false
      }
    )

    const taskId = typeof selectedTask.value.id === 'string'
      ? parseInt(selectedTask.value.id)
      : selectedTask.value.id

    console.log('🗑️ 删除任务 ID:', taskId, '类型:', typeof taskId)

    await taskStore.deleteTask(taskId)

    dialogVisible.value = false
    await taskStore.fetchTasks()

    ElMessage.success({
      message: '🗑️ 任务已删除',
      grouping: true,
      duration: 2000
    })

  } catch (error) {
    if (error !== 'cancel') {
      console.error('❌ 删除任务失败:', error)
      ElMessage.error('删除失败: ' + error.message)
    }
  } finally {
    isDeleting.value = false
  }
}

// 重置表单
function resetForm() {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  selectedTask.value = null
  taskForm.value = {
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    deadline: null,
    priority: 'medium',
    status: 'pending'
  }
}

// ✅ 渲染日历事件（手动管理）- 增强视觉效果
function renderCalendarEvents() {
  if (!calendarRef.value) return

  const calendarApi = calendarRef.value.getApi()
  calendarApi.removeAllEvents()

  const events = taskStore.tasks
    .filter(task => task && task.id)
    .map(task => {
      let startTime = task.start_time
      let endTime = task.end_time
      let allDay = false

      if (!startTime || !endTime) {
        allDay = true
        if (task.deadline) {
          startTime = task.deadline.split('T')[0] + 'T00:00:00'
          endTime = task.deadline.split('T')[0] + 'T23:59:59'
        } else if (task.created_at) {
          startTime = task.created_at.split('T')[0] + 'T00:00:00'
          endTime = task.created_at.split('T')[0] + 'T23:59:59'
        } else {
          console.warn(`任务 "${task.title}" 缺少时间信息，将不会显示在日历上`)
          return null
        }
      } else {
        if (!startTime.includes('T')) {
          startTime = startTime.replace(' ', 'T')
        }
        if (!endTime.includes('T')) {
          endTime = endTime.replace(' ', 'T')
        }
      }

      const priorityConfig = {
        high: {
          backgroundColor: '#f56c6c',
          borderColor: '#f56c6c',
          icon: '🔴'
        },
        medium: {
          backgroundColor: '#e6a23c',
          borderColor: '#e6a23c',
          icon: '🟡'
        },
        low: {
          backgroundColor: '#67c23a',
          borderColor: '#67c23a',
          icon: '🟢'
        }
      }

      const config = priorityConfig[task.priority] || priorityConfig.medium

      return {
        id: task.id.toString(),
        title: `${config.icon} ${task.title}`,
        start: startTime,
        end: endTime,
        allDay: allDay,
        backgroundColor: config.backgroundColor,
        borderColor: config.borderColor,
        textColor: '#fff',
        classNames: [`priority-${task.priority}`],
        extendedProps: {
          ...task,
          description: task.description || '',
          priority_text: getPriorityText(task.priority),
          status_text: getStatusText(task.status)
        }
      }
    })
    .filter(event => event !== null)

  console.log('渲染日历事件:', events.length, '个任务')
  if (events.length > 0) {
    console.log('示例事件:', events[0])
  }

  events.forEach(event => {
    calendarApi.addEvent(event)
  })
}

// ✅ 监听任务变化，自动更新日历
watch(() => taskStore.tasks, (newTasks) => {
  console.log('🔄 任务列表变化，重新渲染日历事件，任务数:', newTasks.length)
  renderCalendarEvents()
}, { deep: true })

// 组件挂载时获取任务
onMounted(async () => {
  // ✅ 初始化缓存
  initHolidayCache()

  await taskStore.fetchTasks()

  await nextTick()
  renderCalendarEvents()

  // ✅ 启动缓存监控（仅开发环境）
  if (process.env.NODE_ENV === 'development') {
    console.log('🔍 缓存监控已启动')
  }
})

</script>

<style scoped>
.calendar-container {
  position: relative;
  height: 100%;
}

/* ✅ 骨架屏样式 */
.skeleton-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: white;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.skeleton-calendar {
  width: 100%;
  height: 100%;
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 16px;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}

.skeleton-day {
  aspect-ratio: 1;
  padding: 8px;
}

/* ✅ 空状态引导 */
.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 50;
  animation: slide-up 0.5s ease;
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translate(-50%, -40%);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%);
  }
}

.empty-content {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.empty-content h3 {
  margin: 20px 0 10px;
  font-size: 24px;
  color: #303133;
  font-weight: 600;
}

.empty-hint {
  color: #909399;
  font-size: 14px;
  margin-bottom: 24px;
  line-height: 1.6;
}

.add-first-task-btn {
  padding: 12px 32px;
  font-size: 16px;
  border-radius: 8px;
}

:deep(.fc) {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

:deep(.fc-toolbar) {
  margin-bottom: 1.5em !important;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

:deep(.fc-toolbar-title) {
  font-size: 1.5em !important;
  font-weight: 600;
  color: #303133;
}

/* ✅ 任务卡片基础样式 */
:deep(.fc-event) {
  cursor: pointer;
  border: none !important;
  border-radius: 6px !important;
  padding: 4px 8px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* ✅ 任务卡片悬浮动画 */
:deep(.fc-event:hover) {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15) !important;
  z-index: 10 !important;
}

/* ✅ 高优先级任务特殊效果 */
:deep(.priority-high) {
  background: linear-gradient(135deg, #f56c6c 0%, #ff8a80 100%) !important;
  animation: pulse-red 2s ease-in-out infinite;
}

:deep(.priority-medium) {
  background: linear-gradient(135deg, #e6a23c 0%, #ffb74d 100%) !important;
}

:deep(.priority-low) {
  background: linear-gradient(135deg, #67c23a 0%, #81c784 100%) !important;
}

/* ✅ 脉冲动画 - 高优先级提醒 */
@keyframes pulse-red {
  0%, 100% {
    box-shadow: 0 2px 4px rgba(245, 108, 108, 0.3);
  }
  50% {
    box-shadow: 0 4px 12px rgba(245, 108, 108, 0.6);
  }
}

/* ✅ 当前选中任务的高亮效果 */
:deep(.fc-event.selected-task) {
  ring: 3px solid #409eff !important;
  ring-offset: 2px;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.3) !important;
  transform: scale(1.05);
}

:deep(.fc-event-title) {
  font-weight: 500;
  font-size: 0.85em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ✅ 对话框美化 */
:deep(.task-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  margin: 0;
}

:deep(.el-dialog__title) {
  color: white;
  font-weight: 600;
  font-size: 1.2em;
}

:deep(.el-dialog__close) {
  color: white;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

.task-detail h3 {
  margin-bottom: 20px;
  color: #303133;
  font-size: 1.4em;
  font-weight: 600;
  padding-bottom: 12px;
  border-bottom: 2px solid #e4e7ed;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* ✅ 优先级选项样式 */
.priority-option {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ✅ 对话框弹跳进入动画 */
:deep(.dialog-bounce-enter-active) {
  animation: bounce-in 0.5s;
}
@keyframes bounce-in {
  0% { transform: scale(0); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

/* ✅ 删除时的内容收缩动画 */
.is-deleting {
  animation: delete-shrink 0.4s ease-out forwards;
}

@keyframes delete-shrink {
  0% {
    opacity: 1;
    transform: scale(1);
    filter: blur(0);
  }
  100% {
    opacity: 0.5;
    transform: scale(0.95);
    filter: blur(2px);
  }
}

/* ✅ 冲突时的抖动动画 */
:deep(.shake-animation) {
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
  background-color: #f56c6c !important;
}
@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}

/* ✅ 表单输入框出错时的脉冲效果 */
:deep(.el-form-item.is-error .el-input__wrapper) {
  animation: pulse-border 0.5s ease-in-out;
  box-shadow: 0 0 0 1px #f56c6c inset;
}
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4) inset; }
  50% { box-shadow: 0 0 0 4px rgba(245, 108, 108, 0.1) inset; }
  100% { box-shadow: 0 0 0 1px #f56c6c inset; }
}

.task-form {
  padding: 10px;
}

/* 快捷截止选项样式 */
.deadline-quick-options {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.deadline-quick-options .el-button {
  flex: 1;
  min-width: 0;
}

/* ✅ 响应式优化 */
@media (max-width: 768px) {
  .calendar-container {
    padding: 10px;
    height: calc(100vh - 20px);
  }

  :deep(.fc-toolbar) {
    flex-direction: column;
    gap: 8px;
  }

  :deep(.el-dialog) {
    width: 90% !important;
  }

  .empty-content {
    padding: 24px;
    max-width: 90vw;
  }

  .empty-content h3 {
    font-size: 20px;
  }
}

/* ✅ 加载状态样式 */
:deep(.fc-loading) {
  opacity: 0.6;
  pointer-events: none;
}

/* ✅ 删除确认弹窗样式优化 */
:deep(.delete-confirm-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.delete-confirm-dialog .el-message-box__header) {
  background: linear-gradient(135deg, #f56c6c 0%, #ff8a80 100%);
  padding: 16px;
  margin: 0;
}

:deep(.delete-confirm-dialog .el-message-box__title) {
  color: white;
  font-weight: 600;
}

:deep(.delete-confirm-dialog .el-message-box__close) {
  color: white;
}

:deep(.delete-confirm-dialog .el-message-box__content) {
  padding: 24px;
  font-size: 15px;
}

/* ✅ 删除按钮的点击反馈 */
:deep(.el-button--danger) {
  transition: all 0.2s ease;
}

:deep(.el-button--danger:active) {
  transform: scale(0.95);
}

/* ✅ 自定义日期单元格样式 */
:deep(.custom-day-cell) {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

:deep(.day-number) {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

:deep(.holiday-badge) {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  background: #ffd700;
  color: #d32f2f;
  font-weight: 500;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.holiday-badge.is-legal) {
  background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
  color: white;
  box-shadow: 0 1px 3px rgba(238, 90, 111, 0.3);
}

/* ✅ 周末的日期数字颜色 */
:deep(.fc-day-saturday .day-number),
:deep(.fc-day-sunday .day-number) {
  color: #909399;
}
</style>