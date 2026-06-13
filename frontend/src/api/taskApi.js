import api from './index'

export const taskApi = {
  getTasks(userId = 1, status = null) {
    const params = { user_id: userId }
    if (status) {
      params.status = status
    }
    return api.get('/tasks/', { params })
  },

  createTask(data) {
    return api.post('/tasks/', data)
  },

  confirmTask(data) {
    return api.post('/tasks/confirm', data)
  },

  updateTask(taskId, data, userId = 1) {
    return api.put(`/tasks/${taskId}`, data, {
      params: { user_id: userId }
    })
  },

  deleteTask(taskId, userId = 1) {
    return api.delete(`/tasks/${taskId}`, {
      params: { user_id: userId }
    })
  },

  batchDeleteTasks(taskIds, userId = 1) {
    return api.post('/tasks/batch-delete', {
      task_ids: taskIds,
      user_id: userId
    })
  },

  parseTask(text) {
    return api.post('/tasks/parse', { text })
  },

  checkConflicts(userId = 1) {
    return api.get('/tasks/conflicts', {
      params: { user_id: userId }
    })
  },

  sendMessage(message, userId = 1) {
    return api.post('/chat/send', { message, user_id: userId })
  }
}

export const chatApi = {
  sendMessage(message, userId = 1) {
    return api.post('/chat/send', { message, user_id: userId })
  }
}

export const preferenceApi = {
  getPreferences(userId = 1) {
    return api.get('/preferences/', {
      params: { user_id: userId }
    })
  },

  updatePreferences(data, userId = 1) {
    return api.post('/preferences/', { ...data, user_id: userId })
  },

  createPreferences(data, userId = 1) {
    return api.post('/preferences/', { ...data, user_id: userId })
  },

  getLearnedHabits(userId = 1) {
    return api.get('/preferences/habits', {
      params: { user_id: userId }
    })
  },

  deleteHabit(keyword, userId = 1) {
    return api.delete(`/preferences/habits/${keyword}`, {
      params: { user_id: userId }
    })
  },

  resetHabits(userId = 1) {
    return api.post('/preferences/habits/reset', {}, {
      params: { user_id: userId }
    })
  },

  addCustomKeyword(keyword, category, userId = 1) {
    return api.post('/preferences/keywords/custom', {
      keyword,
      category,
      user_id: userId
    })
  },

  setAssistantNickname(nickname, userId = 1) {
    return api.post('/preferences/nickname', {
      nickname,
      user_id: userId
    })
  },

  getAssistantNickname(userId = 1) {
    return api.get('/preferences/nickname', {
      params: { user_id: userId }
    })
  },

  setUserNickname(nickname, userId = 1) {
    return api.post('/preferences/user-nickname', {
      nickname,
      user_id: userId
    })
  },

  getUserNickname(userId = 1) {
    return api.get('/preferences/user-nickname', {
      params: { user_id: userId }
    })
  }

}
