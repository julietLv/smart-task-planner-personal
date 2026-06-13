<template>
  <el-dialog
    v-model="visible"
    title="📋 任务记录"
    width="900px"
    :close-on-click-modal="false"
    class="task-record-dialog"
  >
    <div class="filter-bar">
      <div class="filter-left">
        <el-radio-group v-model="filterStatus" size="small">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="pending">待完成</el-radio-button>
          <el-radio-button value="done">已完成</el-radio-button>
          <el-radio-button value="cancelled">已取消</el-radio-button>
        </el-radio-group>
      </div>

      <div class="filter-actions">
        <!-- ✅ 新增：搜索框 -->
        <el-input
          v-model="searchKeyword"
          placeholder="🔍 搜索任务标题或描述..."
          clearable
          size="small"
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          style="width: 240px"
          value-format="YYYY-MM-DD"
        />

        <el-button
          v-if="selectedTasks.length > 0"
          type="danger"
          size="small"
          @click="handleBatchDelete"
          :loading="taskStore.loading"
          class="batch-delete-btn"
        >
          <el-icon><Delete /></el-icon>
          批量删除 ({{ selectedTasks.length }})
        </el-button>
      </div>
    </div>

    <div class="stats-cards">
      <el-card shadow="never" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon stat-blue">📊</div>
          <div class="stat-info">
            <div class="stat-value">{{ filteredTasks.length }}</div>
            <div class="stat-label">总任务数</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon stat-green">✅</div>
          <div class="stat-info">
            <div class="stat-value">{{ doneCount }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon stat-orange"></div>
          <div class="stat-info">
            <div class="stat-value">{{ pendingCount }}</div>
            <div class="stat-label">待完成</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="stat-card">
        <div class="stat-content">
          <div class="stat-icon stat-purple">🎯</div>
          <div class="stat-info">
            <div class="stat-value">{{ completionRate }}%</div>
            <div class="stat-label">完成率</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- ✅ 新增：图表可视化区域 -->
    <div class="charts-section" v-if="filteredTasks.length > 0">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card shadow="never" class="chart-card">
            <div ref="completionChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" class="chart-card">
            <div ref="priorityChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" class="chart-card">
            <div ref="statusChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <div class="task-list-container">
      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="全部任务" name="all">
          <TaskListWithSelection
            :tasks="filteredTasks"
            :selected-tasks="selectedTasks"
            @select="handleSelectTask"
            @refresh="fetchTasks"
          />
        </el-tab-pane>

        <el-tab-pane label="待完成" name="pending">
          <TaskListWithSelection
            :tasks="pendingTasks"
            :selected-tasks="selectedTasks"
            @select="handleSelectTask"
            @refresh="fetchTasks"
          />
        </el-tab-pane>

        <el-tab-pane label="已完成" name="done">
          <TaskListWithSelection
            :tasks="doneTasks"
            :selected-tasks="selectedTasks"
            @select="handleSelectTask"
            @refresh="fetchTasks"
          />
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">关闭</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { Delete, Search } from '@element-plus/icons-vue'
import { useTaskStore } from '../stores/taskStore'
import TaskListWithSelection from './TaskListWithSelection.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'

const taskStore = useTaskStore()
const visible = ref(false)
const activeTab = ref('all')
const filterStatus = ref('all')
const dateRange = ref(null)
const selectedTasks = ref([])
const searchKeyword = ref('') // ✅ 新增：搜索关键词

// ✅ 新增：图表引用
const completionChartRef = ref(null)
const priorityChartRef = ref(null)
const statusChartRef = ref(null)

let completionChart = null
let priorityChart = null
let statusChart = null

// ✅ 新增：搜索防抖定时器
let searchTimer = null

function open() {
  visible.value = true
  selectedTasks.value = []
  searchKeyword.value = '' // ✅ 打开时清空搜索
  fetchTasks()
}

async function fetchTasks() {
  await taskStore.fetchTasks()
  // ✅ 数据加载后初始化图表
  await nextTick()
  initCharts()
}

const pendingTasks = computed(() =>
  taskStore.tasks.filter(t => t.status === 'pending')
)

const doneTasks = computed(() =>
  taskStore.tasks.filter(t => t.status === 'done')
)

const doneCount = computed(() => doneTasks.value.length)
const pendingCount = computed(() => pendingTasks.value.length)
const completionRate = computed(() => {
  const total = doneCount.value + pendingCount.value
  if (total === 0) return 0
  return Math.round((doneCount.value / total) * 100)
})

// ✅ 新增：搜索处理函数（防抖）
function handleSearch() {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }

  searchTimer = setTimeout(() => {
    // 搜索时自动切换到"全部任务"Tab
    if (searchKeyword.value && activeTab.value !== 'all') {
      activeTab.value = 'all'
    }

    // 更新图表
    nextTick(() => {
      initCharts()
    })

    // 显示搜索结果提示
    if (searchKeyword.value) {
      const resultCount = filteredTasks.value.length
      if (resultCount === 0) {
        ElMessage.info(`未找到包含"${searchKeyword.value}"的任务`)
      }
    }
  }, 300) // 300ms 防抖
}

// ✅ 修改：filteredTasks 增加搜索过滤
const filteredTasks = computed(() => {
  let tasks = taskStore.tasks

  // ✅ 新增：关键词搜索（支持标题和描述）
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase().trim()
    tasks = tasks.filter(t => {
      const titleMatch = t.title?.toLowerCase().includes(keyword)
      const descMatch = t.description?.toLowerCase().includes(keyword)
      return titleMatch || descMatch
    })
  }

  // 状态筛选
  if (filterStatus.value !== 'all') {
    tasks = tasks.filter(t => t.status === filterStatus.value)
  }

  // 日期筛选
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    const startDate = new Date(start)
    const endDate = new Date(end + 'T23:59:59')
    tasks = tasks.filter(t => {
      if (!t.start_time) return false
      const taskDate = new Date(t.start_time)
      return taskDate >= startDate && taskDate <= endDate
    })
  }

  return tasks
})

// ✅ 新增：初始化图表
function initCharts() {
  if (filteredTasks.value.length === 0) return

  initCompletionChart()
  initPriorityChart()
  initStatusChart()
}

// ✅ 完成率环形图
function initCompletionChart() {
  if (!completionChartRef.value) return

  if (completionChart) {
    completionChart.dispose()
  }

  completionChart = echarts.init(completionChartRef.value)

  const total = doneCount.value + pendingCount.value
  const cancelledCount = filteredTasks.value.filter(t => t.status === 'cancelled').length

  const option = {
    title: {
      text: '完成率',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 14,
        fontWeight: 600,
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: 5,
      left: 'center',
      textStyle: {
        fontSize: 11
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{d}%',
          fontSize: 11
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 13,
            fontWeight: 'bold'
          }
        },
        data: [
          {
            value: doneCount.value,
            name: '已完成',
            itemStyle: { color: '#67c23a' }
          },
          {
            value: pendingCount.value,
            name: '待完成',
            itemStyle: { color: '#e6a23c' }
          },
          {
            value: cancelledCount,
            name: '已取消',
            itemStyle: { color: '#f56c6c' }
          }
        ].filter(item => item.value > 0)
      }
    ]
  }

  completionChart.setOption(option)
}

// ✅ 优先级分布柱状图
function initPriorityChart() {
  if (!priorityChartRef.value) return

  if (priorityChart) {
    priorityChart.dispose()
  }

  priorityChart = echarts.init(priorityChartRef.value)

  const priorityStats = {
    high: filteredTasks.value.filter(t => t.priority === 'high').length,
    medium: filteredTasks.value.filter(t => t.priority === 'medium').length,
    low: filteredTasks.value.filter(t => t.priority === 'low').length
  }

  const option = {
    title: {
      text: '优先级分布',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 14,
        fontWeight: 600,
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 50,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['高', '中', '低'],
      axisLine: {
        lineStyle: {
          color: '#dcdfe6'
        }
      },
      axisLabel: {
        color: '#606266',
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0'
        }
      },
      axisLabel: {
        color: '#606266',
        fontSize: 11
      }
    },
    series: [
      {
        type: 'bar',
        data: [
          {
            value: priorityStats.high,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#f56c6c' },
                { offset: 1, color: '#f89898' }
              ])
            }
          },
          {
            value: priorityStats.medium,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#e6a23c' },
                { offset: 1, color: '#f0c78a' }
              ])
            }
          },
          {
            value: priorityStats.low,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#67c23a' },
                { offset: 1, color: '#95d475' }
              ])
            }
          }
        ],
        barWidth: '50%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }

  priorityChart.setOption(option)
}

// ✅ 任务状态分布图
function initStatusChart() {
  if (!statusChartRef.value) return

  if (statusChart) {
    statusChart.dispose()
  }

  statusChart = echarts.init(statusChartRef.value)

  const statusStats = {
    pending: filteredTasks.value.filter(t => t.status === 'pending').length,
    done: filteredTasks.value.filter(t => t.status === 'done').length,
    cancelled: filteredTasks.value.filter(t => t.status === 'cancelled').length,
    overdue: filteredTasks.value.filter(t => t.status === 'overdue').length
  }

  const option = {
    title: {
      text: '状态分布',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 14,
        fontWeight: 600,
        color: '#303133'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      bottom: 5,
      left: 'center',
      textStyle: {
        fontSize: 11
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '55%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{d}%',
          fontSize: 11
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 13,
            fontWeight: 'bold'
          }
        },
        data: [
          {
            value: statusStats.pending,
            name: '待完成',
            itemStyle: { color: '#e6a23c' }
          },
          {
            value: statusStats.done,
            name: '已完成',
            itemStyle: { color: '#67c23a' }
          },
          {
            value: statusStats.cancelled,
            name: '已取消',
            itemStyle: { color: '#f56c6c' }
          },
          {
            value: statusStats.overdue,
            name: '已超时',
            itemStyle: { color: '#909399' }
          }
        ].filter(item => item.value > 0)
      }
    ]
  }

  statusChart.setOption(option)
}

function handleSelectTask(taskId) {
  const index = selectedTasks.value.indexOf(taskId)
  if (index > -1) {
    selectedTasks.value.splice(index, 1)
  } else {
    selectedTasks.value.push(taskId)
  }
}

async function handleBatchDelete() {
  if (selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要删除的任务')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )

    const response = await taskStore.batchDeleteTasks(selectedTasks.value)

    if (response.success) {
      ElMessage.success({
        message: response.message,
        duration: 2000
      })
      selectedTasks.value = []
      await fetchTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败: ' + error.message)
    }
  }
}

// ✅ 修改：监听增加 searchKeyword
watch([filterStatus, dateRange, activeTab], () => {
  nextTick(() => {
    initCharts()
  })
})

// ✅ 窗口大小变化时自适应
onMounted(() => {
  window.addEventListener('resize', () => {
    completionChart?.resize()
    priorityChart?.resize()
    statusChart?.resize()
  })
})

defineExpose({ open })
</script>

<style scoped>
.task-record-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.task-record-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
}

.task-record-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fafafa 100%);
  border-radius: 10px;
  border: 1px solid #ebeef5;
  gap: 12px;
}

.filter-left {
  flex-shrink: 0;
}

.filter-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

/* ✅ 新增：搜索框样式 */
.search-input {
  width: 220px;
}

.search-input :deep(.el-input__wrapper) {
  background: #fff;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
  transition: all 0.3s;
}

.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.search-input :deep(.el-input__prefix) {
  color: #909399;
}

.batch-delete-btn {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(245, 108, 108, 0);
  }
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  border: none;
  background: #fafafa;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.stat-card :deep(.el-card__body) {
  padding: 16px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-blue {
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
}

.stat-green {
  background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
}

.stat-orange {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
}

.stat-purple {
  background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

/* ✅ 新增：图表区域样式 */
.charts-section {
  margin-bottom: 20px;
}

.chart-card {
  border: none;
  background: #fafafa;
}

.chart-card :deep(.el-card__body) {
  padding: 12px;
}

.chart-container {
  width: 100%;
  height: 180px;
}

.task-list-container {
  min-height: 300px;
  max-height: 500px;
  overflow-y: auto;
}

.task-list-container :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.task-list-container :deep(.el-tabs__item) {
  padding: 0 20px;
  height: 40px;
  line-height: 40px;
  font-size: 14px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 8px;
}
</style>
