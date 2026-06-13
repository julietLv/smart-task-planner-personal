// frontend/src/services/websocketService.js
import { useNotificationStore } from '../stores/notificationStore'
import { ElNotification } from 'element-plus'

class WebSocketService {
  constructor() {
    this.ws = null
    this.userId = 1 // TODO: 从用户认证中获取
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000 // 3秒
    this.store = useNotificationStore()
  }

  /**
   * 连接WebSocket
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('✅ WebSocket 已连接')
      return
    }

    const wsUrl = `ws://localhost:8080/ws/${this.userId}`
    console.log(`🔌 正在连接 WebSocket: ${wsUrl}`)

    this.ws = new WebSocket(wsUrl)

    // 连接成功
    this.ws.onopen = () => {
      console.log('✅ WebSocket 连接成功')
      this.reconnectAttempts = 0
    }

    // 接收消息
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        this.handleMessage(message)
      } catch (error) {
        console.error('❌ 解析WebSocket消息失败:', error)
      }
    }

    // 连接关闭
    this.ws.onclose = () => {
      console.log('❌ WebSocket 连接关闭')
      this.attemptReconnect()
    }

    // 连接错误
    this.ws.onerror = (error) => {
      console.error('❌ WebSocket 错误:', error)
    }
  }

  /**
   * 处理接收到的消息
   */
  handleMessage(message) {
    console.log('📨 收到WebSocket消息:', message.type)

    switch (message.type) {
      case 'welcome':
        console.log('👋 欢迎消息:', message.data.message)
        break

      case 'daily_summary':
        this.handleDailySummary(message.data)
        break

      case 'deadline_reminder':
        this.handleDeadlineReminder(message.data)
        break

      case 'notification':
        this.handleGeneralNotification(message.data)
        break

      case 'conflict_notification':
        this.handleConflictNotification(message.data)
        break

      case 'schedule_change':
        this.handleScheduleChange(message.data)
        break

      case 'heartbeat_ack':
        // 心跳响应，无需处理
        break

      default:
        console.warn('⚠️ 未知消息类型:', message.type)
    }
  }

  /**
   * 处理每日摘要
   */
  handleDailySummary(data) {
    console.log('📅 收到每日摘要:', data.date)
    // 可以在这里显示摘要弹窗或更新UI
  }

  /**
   * 处理截止提醒 - 区分紧急/普通
   */
  handleDeadlineReminder(data) {
    console.log('🔔 收到截止提醒:', data.title)

    const notificationType = data.notification_type || 'info'

    // ✅ 添加到通知中心
    this.store.addNotification({
      type: data.status === 'overdue' ? 'error' : 'warning',
      title: data.title,
      message: data.message,
      taskData: data
    })

    // ✅ 紧急通知：显示弹窗
    if (notificationType === 'urgent') {
      ElNotification({
        title: '⏰ 紧急提醒',
        message: data.message,
        type: 'error',
        duration: 0, // 不自动关闭
        position: 'top-right',
        onClick: () => {
          // 点击通知可以跳转到任务详情
          console.log('跳转到任务:', data.task_id)
        }
      })
    }
    // 普通通知：只显示轻微提示
    else if (notificationType === 'normal') {
      ElNotification({
        title: '📅 任务提醒',
        message: data.message,
        type: 'warning',
        duration: 5000,
        position: 'bottom-right'
      })
    }
  }

  /**
   * 处理通用通知
   */
  handleGeneralNotification(data) {
    console.log('📢 收到通用通知:', data)

    this.store.addNotification({
      type: 'info',
      title: data.title || '系统通知',
      message: data.message
    })
  }

  /**
   * 处理冲突通知
   */
  handleConflictNotification(data) {
    console.log('⚠️ 收到冲突通知:', data.conflict_count, '个冲突')

    // 添加到通知中心
    this.store.addNotification({
      type: 'warning',
      title: '检测到任务冲突',
      message: data.message || `发现${data.conflict_count}个时间冲突`,
      conflictData: data
    })

    // 显示提示
    ElNotification({
      title: '⚠️ 任务冲突',
      message: data.message || '检测到任务时间冲突，请查看通知中心',
      type: 'warning',
      duration: 8000,
      position: 'top-right'
    })
  }

  /**
   * 处理日程变更
   */
  handleScheduleChange(data) {
    console.log('📋 收到日程变更:', data)

    this.store.addNotification({
      type: 'info',
      title: '日程变更',
      message: data.message || '您的日程安排已更新'
    })
  }

  /**
   * 尝试重新连接
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ 达到最大重连次数，停止重连')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`🔄 ${delay/1000}秒后尝试第${this.reconnectAttempts}次重连...`)

    setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * 发送消息
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.error('❌ WebSocket 未连接')
    }
  }

  /**
   * 发送心跳
   */
  sendHeartbeat() {
    this.send({ type: 'heartbeat' })
  }

  /**
   * 请求每日摘要
   */
  requestSummary() {
    this.send({ type: 'request_summary' })
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

// ✅ 导出单例
export const websocketService = new WebSocketService()
