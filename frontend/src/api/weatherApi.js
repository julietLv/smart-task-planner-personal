/**
 * 天气相关API
 */
import axios from 'axios'

const API_BASE = '/api/weather'

/**
 * 获取当前天气
 * @param {string} city - 城市名称（可选）
 * @param {number} user_id - 用户ID
 * @returns {Promise}
 */
export function getCurrentWeather(city = null, user_id = 1) {
  const params = { user_id }
  if (city) params.city = city

  return axios.get(`${API_BASE}/current`, { params })
}

/**
 * 获取天气预报
 * @param {string} city - 城市名称（可选）
 * @param {number} days - 天数
 * @param {number} user_id - 用户ID
 * @returns {Promise}
 */
export function getWeatherForecast(city = null, days = 3, user_id = 1) {
  const params = { user_id, days }
  if (city) params.city = city

  return axios.get(`${API_BASE}/forecast`, { params })
}

/**
 * 更新用户城市
 * @param {number} user_id - 用户ID
 * @param {string} city - 城市名称
 * @returns {Promise}
 */
export function updateUserCity(user_id = 1, city) {
  return axios.put(`${API_BASE}/city`, {
    user_id,
    city
  })
}

/**
 * 获取用户城市
 * @param {number} user_id - 用户ID
 * @returns {Promise}
 */
export function getUserCity(user_id = 1) {
  return axios.get(`${API_BASE}/city`, {
    params: { user_id }
  })
}
