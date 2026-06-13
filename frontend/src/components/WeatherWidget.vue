<template>
  <div class="weather-widget">
    <!-- 天气信息卡片 -->
    <div class="weather-card" v-loading="loading">
      <div class="weather-main">
        <span class="weather-icon">{{ weatherIcon }}</span>
        <div class="weather-info">
          <div class="city-temp">
            <span class="city">{{ city }}</span>
            <span class="temp">{{ temperature }}°C</span>
          </div>
          <span class="condition">{{ conditionText }}</span>
        </div>
      </div>

      <!-- 功能按钮区 -->
      <div class="action-buttons">
        <el-button
          type="primary"
          size="small"
          @click="handleViewTasks"
          class="action-btn"
        >
          <el-icon><Document /></el-icon>
          任务记录
        </el-button>
        <el-button
          type="primary"
          size="small"
          @click="handleShowDetail"
          class="action-btn"
        >
          <el-icon><View /></el-icon>
          天气详情
        </el-button>
      </div>
    </div>

    <!-- 天气详情对话框 -->
    <el-dialog
      v-model="showDetail"
      :title="`${city} - 天气详情`"
      width="500px"
      :close-on-click-modal="true"
      teleport="body"
      class="weather-detail-dialog"
    >
      <div class="detail-content">
        <!-- 当前天气 -->
        <div class="current-section">
          <div class="location-bar">
            <span class="location-icon">📍</span>
            <span class="city-name">{{ city }}</span>
            <el-button
              type="primary"
              size="small"
              @click="showCitySelector = true"
              class="change-city-btn"
            >
              切换城市
            </el-button>
          </div>

          <div class="weather-display">
            <span class="big-icon">{{ weatherIcon }}</span>
            <div class="temp-info">
              <span class="current-temp">{{ temperature }}°C</span>
              <span class="temp-range">{{ tempMin }}°C / {{ temperature }}°C</span>
            </div>
          </div>

          <div class="weather-metrics">
            <div class="metric-item">
              <span class="metric-label">天气</span>
              <span class="metric-value">{{ conditionText }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">湿度</span>
              <span class="metric-value">{{ humidity }}%</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">风力</span>
              <span class="metric-value">{{ windLevel }}级</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">风速</span>
              <span class="metric-value">{{ windSpeedKmh }} km/h</span>
            </div>
          </div>
        </div>

        <!-- 未来预报 -->
        <div class="forecast-section" v-if="forecasts.length > 0">
          <h3 class="section-title">📅 未来3天预报</h3>
          <div class="forecast-list">
            <div
              v-for="(forecast, index) in forecasts"
              :key="index"
              class="forecast-item"
            >
              <span class="forecast-date">{{ forecast.date }}</span>
              <div class="forecast-data">
                <span class="forecast-icon">{{ getWeatherIcon(forecast.condition) }}</span>
                <span class="forecast-temp">{{ forecast.temp_min }}°C ~ {{ forecast.temperature }}°C</span>
                <span class="forecast-condition">{{ getConditionText(forecast.condition) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

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
            :class="{ 'is-current': cityItem === city }"
            @click="selectCity(cityItem)"
          >
            <span class="option-icon">{{ cityItem === city ? '' : '🏙️' }}</span>
            <span class="option-text">{{ cityItem }}</span>
            <el-tag v-if="cityItem === city" type="primary" size="small">当前</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, View } from '@element-plus/icons-vue'
import { getCurrentWeather, getWeatherForecast, updateUserCity, getUserCity } from '@/api/weatherApi'

// 定义事件
const emit = defineEmits(['view-tasks'])

// 常用城市列表
const commonCities = [
  '北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安',
  '南京', '重庆', '天津', '苏州', '长沙', '郑州', '东莞', '青岛',
  '宁波', '昆明', '厦门', '福州', '合肥', '济南', '哈尔滨', '沈阳'
]

// 响应式数据
const city = ref('北京')
const temperature = ref(0)
const condition = ref('sunny')
const humidity = ref(0)
const windLevel = ref(0)
const windSpeedKmh = ref(0)
const tempMin = ref(0)
const forecasts = ref([])
const loading = ref(false)
const showDetail = ref(false)
const showCitySelector = ref(false)
const searchCity = ref('')

// 计算属性
const weatherIcon = computed(() => getWeatherIcon(condition.value))
const conditionText = computed(() => getConditionText(condition.value))
const filteredCities = computed(() => {
  if (!searchCity.value) return commonCities
  return commonCities.filter(c => c.includes(searchCity.value))
})

// 天气图标映射
function getWeatherIcon(condition) {
  const iconMap = {
    'sunny': '☀️',
    'cloudy': '☁️',
    'rainy': '🌧️',
    'stormy': '⛈️',
    'snowy': '❄️'
  }
  return iconMap[condition] || '️'
}

// 天气文字映射
function getConditionText(condition) {
  const textMap = {
    'sunny': '晴',
    'cloudy': '多云',
    'rainy': '雨',
    'stormy': '暴雨',
    'snowy': '雪'
  }
  return textMap[condition] || '晴'
}

// 加载天气数据
async function loadWeather() {
  loading.value = true
  try {
    const cityRes = await getUserCity()
    if (cityRes.data.success) {
      city.value = cityRes.data.city
    }

    const weatherRes = await getCurrentWeather(city.value)
    if (weatherRes.data.success) {
      const weather = weatherRes.data
      temperature.value = weather.temperature
      condition.value = weather.condition
      humidity.value = weather.humidity
      windLevel.value = weather.wind_level || weather.wind_speed || 0
      windSpeedKmh.value = weather.wind_speed_kmh || 0
      tempMin.value = weather.temp_min || temperature.value - 5
    }

    const forecastRes = await getWeatherForecast(city.value, 3)
    if (forecastRes.data.success) {
      forecasts.value = forecastRes.data.forecasts
    }
  } catch (error) {
    console.error('加载天气数据失败:', error)
    ElMessage.error('加载天气数据失败')
  } finally {
    loading.value = false
  }
}

// 选择城市
async function selectCity(newCity) {
  try {
    loading.value = true
    await updateUserCity(1, newCity)
    city.value = newCity
    showCitySelector.value = false
    await loadWeather()
    ElMessage.success(`已切换到${newCity}`)
  } catch (error) {
    console.error('切换城市失败:', error)
    ElMessage.error('切换城市失败')
  } finally {
    loading.value = false
  }
}

// 显示天气详情
function handleShowDetail() {
  showDetail.value = true
}

// 查看任务记录
function handleViewTasks() {
  emit('view-tasks')
}

// 组件挂载时加载数据
onMounted(() => {
  loadWeather()

  // 监听城市变化事件
  window.addEventListener('city-changed', handleCityChanged)
})

// 组件卸载时移除监听
onUnmounted(() => {
  window.removeEventListener('city-changed', handleCityChanged)
})

// 处理城市变化
function handleCityChanged(event) {
  const newCity = event.detail.city
  if (newCity && newCity !== city.value) {
    city.value = newCity
    loadWeather()
  }
}

// 监听弹窗打开时刷新数据
watch(showDetail, (newValue) => {
  if (newValue) {
    loadWeather()
  }
})
</script>

<style scoped>
.weather-widget {
  width: 100%;
}

.weather-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 16px;
  color: white;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
  transition: box-shadow 0.3s ease;
}

.weather-card:hover {
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.4);
}

.weather-main {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.weather-icon {
  font-size: 32px;
}

.weather-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.city-temp {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.city {
  font-size: 14px;
  opacity: 0.9;
}

.temp {
  font-size: 24px;
  font-weight: bold;
}

.condition {
  font-size: 12px;
  opacity: 0.8;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.action-btn {
  flex: 1;
  background: rgba(255, 255, 255, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: white;
  border-radius: 8px;
  font-weight: 500;
  backdrop-filter: blur(4px);
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.35);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.action-btn:active {
  transform: translateY(0);
}

/* 详情对话框样式 */
.weather-detail-dialog :deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

.weather-detail-dialog :deep(.el-dialog__header) {
  padding: 20px 20px 10px;
  border-bottom: 1px solid #ebeef5;
}

.weather-detail-dialog :deep(.el-dialog__body) {
  padding: 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.detail-content {
  padding: 0;
}

.current-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 20px;
  color: white;
  margin-bottom: 20px;
}

.location-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.location-icon {
  font-size: 18px;
}

.city-name {
  flex: 1;
  font-size: 18px;
  font-weight: bold;
}

.change-city-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
}

.change-city-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.weather-display {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.big-icon {
  font-size: 48px;
}

.temp-info {
  display: flex;
  flex-direction: column;
}

.current-temp {
  font-size: 36px;
  font-weight: bold;
}

.temp-range {
  font-size: 14px;
  opacity: 0.8;
}

.weather-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric-item {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.metric-label {
  display: block;
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 4px;
}

.metric-value {
  display: block;
  font-size: 16px;
  font-weight: bold;
}

.forecast-section {
  margin-top: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 12px;
  color: #333;
}

.forecast-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.forecast-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.forecast-item:hover {
  background: #e8eaf0;
}

.forecast-date {
  font-size: 14px;
  color: #666;
}

.forecast-data {
  display: flex;
  align-items: center;
  gap: 12px;
}

.forecast-icon {
  font-size: 20px;
}

.forecast-temp {
  font-size: 14px;
  font-weight: bold;
  color: #333;
}

.forecast-condition {
  font-size: 14px;
  color: #666;
}

/* 城市选择器样式 */
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
</style>
