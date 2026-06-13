import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi, preferenceApi } from '../api/taskApi'

const CACHE_TTL = 5 * 60 * 1000 // 5分钟缓存

function getCachedData(key) {
  try {
    const cached = localStorage.getItem(key)
    if (!cached) return null

    const { data, timestamp } = JSON.parse(cached)
    const now = Date.now()

    if (now - timestamp > CACHE_TTL) {
      localStorage.removeItem(key)
      return null
    }

    return data
  } catch (error) {
    console.error('读取缓存失败:', error)
    return null
  }
}

function setCachedData(key, data) {
  try {
    const cacheItem = {
      data,
      timestamp: Date.now()
    }
    localStorage.setItem(key, JSON.stringify(cacheItem))
  } catch (error) {
    console.error('保存缓存失败:', error)
  }
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const loading = ref(false)
  const error = ref(null)
  const currentUser = ref({ id: 1, name: '默认用户' })
  const preferences = ref(null)
  const learnedHabits = ref(null)
  const todaySummary = ref(null)

  const highPriorityTasks = computed(() =>
    tasks.value.filter(t => t.priority === 'high')
  )

  const mediumPriorityTasks = computed(() =>
    tasks.value.filter(t => t.priority === 'medium')
  )

  const lowPriorityTasks = computed(() =>
    tasks.value.filter(t => t.priority === 'low')
  )

  const pendingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'pending')
  )

  const completedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'done')
  )

  async function fetchTasks(userId = 1, status = null, forceRefresh = false) {
    loading.value = true
    error.value = null

    const cacheKey = `tasks_${userId}_${status || 'all'}`

    // ⭐ forceRefresh 时跳过缓存，强制从服务器获取最新数据
    if (!forceRefresh) {
      const cachedData = getCachedData(cacheKey)
      if (cachedData) {
        tasks.value = cachedData
        loading.value = false
        return
      }
    }

    try {
      const response = await taskApi.getTasks(userId, status)
      if (response.success) {
        tasks.value = response.tasks
        setCachedData(cacheKey, response.tasks)
      }
    } catch (err) {
      error.value = err.message
      console.error('获取任务失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.createTask(data)
      if (response.success) {
        tasks.value.unshift(response.task)

        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('tasks_')) {
            localStorage.removeItem(key)
          }
        })

        return response
      }
    } catch (err) {
      error.value = err.message
      console.error('创建任务失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateTask(taskId, data, userId = 1) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.updateTask(taskId, data, userId)
      if (response.success) {
        const index = tasks.value.findIndex(t => t.id === taskId)
        if (index !== -1) {
          tasks.value[index] = response.task
        }

        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('tasks_')) {
            localStorage.removeItem(key)
          }
        })

        return response
      }
    } catch (err) {
      error.value = err.message
      console.error('更新任务失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteTask(taskId, userId = 1) {
    loading.value = true
    error.value = null
    try {
      const numericTaskId = typeof taskId === 'string' ? parseInt(taskId) : taskId

      console.log('📤 删除任务请求 - ID:', numericTaskId, '用户ID:', userId)

      const response = await taskApi.deleteTask(numericTaskId, userId)
      if (response.success) {
        tasks.value = tasks.value.filter(t => t.id !== numericTaskId)

        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('tasks_')) {
            localStorage.removeItem(key)
          }
        })

        return response
      }
    } catch (err) {
      error.value = err.message
      console.error('删除任务失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function batchDeleteTasks(taskIds, userId = 1) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.batchDeleteTasks(taskIds, userId)
      if (response.success) {
        tasks.value = tasks.value.filter(t => !taskIds.includes(t.id))

        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('tasks_')) {
            localStorage.removeItem(key)
          }
        })

        return response
      }
    } catch (err) {
      error.value = err.message
      console.error('批量删除任务失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchPreferences(userId = 1) {
    const cacheKey = `preferences_${userId}`
    const cachedData = getCachedData(cacheKey)

    if (cachedData) {
      preferences.value = cachedData
      return { success: true, preferences: cachedData }
    }

    try {
      const response = await preferenceApi.getPreferences(userId)
      if (response.success) {
        preferences.value = response.preferences
        setCachedData(cacheKey, response.preferences)
        return response
      }
    } catch (err) {
      console.error('获取偏好设置失败:', err)
      throw err
    }
  }

  async function updatePreferences(data, userId = 1) {
    try {
      const response = await preferenceApi.updatePreferences(data, userId)
      if (response.success) {
        preferences.value = response.preferences

        const cacheKey = `preferences_${userId}`
        setCachedData(cacheKey, response.preferences)

        return response
      }
    } catch (err) {
      console.error('更新偏好设置失败:', err)
      throw err
    }
  }

  async function createDefaultPreferences(userId = 1) {
    const defaultPrefs = {
      work_start_time: '09:00',
      work_end_time: '18:00',
      blocked_time_start: '22:00',
      blocked_time_end: '08:00',
      default_task_duration: 60,
      notification_enabled: true
    }

    const response = await preferenceApi.createPreferences(defaultPrefs, userId)
    if (response.success) {
      preferences.value = response.preferences
    }
    return response
  }

  async function checkConflicts(userId = 1) {
    try {
      const response = await taskApi.checkConflicts(userId)
      return response
    } catch (err) {
      console.error('检测冲突失败:', err)
      throw err
    }
  }

  async function fetchLearnedHabits(userId = 1) {
    const cacheKey = `habits_${userId}`
    const cachedData = getCachedData(cacheKey)

    if (cachedData) {
      learnedHabits.value = cachedData
      return { success: true, summary: cachedData }
    }

    try {
      const response = await preferenceApi.getLearnedHabits(userId)
      if (response.success) {
        learnedHabits.value = response.summary
        setCachedData(cacheKey, response.summary)
        return response
      }
    } catch (err) {
      console.error('获取学习习惯失败:', err)
      throw err
    }
  }

  async function deleteHabit(keyword, userId = 1) {
    try {
      const response = await preferenceApi.deleteHabit(keyword, userId)
      if (response.success) {
        await fetchLearnedHabits(userId)
        return response
      }
    } catch (err) {
      console.error('删除习惯失败:', err)
      throw err
    }
  }

  async function resetHabits(userId = 1) {
    try {
      const response = await preferenceApi.resetHabits(userId)
      if (response.success) {
        learnedHabits.value = null

        const cacheKey = `habits_${userId}`
        localStorage.removeItem(cacheKey)

        return response
      }
    } catch (err) {
      console.error('重置习惯失败:', err)
      throw err
    }
  }

  async function addCustomKeyword(keyword, category, userId = 1) {
    try {
      const response = await preferenceApi.addCustomKeyword(keyword, category, userId)
      if (response.success) {
        return response
      }
    } catch (err) {
      console.error('添加自定义关键词失败:', err)
      throw err
    }
  }

  // 确认任务操作（处理冲突后的用户选择）
  async function confirmTask(data) {
    loading.value = true
    error.value = null
    try {
      const response = await taskApi.confirmTask(data)

      // 如果任务创建成功，添加到列表
      if (response && response.success && response.task) {
        tasks.value.unshift(response.task)

        // ⭐ 关键修复：清除 localStorage 缓存，防止后续 fetchTasks 返回旧数据
        Object.keys(localStorage).forEach(key => {
          if (key.startsWith('tasks_')) {
            localStorage.removeItem(key)
          }
        })
      }

      // 始终返回响应（包括成功和失败）
      return response
    } catch (err) {
      error.value = err.message
      console.error('确认任务失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentUser(user) {
    currentUser.value = user
  }

  function clearError() {
    error.value = null
  }

  function getTaskById(taskId) {
    return tasks.value.find(t => t.id === taskId) || null
  }

  // ⭐ Phase 3: 添加清除缓存的方法
  function invalidateCache(cacheType, userId = 1) {
    if (cacheType === 'preferences') {
      const cacheKey = `preferences_${userId}`
      localStorage.removeItem(cacheKey)
      console.log(`✅ 已清除偏好设置缓存: ${cacheKey}`)
    } else if (cacheType === 'habits') {
      const cacheKey = `habits_${userId}`
      localStorage.removeItem(cacheKey)
      console.log(`✅ 已清除习惯缓存: ${cacheKey}`)
    }
  }

  return {
    tasks,
    loading,
    error,
    currentUser,
    preferences,
    learnedHabits,
    todaySummary,
    highPriorityTasks,
    mediumPriorityTasks,
    lowPriorityTasks,
    pendingTasks,
    completedTasks,
    fetchTasks,
    createTask,
    addTask: createTask,
    updateTask,
    deleteTask,
    batchDeleteTasks,
    fetchPreferences,
    updatePreferences,
    createDefaultPreferences,
    checkConflicts,
    fetchLearnedHabits,
    deleteHabit,
    resetHabits,
    addCustomKeyword,
    confirmTask,
    setCurrentUser,
    clearError,
    getTaskById,
    invalidateCache  // ⭐ Phase 3: 导出清除缓存方法
  }
})
