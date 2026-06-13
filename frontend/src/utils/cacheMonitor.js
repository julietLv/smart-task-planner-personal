// frontend/src/utils/cacheMonitor.js - 新建文件

/**
 * 缓存性能监控系统
 * 用于收集缓存命中率、响应时间等指标
 */

class CacheMonitor {
  constructor() {
    this.stats = {
      // 缓存命中统计
      memoryHit: 0,
      localStorageHit: 0,
      serverRequest: 0,

      // 响应时间统计（毫秒）
      responseTimes: [],

      // 错误统计
      errors: 0,

      // 预加载统计
      preloadCount: 0,
      preloadSuccess: 0
    }

    this.startTime = Date.now()
    this.reportInterval = null
  }

  // 记录内存缓存命中
  recordMemoryHit() {
    this.stats.memoryHit++
  }

  // 记录 LocalStorage 命中
  recordLocalStorageHit() {
    this.stats.localStorageHit++
  }

  // 记录服务器请求
  recordServerRequest(responseTime) {
    this.stats.serverRequest++
    if (responseTime) {
      this.stats.responseTimes.push(responseTime)
    }
  }

  // 记录错误
  recordError() {
    this.stats.errors++
  }

  // 记录预加载
  recordPreload(success = true) {
    this.stats.preloadCount++
    if (success) {
      this.stats.preloadSuccess++
    }
  }

  // 计算平均响应时间
  getAvgResponseTime() {
    if (this.stats.responseTimes.length === 0) return 0
    const sum = this.stats.responseTimes.reduce((a, b) => a + b, 0)
    return Math.round(sum / this.stats.responseTimes.length)
  }

  // 计算缓存命中率
  getCacheHitRate() {
    const total = this.stats.memoryHit + this.stats.localStorageHit + this.stats.serverRequest
    if (total === 0) return 0
    const hits = this.stats.memoryHit + this.stats.localStorageHit
    return ((hits / total) * 100).toFixed(2)
  }

  // 获取完整统计报告
  getReport() {
    const totalRequests = this.stats.memoryHit + this.stats.localStorageHit + this.stats.serverRequest
    const uptime = Math.floor((Date.now() - this.startTime) / 1000)

    return {
      ...this.stats,
      avgResponseTime: this.getAvgResponseTime(),
      cacheHitRate: this.getCacheHitRate() + '%',
      totalRequests,
      uptimeSeconds: uptime,
      requestsPerMinute: totalRequests > 0 && uptime > 0
        ? ((totalRequests / uptime) * 60).toFixed(2)
        : 0
    }
  }

  // 打印统计报告
  printReport() {
    const report = this.getReport()
    console.group('📊 缓存性能报告')
    console.log('运行时间:', report.uptimeSeconds, '秒')
    console.log('总请求数:', report.totalRequests)
    console.log('请求频率:', report.requestsPerMinute, '次/分钟')
    console.log('---')
    console.log('⚡ 内存缓存命中:', report.memoryHit)
    console.log('💾 LocalStorage命中:', report.localStorageHit)
    console.log('🌐 服务器请求:', report.serverRequest)
    console.log('---')
    console.log('✅ 缓存命中率:', report.cacheHitRate)
    console.log('⏱️ 平均响应时间:', report.avgResponseTime, 'ms')
    console.log('❌ 错误次数:', report.errors)
    console.log('🔄 预加载:', `${report.preloadSuccess}/${report.preloadCount}`)
    console.groupEnd()
  }

  // 启动定期报告
  startReporting(intervalMs = 60000) {
    if (this.reportInterval) return

    this.reportInterval = setInterval(() => {
      this.printReport()

      // 如果命中率低且服务器请求多，建议启用 Redis
      if (this.shouldEnableRedis()) {
        console.warn('⚠️ 检测到高并发低命中率，建议考虑启用 Redis 缓存')
      }
    }, intervalMs)
  }

  // 停止定期报告
  stopReporting() {
    if (this.reportInterval) {
      clearInterval(this.reportInterval)
      this.reportInterval = null
    }
  }

  // 判断是否应该启用 Redis
  shouldEnableRedis() {
    const report = this.getReport()

    // 条件1：服务器请求频率高（>10次/分钟）
    const highFrequency = parseFloat(report.requestsPerMinute) > 10

    // 条件2：缓存命中率低（<50%）
    const lowHitRate = parseFloat(report.cacheHitRate) < 50

    // 条件3：平均响应时间长（>300ms）
    const slowResponse = report.avgResponseTime > 300

    // 满足任意两个条件就建议启用 Redis
    const conditions = [highFrequency, lowHitRate, slowResponse]
    const metConditions = conditions.filter(Boolean).length

    return metConditions >= 2
  }

  // 导出统计数据（用于发送到后端分析）
  exportStats() {
    return {
      timestamp: new Date().toISOString(),
      stats: this.getReport(),
      userAgent: navigator.userAgent,
      platform: navigator.platform
    }
  }
}

// 创建全局单例
export const cacheMonitor = new CacheMonitor()

// 开发环境自动启动监控
if (process.env.NODE_ENV === 'development') {
  cacheMonitor.startReporting(60000)  // 每分钟报告一次
}
