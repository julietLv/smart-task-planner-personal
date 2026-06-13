// frontend/src/api/notificationApi.js
import api from './index'

export const notificationApi = {
  // 获取到期提醒
  getReminders(userId = 1, hoursBefore = 6) {
    return api.get('/notifications/reminders', {
      params: { user_id: userId, hours_before: hoursBefore }
    })
  },

  // 获取重排建议
  getRescheduleSuggestion(taskId, userId = 1) {
    return api.post('/notifications/reschedule-suggestion', {
      task_id: taskId,
      user_id: userId
    })
  },

  // 获取每日摘要
  getDailySummary(userId = 1, date = null) {
    return api.get('/notifications/daily-summary', {
      params: { user_id: userId, date }
    })
  },

  // 获取每周摘要
  getWeeklySummary(userId = 1, weekOffset = 0) {
    return api.get('/notifications/weekly-summary', {
      params: { user_id: userId, week_offset: weekOffset }
    })
  },

  // 检测冲突
  getConflicts(userId = 1) {
    return api.get('/notifications/conflicts', {
      params: { user_id: userId }
    })
  },

  // ✅ 新增：获取持久化通知列表
  getNotifications(userId = 1, limit = 100, unreadOnly = false) {
    return api.get('/notifications/', {
      params: { user_id: userId, limit, unread_only: unreadOnly }
    })
  },

  // ✅ 新增：标记通知为已读
  markAsRead(notificationId, userId = 1) {
    return api.post(`/notifications/${notificationId}/read`, {
      user_id: userId
    })
  },

  // ✅ 新增：标记所有通知为已读
  markAllAsRead(userId = 1) {
    return api.post('/notifications/read-all', null, {
      params: { user_id: userId }
    })
  },

  // ✅ 新增：删除单个通知
  deleteNotification(notificationId, userId = 1) {
    return api.delete(`/notifications/${notificationId}`, {
      params: { user_id: userId }
    })
  },

  // ✅ 新增：清空所有通知
  clearAllNotifications(userId = 1) {
    return api.post('/notifications/clear-all', null, {
      params: { user_id: userId }
    })
  }
}
