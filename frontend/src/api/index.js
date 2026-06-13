import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 90000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 可以在这里添加 token 等认证信息
    // const token = localStorage.getItem('token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    console.log('📤 请求:', config.method.toUpperCase(), config.url)
    return config
  },
  error => {
    console.error('❌ 请求错误:', error.message)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('响应:', response.config.url, response.status)
    return response.data
  },
  error => {
    let message = '网络请求失败'

    if (error.response) {
      switch (error.response.status) {
        case 400:
          message = '请求参数错误'
          break
        case 401:
          message = '未授权，请重新登录'
          break
        case 403:
          message = '拒绝访问'
          break
        case 404:
          message = '请求的资源不存在'
          break
        case 500:
          message = '服务器内部错误'
          break
        case 502:
          message = '网关错误'
          break
        case 503:
          message = '服务不可用'
          break
        default:
          message = error.response.data?.detail || `请求失败 (${error.response.status})`
      }
    } else if (error.request) {
      message = '网络连接失败，请检查网络'
    } else {
      message = error.message || '未知错误'
    }

    console.error('响应错误:', message)
    if (ElMessage && ElMessage.error) {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

export default api
