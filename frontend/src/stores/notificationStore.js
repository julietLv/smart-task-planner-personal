import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationApi } from '../api/notificationApi'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const unreadCount = ref(0)
  const loading = ref(false)

  // ✅ 新增：从数据库加载持久化通知
  async function loadNotifications(userId = 1, limit = 100, unreadOnly = false) {
    loading.value = true
    try {
      const response = await notificationApi.getNotifications(userId, limit, unreadOnly)

      console.log(' 后端返回的原始通知数据:', JSON.stringify(response.notifications, null, 2))

      if (response.success) {
        notifications.value = response.notifications.map(n => ({
          id: n.id,
          type: n.type === 'daily_summary' ? 'daily_summary' :
                n.type === 'deadline_reminder' ? (n.notification_type === 'urgent' ? 'error' : 'warning') :
                n.type === 'conflict_notification' ? 'warning' : 'info',
          title: n.title,
          message: n.message,
          time: new Date(n.created_at).toLocaleString(),
          read: n.is_read,
          taskData: n.task_id ? { task_id: n.task_id } : null,
          notificationType: n.notification_type || 'info',
          createdAt: n.created_at,
          readAt: n.read_at
        }))

        unreadCount.value = notifications.value.filter(n => !n.read).length
        console.log(`✅ 从数据库加载 ${notifications.value.length} 条通知，${unreadCount.value} 条未读`)
      }
    } catch (err) {
      console.error('加载通知失败:', err)
    } finally {
      loading.value = false
    }
  }

  // ✅ 从后端获取提醒（实时）
  async function fetchReminders(userId = 1, hoursBefore = 6) {
    loading.value = true
    try {
      const response = await notificationApi.getReminders(userId, hoursBefore)
      if (response.success) {
        // 将提醒添加到通知列表（去重）
        response.reminders.forEach(r => {
          const exists = notifications.value.some(n =>
            n.taskData?.task_id === r.task_id && !n.read
          )

          if (!exists) {
            addNotification({
              type: r.status === 'overdue' ? 'error' : 'warning',
              title: r.title,
              message: r.message,
              taskData: r,
              notificationType: r.notification_type || 'info'
            })
          }
        })
        console.log(`✅ 获取到 ${response.reminders.length} 条提醒`)
      }
    } catch (err) {
      console.error('获取提醒失败:', err)
    } finally {
      loading.value = false
    }
  }

  // ✅ 获取每日摘要
  async function fetchDailySummary(userId = 1, date = null) {
    try {
      const response = await notificationApi.getDailySummary(userId, date)
      return response
    } catch (err) {
      console.error('获取每日摘要失败:', err)
      return null
    }
  }

  // ✅ 获取每周摘要
  async function fetchWeeklySummary(userId = 1, weekOffset = 0) {
    try {
      const response = await notificationApi.getWeeklySummary(userId, weekOffset)
      return response
    } catch (err) {
      console.error('获取每周摘要失败:', err)
      return null
    }
  }

  // ✅ 检测冲突
  async function checkConflicts(userId = 1) {
    try {
      const response = await notificationApi.getConflicts(userId)
      return response
    } catch (err) {
      console.error('检测冲突失败:', err)
      return null
    }
  }

  // ✅ 手动添加通知（兼容旧版 + WebSocket实时通知）
  function addNotification(notification) {
    const newNotif = {
      id: notification.id || Date.now() + Math.random(),
      type: notification.type || 'info',
      title: notification.title,
      message: notification.message,
      time: notification.time || new Date().toLocaleTimeString(),
      read: false,
      taskData: notification.taskData || null,
      conflictData: notification.conflictData || null,
      notificationType: notification.notificationType || 'normal',
      createdAt: notification.createdAt || new Date().toISOString()
    }

    // ✅ 检查是否已存在（避免重复）
    const exists = notifications.value.some(n =>
      n.id === newNotif.id ||
      (n.taskData?.task_id === newNotif.taskData?.task_id &&
       n.title === newNotif.title &&
       !n.read)
    )

    if (!exists) {
      notifications.value.unshift(newNotif)
      unreadCount.value++

      if (notifications.value.length > 50) {
        notifications.value.pop()
      }
    }
  }

  // ✅ 标记为已读（同步到后端）
  async function markAsRead(id) {
    const notif = notifications.value.find(n => n.id === id)
    if (notif && !notif.read) {
      notif.read = true
      notif.readAt = new Date().toISOString()
      unreadCount.value = Math.max(0, unreadCount.value - 1)

      // ✅ 同步到后端数据库
      try {
        await notificationApi.markAsRead(id)
      } catch (err) {
        console.error('标记已读失败:', err)
      }
    }
  }

  // ✅ 全部标记为已读（同步到后端）
  async function markAllAsRead(userId = 1) {
    notifications.value.forEach(n => {
      n.read = true
      n.readAt = new Date().toISOString()
    })
    unreadCount.value = 0

    try {
      await notificationApi.markAllAsRead(userId)
      console.log('✅ 所有通知已标记为已读')
    } catch (err) {
      console.error('批量标记失败:', err)
    }
  }

  // ✅ 新增：删除单个通知
  async function deleteNotification(id, userId = 1) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      const removed = notifications.value.splice(index, 1)[0]
      if (!removed.read) {
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }

      try {
        await notificationApi.deleteNotification(id, userId)
        console.log('✅ 通知已删除')
      } catch (err) {
        console.error('删除通知失败:', err)
        notifications.value.splice(index, 0, removed)
      }
    }
  }

  // ✅ 清空所有通知（同步到后端）
  async function clearAll(userId = 1) {
    // ✅ 前端清空
    notifications.value = []
    unreadCount.value = 0

    // ✅ 后端删除
    try {
      await notificationApi.clearAllNotifications(userId)
      console.log('✅ 所有通知已清空')
    } catch (err) {
      console.error('清空通知失败:', err)
    }
  }

  // ✅ 获取未读通知数量
  function getUnreadCount() {
    return notifications.value.filter(n => !n.read).length
  }

  return {
    notifications,
    unreadCount,
    loading,
    loadNotifications,  // ✅ 新增
    addNotification,
    markAsRead,
    markAllAsRead,
    deleteNotification,  // ✅ 新增
    clearAll,
    fetchReminders,
    fetchDailySummary,
    fetchWeeklySummary,
    checkConflicts,
    getUnreadCount
  }
})
