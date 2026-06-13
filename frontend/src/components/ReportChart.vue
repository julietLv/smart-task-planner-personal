<template>
  <div class="report-chart-container">
    <div ref="priorityChartRef" class="chart-item"></div>
    <div ref="statusChartRef" class="chart-item"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  }
})

const priorityChartRef = ref(null)
const statusChartRef = ref(null)

let priorityChart = null
let statusChart = null

function initCharts() {
  if (!props.chartData) return

  if (priorityChartRef.value && props.chartData.priority) {
    priorityChart = echarts.init(priorityChartRef.value)
    const priorityOption = {
      title: {
        text: props.chartData.priority.title,
        left: 'center',
        textStyle: {
          fontSize: 14,
          fontWeight: 600,
          color: '#303133'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}个 ({d}%)'
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            position: 'inside',
            formatter: '{b}\n{c}个\n{d}%',
            fontSize: 12,
            color: '#fff',
            fontWeight: 600
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          data: props.chartData.priority.data
        }
      ]
    }
    priorityChart.setOption(priorityOption)
  }

  if (statusChartRef.value && props.chartData.status) {
    statusChart = echarts.init(statusChartRef.value)
    const statusOption = {
      title: {
        text: props.chartData.status.title,
        left: 'center',
        textStyle: {
          fontSize: 14,
          fontWeight: 600,
          color: '#303133'
        }
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}个 ({d}%)'
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: true,
            position: 'inside',
            formatter: '{b}\n{c}个\n{d}%',
            fontSize: 12,
            color: '#fff',
            fontWeight: 600
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          data: props.chartData.status.data
        }
      ]
    }
    statusChart.setOption(statusOption)
  }
}

function resizeCharts() {
  priorityChart?.resize()
  statusChart?.resize()
}

onMounted(() => {
  initCharts()
  window.addEventListener('resize', resizeCharts)
})

watch(() => props.chartData, () => {
  initCharts()
}, { deep: true })

defineExpose({
  resize: resizeCharts
})
</script>

<style scoped>
.report-chart-container {
  display: flex;
  gap: 20px;
  margin: 16px 0;
  justify-content: center;
}

.chart-item {
  width: 280px;
  height: 280px;
}

@media (max-width: 768px) {
  .report-chart-container {
    flex-direction: column;
    align-items: center;
  }

  .chart-item {
    width: 240px;
    height: 240px;
  }
}
</style>
