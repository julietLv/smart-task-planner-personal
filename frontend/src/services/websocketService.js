// frontend/src/services/websocketService.js
import { ElNotification } from 'element-plus'

class WebSocketService {
  constructor() {
    this.ws = null
    this.userId = 1
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.baseReconnectDelay = 1000
    this.maxReconnectDelay = 30000
    this.store = null
    this.isConnected = false
    this.isConnecting = false
    this.heartbeatTimer = null
    this.heartbeatInterval = 25000
    this.visibilityHandler = null
    this.isRejectedByServer = false // ✅ 新增：标记是否被服务器拒绝
  }

  /**
   * 获取 store（延迟加载）
   */
  getStore() {
    if (!this.store) {
      const { useNotificationStore } = require('../stores/notificationStore')
      this.store = useNotificationStore()
    }
    return this.store
  }

  /**
   * 连接WebSocket - ✅ 连接共享/复用
   */
  connect() {
    // ✅ 如果被服务器拒绝，暂时不重连
    if (this.isRejectedByServer) {
      console.log('⚠️ 服务器拒绝连接，等待防抖期结束')
      return
    }

    // ✅ 连接复用：如果已连接或正在连接，直接返回
    if (this.isConnected || this.isConnecting) {
      console.log('⚠️ WebSocket 已连接或正在连接，跳过重复连接')
      return
    }

    // ✅ 连接复用：检查现有连接是否有效
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('✅ WebSocket 已连接，复用现有连接')
      this.isConnected = true
      this.startHeartbeat()
      return
    }

    this.isConnecting = true
    const wsUrl = `ws://localhost:8080/ws/${this.userId}`
    console.log(`🔌 正在连接 WebSocket: ${wsUrl}`)

    this.ws = new WebSocket(wsUrl)

    // 连接成功
    this.ws.onopen = () => {
      console.log('✅ WebSocket 连接成功')
      this.isConnected = true
      this.isConnecting = false
      this.isRejectedByServer = false // ✅ 重置拒绝标记
      this.reconnectAttempts = 0
      this.startHeartbeat()
    }

    // 接收消息
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        // ✅ 处理后端主动发送的心跳
        if (message.type === 'heartbeat') {
          console.log('💓 收到后端心跳，发送响应')
          this.send({ type: 'heartbeat' })
          return
        }

        this.handleMessage(message)
      } catch (error) {
        console.error('❌ 解析WebSocket消息失败:', error)
      }
    }

    // 连接关闭
    this.ws.onclose = (event) => {
      console.log(`❌ WebSocket 连接关闭 (code: ${event.code}, reason: ${event.reason})`)
      this.isConnected = false
      this.isConnecting = false
      this.stopHeartbeat()

      // ✅ 如果是被服务器拒绝（403），不触发重连
      if (event.code === 1008) {
        console.log('⚠️ 服务器拒绝连接（防抖），等待后重试')
        this.isRejectedByServer = true

        // 延迟后重置标记，允许重新连接
        setTimeout(() => {
          this.isRejectedByServer = false
          console.log('✅ 防抖期结束，允许重新连接')
        }, this.maxReconnectDelay)

        return
      }

      // ✅ 如果不是正常关闭，则尝试重连
      if (event.code !== 1000) {
        this.attemptReconnect()
      }
    }

    // 连接错误
    this.ws.onerror = (error) => {
      console.error('❌ WebSocket 错误:', error)
      this.isConnecting = false
    }
  }

  /**
   * 启动心跳检测
   */
  startHeartbeat() {
    this.stopHeartbeat()

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected && this.ws?.readyState === WebSocket.OPEN) {
        this.sendHeartbeat()
      }
    }, this.heartbeatInterval)

    console.log(`💓 心跳检测已启动 (间隔: ${this.heartbeatInterval / 1000}秒)`)
  }

  /**
   * 停止心跳检测
   */
  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
      console.log('💓 心跳检测已停止')
    }
  }

  /**
   * 设置页面可见性监听 - ✅ 页面可见性检测
   */
  setupVisibilityListener() {
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler)
    }

    this.visibilityHandler = () => {
      if (document.hidden) {
        console.log('📱 页面隐藏，断开 WebSocket 连接')
        this.disconnect(false)
      } else {
        console.log('📱 页面显示，重新连接 WebSocket')
        setTimeout(() => this.connect(), 500)
      }
    }

    document.addEventListener('visibilitychange', this.visibilityHandler)
    console.log('👁️ 页面可见性监听已启用')
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

      case 'report_generated':
        this.handleReportGenerated(message.data)
        break

      case 'heartbeat_ack':
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
  }

  /**
   * 处理截止提醒 - 区分紧急/普通
   */
  handleDeadlineReminder(data) {
    console.log('🔔 收到截止提醒:', data.title)

    const notificationType = data.notification_type || 'info'
    const store = this.getStore()

    store.addNotification({
      type: data.status === 'overdue' ? 'error' : 'warning',
      title: data.title,
      message: data.message,
      taskData: data,
      notificationType: notificationType
    })

    if (notificationType === 'urgent') {
      ElNotification({
        title: '⏰ 紧急提醒',
        message: data.message,
        type: 'error',
        duration: 0,
        position: 'top-right',
        onClick: () => {
          console.log('跳转到任务:', data.task_id)
        }
      })
    }
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
    const store = this.getStore()

    store.addNotification({
      type: 'info',
      title: data.title || '系统通知',
      message: data.message
    })
  }

  /**
   * 处理冲突通知
   */
  handleConflictNotification(data) {
    const store = this.getStore()

    store.addNotification({
      type: 'warning',
      title: '检测到任务冲突',
      message: data.message || `发现${data.conflict_count}个时间冲突`,
      conflictData: data
    })

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
    const store = this.getStore()

    store.addNotification({
      type: 'info',
      title: '日程变更',
      message: data.message || '您的日程安排已更新'
    })
  }

  /**
   * 处理周报生成
   */
  handleReportGenerated(data) {
    console.log('📊 收到周报数据:', data)

    // 触发事件，让 ChatWindow 组件接收
    if (this.reportCallback) {
      this.reportCallback(data)
    }
  }

  /**
   * 设置周报回调函数
   */
  setReportCallback(callback) {
    this.reportCallback = callback
  }

  /**
   * 尝试重新连接 - ✅ 指数退避算法
   */
  attemptReconnect() {
    // ✅ 检查是否被服务器拒绝
    if (this.isRejectedByServer) {
      console.log('⚠️ 服务器防抖中，不触发重连')
      return
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ 达到最大重连次数，停止重连')
      return
    }

    // ✅ 指数退避：1s, 2s, 4s, 8s, 最大10s（更快响应）
    const exponentialDelay = this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts)
    const delay = Math.min(exponentialDelay, 10000)  // 最大延迟从30s改为10s

    this.reconnectAttempts++

    console.log(`🔄 ${delay/1000}秒后尝试第${this.reconnectAttempts}次重连...`)

    setTimeout(() => {
      // ✅ 检查通知抽屉是否打开
      const drawerElement = document.querySelector('.el-drawer.is-open')
      if (drawerElement) {
        console.log('⚠️ 通知抽屉正在显示，延迟重连...')
        this.attemptReconnect()
        return
      }

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
   * @param {boolean} shouldReconnect - 是否应该触发重连（默认true）
   */
  disconnect(shouldReconnect = true) {
    this.stopHeartbeat()

    if (this.ws) {
      if (!shouldReconnect) {
        this.ws.close(1000, 'User initiated disconnect')
      } else {
        this.ws.close()
      }

      this.ws = null
      this.isConnected = false
      this.isConnecting = false
      console.log('🔌 WebSocket 已断开')
    }
  }

  /**
   * 完全销毁（清理所有资源）
   */
  destroy() {
    if (this.visibilityHandler) {
      document.removeEventListener('visibilitychange', this.visibilityHandler)
      this.visibilityHandler = null
    }

    this.stopHeartbeat()
    this.disconnect(false)
    console.log('🗑️ WebSocket 服务已销毁')
  }
}

// ✅ 导出单例 - ✅ 连接共享/复用
export const websocketService = new WebSocketService()
