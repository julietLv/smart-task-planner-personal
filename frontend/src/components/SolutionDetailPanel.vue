<template>
  <teleport to="body">
    <transition name="panel-slide">
      <div v-if="visible" class="solution-detail-panel" @click.self="handleClose">
        <div class="panel-backdrop" @click="handleClose"></div>

        <div class="panel-content">
          <!-- 关闭按钮 -->
          <el-button class="close-btn" circle size="small" @click="handleClose">
            <el-icon><Close /></el-icon>
          </el-button>

          <!-- 面板头部 -->
          <div class="panel-header">
            <div class="header-info">
              <h3 class="panel-title">{{ solutionTitle }}</h3>
              <el-tag type="success" size="large" effect="dark">
                综合匹配度: {{ solutionScore }}
              </el-tag>
            </div>
            <div class="time-range">
              <el-icon><Clock /></el-icon>
              <span>{{ formatTimeRange(solution.start_time, solution.end_time) }}</span>
            </div>
          </div>

          <!-- 8维能力雷达图 -->
          <div class="chart-section radar-section">
            <h4 class="section-title"> 8维能力雷达图</h4>
            <v-chart class="radar-chart" :option="radarOption" autoresize />
          </div>

          <!-- 认知负载折线图 -->
          <div class="chart-section load-section">
            <h4 class="section-title">📊 认知负载预测</h4>
            <v-chart class="load-chart" :option="loadOption" autoresize />

            <!-- AI建议提示 -->
            <div v-if="attentionDropHint" class="ai-suggestion">
              <el-icon class="suggestion-icon"><Warning /></el-icon>
              <span class="suggestion-text">{{ attentionDropHint }}</span>
            </div>
          </div>

          <!-- 方案优势 -->
          <div v-if="solution.reasons && solution.reasons.length > 0" class="advantages-section">
            <h4 class="section-title">✨ 方案优势</h4>
            <ul class="advantages-list">
              <li v-for="(reason, idx) in solution.reasons" :key="idx" class="advantage-item">
                <el-icon class="advantage-icon"><Check /></el-icon>
                <span>{{ reason }}</span>
              </li>
            </ul>
          </div>

          <!-- 一键采纳按钮 -->
          <div class="panel-actions">
            <el-button
              type="primary"
              size="large"
              class="adopt-btn"
              @click="handleAdopt"
              :loading="adopting"
            >
              <el-icon v-if="!adopting"><Check /></el-icon>
              {{ adopting ? '正在写入日程...' : '✅ 一键采纳此方案' }}
            </el-button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Close, Clock, Warning, Check } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import * as echarts from 'echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart, LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkPointComponent
} from 'echarts/components'
import { ElMessage } from 'element-plus'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  RadarChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkPointComponent
])

// Props
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  solution: {
    type: Object,
    required: true
  },
  taskPreview: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['close', 'adopt'])

// 状态
const adopting = ref(false)

// 计算属性
const solutionTitle = computed(() => {
  return props.taskPreview.title || props.solution.title || '未命名任务'
})

const solutionScore = computed(() => {
  return props.solution.score || 0
})

// 维度详情（从后端获取）
const dimensionDetails = computed(() => {
  const raw = props.solution.dimension_details || {}

  // 将后端返回的嵌套对象转换为简单的数字格式
  return {
    date_freshness: raw.date_freshness?.raw || 0,
    habit_match: raw.habit_match?.raw || 0,
    urgency: raw.urgency?.raw || 0,
    time_quality: raw.time_quality?.raw || 0,
    load_balance: raw.load_balance?.raw || 0,
    priority: raw.priority?.raw || 0,
    holiday: raw.holiday?.raw || 0,
    weather: raw.weather?.raw || 0
  }
})

// 雷达图配置
const radarOption = computed(() => {
  // 直接使用后端原始数据（包含完整的 raw, normalized, weighted, weight）
  const rawDimensionDetails = props.solution.dimension_details || {}

  // 维度配置：从后端数据中提取真实权重
  const dimensionConfigs = [
    { key: 'date_freshness', name: '日期新鲜度', max: 35 },
    { key: 'habit_match', name: '习惯匹配', max: 65 },
    { key: 'urgency', name: '任务紧急度', max: 50 },
    { key: 'time_quality', name: '时间段质量', max: 55 },
    { key: 'load_balance', name: '负载平衡', max: 15 },
    { key: 'priority', name: '优先级权重', max: 70 },
    { key: 'holiday', name: '节假日效应', max: 40 },
    { key: 'weather', name: '天气因素', max: 30 }
  ]

  const dimensions = dimensionConfigs.map(config => {
    const detail = rawDimensionDetails[config.key] || {}
    return {
      name: config.name,
      max: config.max,
      value: detail.raw || 0,
      normalized: detail.normalized || 0,
      weight: detail.weight || 0,  // 使用后端返回的真实权重（小数形式，如 0.2）
      weighted: detail.weighted || 0
    }
  })

  // 归一化到 0-100
  const normalizedData = dimensions.map(dim => {
    return Math.round((dim.value / dim.max) * 100)
  })

  return {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove|click',
      formatter: (params) => {
        const dim = dimensions[params.dataIndex]
        const percentage = Math.round(dim.normalized * 100)
        const weightPercent = (dim.weight * 100).toFixed(1)
        const weightedContribution = (dim.weighted * 100).toFixed(2)

        return `
          <div style="font-weight:bold;margin-bottom:5px">${dim.name}</div>
          <div>原始得分：${dim.value}/${dim.max}</div>
          <div>归一化：${percentage}%</div>
          <div>权重占比：${weightPercent}%</div>
          <div>加权贡献：${weightedContribution}分</div>
        `
      }
    },
    radar: {
      indicator: dimensions.map(dim => ({
        name: dim.name,
        max: 100
      })),
      radius: '65%',
      axisName: {
        color: '#606266',
        fontSize: 12
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(64, 158, 255, 0.05)', 'rgba(64, 158, 255, 0.1)']
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(64, 158, 255, 0.2)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(64, 158, 255, 0.15)'
        }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: normalizedData,
        name: '方案评分',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.4)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ])
        },
        lineStyle: {
          color: '#409eff',
          width: 2
        },
        itemStyle: {
          color: '#409eff'
        },
        // 添加数据点标记
        symbol: 'circle',
        symbolSize: 8
      }]
    }]
  }
})

// 认知负载数据（基于真实数据计算）
const cognitiveLoadData = computed(() => {
  const startTime = props.solution.start_time
  const endTime = props.solution.end_time

  if (!startTime || !endTime) {
    return { times: [], values: [], attentionDrops: [] }
  }

  const start = new Date(startTime)
  const end = new Date(endTime)
  const times = []
  const values = []
  const attentionDrops = []

  let current = new Date(start)

  while (current <= end) {
    const timeStr = current.toTimeString().slice(0, 5)
    times.push(timeStr)

    const hour = current.getHours() + current.getMinutes() / 60

    // 基于真实因素计算认知负载
    let load = calculateRealCognitiveLoad(hour, props.solution)

    // 检测注意力下降点（连续高负载后的休息点）
    if (values.length > 0 && load > 75 && values[values.length - 1] > 70) {
      attentionDrops.push({
        time: timeStr,
        value: Math.round(load),
        reason: '高认知负载时段，建议适当休息'
      })
    }

    values.push(Math.round(load))
    current = new Date(current.getTime() + 15 * 60000)
  }

  return { times, values, attentionDrops }
})

// 基于真实因素计算认知负载
function calculateRealCognitiveLoad(hour, solution) {
  let load = 50 // 基准值

  // 1. 时间因素：上午认知高峰，下午逐渐下降
  if (hour >= 9 && hour <= 11) {
    load += 15 // 上午高效时段
  } else if (hour >= 14 && hour <= 15) {
    load += 10 // 下午黄金时段
  } else if (hour >= 15.5 && hour <= 17) {
    load -= 5  // 下午疲劳期
  }

  // 2. 任务优先级影响
  const priority = solution.priority || 'medium'
  if (priority === 'high') load += 15
  else if (priority === 'low') load -= 10

  // 3. 任务类型影响（从标题推断）
  const title = solution.title || ''
  if (title.includes('会议') || title.includes('讨论')) {
    load += 10 // 会议类任务认知负载高
  } else if (title.includes('运动') || title.includes('休息')) {
    load -= 15 // 轻松类任务
  }

  // 4. 连续工作时间（如果有多个任务）
  // 这里可以后续接入任务密度数据

  return Math.max(0, Math.min(100, load))
}

const attentionDropHint = computed(() => {
  if (cognitiveLoadData.value.attentionDrops.length > 0) {
    return `⚠️ ${cognitiveLoadData.value.attentionDrops[0].reason}`
  }
  return null
})

// 折线图配置
const loadOption = computed(() => {
  const { times, values, attentionDrops } = cognitiveLoadData.value

  const markPoints = attentionDrops.map(drop => ({
    coord: [drop.time, drop.value],
    value: '️',
    itemStyle: { color: '#f56c6c' },
    label: {
      formatter: drop.reason,
      position: 'top',
      fontSize: 11,
      color: '#f56c6c'
    }
  }))

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        return `${params[0].name}<br/>认知负载: ${params[0].value}%`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: times,
      boundaryGap: false,
      axisLine: {
        lineStyle: { color: '#dcdfe6' }
      },
      axisLabel: {
        color: '#909399',
        fontSize: 11,
        rotate: times.length > 8 ? 45 : 0
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      name: '负载值 (%)',
      nameTextStyle: {
        color: '#909399',
        fontSize: 12
      },
      axisLine: {
        lineStyle: { color: '#dcdfe6' }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(220, 223, 230, 0.3)'
        }
      }
    },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        color: '#409eff',
        width: 3
      },
      itemStyle: {
        color: '#409eff',
        borderWidth: 2
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
        ])
      },
      markPoint: markPoints.length > 0 ? {
        data: markPoints,
        symbol: 'pin',
        symbolSize: 50
      } : undefined
    }]
  }
})

// 方法
const formatTimeRange = (start, end) => {
  if (!start || !end) return '时间待定'
  const formatDate = (timeStr) => {
    const date = new Date(timeStr)
    return date.toTimeString().slice(0, 5)
  }
  return `${formatDate(start)} - ${formatDate(end)}`
}

const handleClose = () => {
  emit('close')
}

const handleAdopt = async () => {
  adopting.value = true

  try {
    // 调用父组件的采纳方法
    emit('adopt', props.solution)

    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 1500))

    ElMessage.success(`✅ 已写入日程：${solutionTitle.value}`)
    handleClose()
  } catch (error) {
    ElMessage.error('写入日程失败，请重试')
  } finally {
    adopting.value = false
  }
}

// ESC 键关闭
const handleKeydown = (e) => {
  if (e.key === 'Escape' && props.visible) {
    handleClose()
  }
}

watch(() => props.visible, (newVal) => {
  if (newVal) {
    window.addEventListener('keydown', handleKeydown)
  } else {
    window.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<style scoped>
.solution-detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  z-index: 10000;
  display: flex;
  justify-content: flex-end;
}

.panel-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 450px;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
}

.panel-content {
  position: relative;
  width: 450px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
  overflow-y: auto;
  padding: 24px;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 10;
}

.panel-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #e4e7ed;
}

.header-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

.chart-section {
  margin-bottom: 24px;
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
}

.radar-chart {
  height: 300px;
  width: 100%;
}

.load-chart {
  height: 250px;
  width: 100%;
  margin-bottom: 12px;
}

.ai-suggestion {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(245, 108, 108, 0.1);
  border-left: 3px solid #f56c6c;
  padding: 12px;
  border-radius: 6px;
}

.suggestion-icon {
  color: #f56c6c;
  font-size: 18px;
}

.suggestion-text {
  color: #f56c6c;
  font-size: 13px;
  font-weight: 500;
}

.advantages-section {
  margin-bottom: 24px;
}

.advantages-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.advantage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #606266;
  font-size: 14px;
}

.advantage-icon {
  color: #67c23a;
  font-size: 16px;
}

.panel-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 2px solid #e4e7ed;
}

.adopt-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  border: none;
}

.adopt-btn:hover {
  background: linear-gradient(135deg, #66b1ff 0%, #409eff 100%);
}

/* 动画 */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.panel-slide-enter-from {
  transform: translateX(100%);
}

.panel-slide-enter-from .panel-backdrop {
  opacity: 0;
}

.panel-slide-leave-to {
  transform: translateX(100%);
}

.panel-slide-leave-to .panel-backdrop {
  opacity: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .solution-detail-panel {
    justify-content: center;
    align-items: flex-end;
  }

  .panel-backdrop {
    right: 0;
  }

  .panel-content {
    width: 100%;
    height: 80vh;
    border-radius: 20px 20px 0 0;
  }

  .panel-slide-enter-from {
    transform: translateY(100%);
  }

  .panel-slide-leave-to {
    transform: translateY(100%);
  }
}
</style>
