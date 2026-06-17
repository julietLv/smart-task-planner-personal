<template>
  <!-- 全屏模式（传送到 body） -->
  <teleport to="body" v-if="isFullscreen">
    <transition name="fullscreen-fade">
      <div class="fullscreen-overlay" @click.self="toggleFullscreen">
        <div class="fullscreen-backdrop" @click.self="toggleFullscreen"></div>
        <div class="fullscreen-chat-container">
          <el-card class="chat-window fullscreen-mode" shadow="always">
            <template #header>
              <div class="chat-header">
                <span class="header-title">💬 {{ assistantDisplayName }}智能助手</span>
                <div class="header-actions">
                  <el-button size="small" @click="clearChat" text>清空对话</el-button>
                  <el-button size="small" @click="toggleFullscreen" :icon="Close" text class="fullscreen-btn">退出全屏</el-button>
                </div>
              </div>
            </template>

            <div ref="messagesContainerRef" class="chat-messages" @scroll="handleMessagesScroll">
                <!-- ⭐ 新消息提示 -->
            <div v-if="isUserScrolling && hasNewMessage" class="new-message-indicator" @click="scrollToNewMessage">
              <span class="arrow-icon">↓</span>
              <span>有新消息</span>
            </div>

              <div v-for="(msg, index) in messages" :key="index" class="message-wrapper">
                <div v-if="shouldShowTimestamp(index)" class="message-timestamp">
                  <span class="timestamp-badge">{{ formatMessageTime(msg.timestamp) }}</span>
                </div>

                <div v-if="msg.role === 'user'" class="message user-message">
                  <div class="message-avatar user-avatar">🐱</div>
                  <div class="message-content user-content">{{ msg.content }}</div>
                </div>

                <div v-else class="message system-message">
                  <div class="message-avatar system-avatar">🤖</div>
                  <div class="message-content system-content">
                    <!-- 周报特殊样式 -->
                    <div v-if="msg.isReport" class="report-content">
                      <div class="markdown-content report-markdown" v-html="renderMarkdown(msg.content)"></div>

                      <!-- ⭐ Word 下载按钮 -->
                      <div v-if="msg.reportData?.word_available" class="report-download-actions">
                        <el-button
                          type="primary"
                          size="small"
                          @click="downloadWordReport(1, msg.reportData.time_range || 'this_week')"
                          :icon="Download"
                        >
                          📄 下载 Word 版本
                        </el-button>
                      </div>
                    </div>

                    <!-- 普通消息 -->
                    <div v-else class="message-text markdown-content" v-html="renderMarkdown(msg.content)"></div>

                    <!-- 时间调整提示动画 -->
                    <transition name="adjustment-slide">
                      <div v-if="msg.timeAdjusted" class="time-adjustment-notice">
                        <div class="adjustment-icon">💡</div>
                        <div class="adjustment-content">
                          <p class="adjustment-title">时间已自动优化</p>
                          <p class="adjustment-detail">{{ msg.adjustmentReason }}</p>
                        </div>
                        <div class="adjustment-badge">
                          <span class="pulse-dot"></span>
                          智能排程
                        </div>
                      </div>
                    </transition>

                    <div v-if="msg.taskPreview && !msg.confirmed" class="task-preview">
                      <!-- 任务基本信息 -->
                      <el-alert
                        :title="`📝 识别到任务：${msg.taskPreview.title || '未命名'}`"
                        type="info"
                        :closable="false"
                        show-icon
                      >
                        <template #default>
                          <div class="preview-details">
                            <p v-if="msg.taskPreview.start_time && msg.taskPreview.end_time">
                              🕐 请求时间：{{ formatDateTime(msg.taskPreview.start_time) }} - {{ formatDateTime(msg.taskPreview.end_time) }}
                            </p>
                            <p v-if="msg.taskPreview.duration">⏱️ 时长：{{ msg.taskPreview.duration }}分钟</p>
                            <p v-if="msg.taskPreview.priority">🎯 优先级：{{ getPriorityText(msg.taskPreview.priority) }}</p>
                          </div>
                        </template>
                      </el-alert>

                      <!-- ⭐ 冲突详情展示 - 时间轴对比卡片 -->
                      <div v-if="msg.hasConflict" class="conflict-timeline-card">
                        <div class="conflict-header">
                          <span class="conflict-icon"></span>
                          <span class="conflict-title">时间冲突提醒</span>
                          <span class="conflict-count">{{ msg.conflicts?.length || 0 }} 个任务重叠</span>
                        </div>

                        <div class="timeline-visualization">
                          <div class="timeline-header">
                            <span class="timeline-label">时间轴对比</span>
                          </div>
                          <div class="timeline-bars">
                            <div v-for="(conflict, idx) in msg.conflicts" :key="idx" class="conflict-bar-group">
                              <div class="conflict-bar existing-task">
                                <span class="bar-label">{{ conflict.conflicting_task_title }}</span>
                                <span class="bar-time">{{ formatTime(conflict.conflicting_time.start) }} - {{ formatTime(conflict.conflicting_time.end) }}</span>
                              </div>
                              <div class="conflict-bar new-task">
                                <span class="bar-label">{{ msg.taskPreview?.title || '新任务' }}</span>
                                <span class="bar-time">{{ formatTime(msg.taskPreview?.start_time) }} - {{ formatTime(msg.taskPreview?.end_time) }}</span>
                                <span class="overlap-badge">⚡ 重叠</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <div class="conflict-summary">
                          <el-icon class="summary-icon"><WarningFilled /></el-icon>
                          <span class="summary-text">
                            检测到与 <strong>{{ msg.conflicts[0]?.conflicting_task_title }}</strong> 等 {{ msg.conflicts.length }} 个任务时间重叠
                          </span>
                        </div>
                      </div>

                      <!-- ⭐ 无冲突时的简单确认 -->
                      <div v-if="!msg.hasConflict" class="preview-actions simple-confirm">
                        <el-button type="primary" size="small" @click="confirmAddTask(msg)" :loading="loading">
                          ✅ 确认添加
                        </el-button>
                        <el-button size="small" @click="modifyTask(msg)">✏️ 修改</el-button>
                      </div>

                      <!-- ⭐ 有冲突时的智能排程方案展示 -->
                      <div v-else class="conflict-resolution-panel">
                        <!-- 推荐方案卡片 -->
                        <div v-if="msg.recommendedSolution" class="recommended-solution-card">
                          <div class="card-header">
                            <div class="header-left">
                              <span class="recommend-badge">🤖 智能推荐</span>
                              <span class="solution-score">评分: {{ msg.recommendedSolution.score }}</span>
                            </div>
                          </div>

                          <div class="card-body">
                            <div class="solution-time">
                               {{ formatSolutionTime(msg.recommendedSolution.start_time) }} - {{ formatSolutionTime(msg.recommendedSolution.end_time) }}
                            </div>

                            <div class="solution-advantages">
                              <p class="advantages-title">✨ 方案优势</p>
                              <p v-for="(reason, idx) in msg.recommendedSolution.reasons" :key="idx" class="advantage-item">
                                ✓ {{ reason }}
                              </p>
                            </div>

                            <!-- ⭐ 新增：为什么推荐 -->
                            <div v-if="msg.recommendedSolution.summary" class="solution-summary">
                              <div class="summary-header">
                                <el-icon class="summary-icon"><Lightning /></el-icon>
                                <span class="summary-title">💡 为什么推荐这个时间段？</span>
                              </div>
                              <p class="summary-content">{{ msg.recommendedSolution.summary }}</p>
                            </div>
                          </div>

                          <!-- 洞察图标 -->
                          <div class="insight-trigger" @click.stop="openSolutionDetail(msg, msg.recommendedSolution)">
                            <el-icon class="insight-icon"><InfoFilled /></el-icon>
                          </div>

                          <div class="card-actions">
                            <el-button
                              type="success"
                              size="large"
                              @click="useRecommendedSolution(msg)"
                              :loading="loading"
                              class="use-recommended-btn"
                            >
                              ✅ 使用此方案
                            </el-button>
                          </div>
                        </div>

                        <!-- 备选方案列表 -->
                        <div v-if="msg.alternativeSolutions && msg.alternativeSolutions.length > 0" class="alternative-solutions">
                          <p class="alternatives-title">📦 其他可选方案：</p>

                          <div
                            v-for="(solution, idx) in msg.alternativeSolutions.slice(0, 2)"
                            :key="idx"
                            class="alternative-solution-item"
                          >
                            <div class="alt-header">
                              <div class="alt-header-left">
                                <span class="alt-badge">方案{{ idx + 2 }}</span>
                                <span class="alt-time">{{ formatSolutionTime(solution.start_time) }} - {{ formatSolutionTime(solution.end_time) }}</span>
                                <span class="alt-score">评分: {{ solution.score }}</span>
                              </div>
                            </div>

                            <div class="alt-body">
                              <div class="alt-advantages">
                                <span v-if="solution.reasons && solution.reasons.length > 0" class="advantage-text">
                                  ✓ {{ solution.reasons[0] }}
                                </span>
                              </div>

                              <!--  新增：备选方案总结 -->
                              <div v-if="solution.summary" class="alt-summary">
                                <span class="alt-summary-icon">💬</span>
                                <span class="alt-summary-text">{{ solution.summary }}</span>
                              </div>
                            </div>

                            <!-- 洞察图标 -->
                            <div class="insight-trigger" @click.stop="openSolutionDetail(msg, solution)">
                              <el-icon class="insight-icon"><InfoFilled /></el-icon>
                            </div>

                            <el-button
                              size="small"
                              plain
                              @click="useAlternativeSolution(msg, solution)"
                              :loading="loading"
                              class="alt-action-btn"
                            >
                              选择此方案
                            </el-button>
                          </div>
                        </div>

                        <!-- 其他操作 -->
                        <div class="other-actions">
                          <el-divider />
                          <div class="action-buttons-row">
                            <el-button
                              type="warning"
                              size="small"
                              @click="ignoreConflict(msg)"
                              :loading="loading"
                            >
                              ⚠️ 忽略冲突，强制创建
                            </el-button>
                            <el-button
                              type="danger"
                              size="small"
                              @click="cancelAddTask(msg)"
                            >
                              ❌ 取消添加
                            </el-button>
                          </div>
                        </div>
                      </div>

                      <!-- 详情面板 -->
                      <SolutionDetailPanel
                        v-if="detailPanelVisible"
                        :visible="detailPanelVisible"
                        :solution="currentSolution"
                        :task-preview="currentTaskPreview"
                        @close="closeSolutionDetail"
                        @adopt="handleAdoptSolution"
                      />
                    </div>

                    <!-- 任务已成功添加后的反馈展示 -->
                    <div v-if="msg.taskCreated && msg.createdTask" class="task-success-feedback">
                      <div class="compact-task-card">
                        <div class="compact-card-header">
                          <span class="success-icon">✅</span>
                          <span class="success-text">任务已添加</span>
                          <el-button type="warning" size="small" plain @click="modifyTaskAfterConfirm(msg)">✏️ 修改</el-button>
                        </div>
                        <div class="compact-card-body">
                          <span class="task-info">{{ msg.createdTask.title }}</span>
                          <span v-if="msg.createdTask.start_time" class="task-info">🕐 {{ formatTime(msg.createdTask.start_time) }}-{{ formatTime(msg.createdTask.end_time) }}</span>
                          <span v-if="msg.createdTask.duration" class="task-info">⏱️ {{ msg.createdTask.duration }}分钟</span>
                          <span v-if="msg.createdTask.priority" class="task-info">🎯 {{ getPriorityText(msg.createdTask.priority) }}</span>
                        </div>
                      </div>
                    </div>

                    <div v-if="msg.suggestions && msg.suggestions.length > 0" class="suggestions">
                      <p class="suggestions-title">💡 建议：</p>
                      <ul>
                        <li v-for="(suggestion, idx) in msg.suggestions" :key="idx">{{ suggestion }}</li>
                      </ul>
                    </div>

                    <!-- P0: 连续性标记警告 -->
                    <div v-if="msg.can_complete_continuously === false" class="continuity-warning">
                      <el-alert
                        title="⚠️ 任务无法连续完成"
                        type="warning"
                        :closable="false"
                        show-icon
                        description="当前时段较为碎片化，建议查看下方拆分方案或调整任务时长"
                      />
                    </div>

                    <!-- 负荷警告 -->
                    <div v-if="msg.load_warning" class="continuity-warning">
                      <el-alert
                        title="📊 当天任务接近饱和"
                        type="info"
                        :closable="false"
                        show-icon
                        :description="msg.load_warning"
                      />
                    </div>

                    <!-- P1: 拆分建议展示 -->
                    <div v-if="msg.split_suggestions && msg.split_suggestions.length > 0" class="split-suggestions">
                      <p class="split-title">📋 任务拆分建议：</p>
                      <div class="split-timeline">
                        <div
                          v-for="(segment, idx) in msg.split_suggestions"
                          :key="idx"
                          class="split-segment-card"
                        >
                          <div class="segment-header">
                            <span class="segment-number">段 {{ segment.segment }}</span>
                            <el-tag size="small" type="info">{{ segment.reason }}</el-tag>
                          </div>
                          <div class="segment-time">
                            🕐 {{ formatTime(segment.start_time) }} - {{ formatTime(segment.end_time) }}
                            <span class="segment-duration">（{{ segment.duration }}分钟）</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <ReportChart v-if="msg.chartData" :chart-data="msg.chartData" />
                  </div> <!-- 闭合 system-content -->
                </div> <!-- 闭合 system-message -->
              </div> <!-- 闭合 message-wrapper -->

              <div v-if="loading" class="typing-indicator">
                <span>🤖</span>
                <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>
              </div>
            </div> <!-- 闭合 chat-messages -->

            <div class="chat-input-area">
              <transition name="voice-panel">
                <div v-if="isVoiceInput" class="voice-input-overlay">
                  <div class="voice-panel-content">
                    <el-button class="close-voice-btn" circle size="small" @click="stopVoiceInput">
                      <el-icon><Close /></el-icon>
                    </el-button>
                    <div class="waveform-wrapper">
                      <canvas ref="waveformCanvas" width="300" height="60"></canvas>
                    </div>
                    <p class="voice-status">{{ voiceStatus }}</p>
                  </div>
                </div>
              </transition>

              <el-input v-model="inputMessage" type="textarea" :rows="4" placeholder="输入消息，例如：&#10;• 明天下午3点开会&#10;• 查看我的任务&#10;• 添加数学作业，周三截止" @keydown.enter.ctrl="sendMessage" :disabled="loading" resize="none" />
              <div class="input-actions">
                <span class="hint-text">按 Ctrl+Enter 发送</span>
                <div class="action-buttons">
                  <el-button type="success" circle @click="toggleVoiceInput" :class="{ 'recording': isVoiceInput }" title="语音输入">
                    <el-icon><Microphone /></el-icon>
                  </el-button>
                  <el-button type="primary" @click="sendMessage" :loading="loading" :disabled="!inputMessage.trim()">发送</el-button>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </transition>
  </teleport>

  <!-- 非全屏模式 -->
  <el-card v-else class="chat-window" shadow="never">
    <template #header>
      <div class="chat-header">
        <span class="header-title">💬 {{ assistantDisplayName }}智能助手</span>
        <div class="header-actions">
          <el-button size="small" @click="clearChat" text>清空对话</el-button>
          <el-button size="small" @click="toggleFullscreen" :icon="FullScreen" text class="fullscreen-btn">全屏</el-button>
        </div>
      </div>
    </template>

       <ChatWindowSkeleton v-if="isLoading" />

    <div v-else ref="messagesContainerRef" class="chat-messages">

      <div v-for="(msg, index) in messages" :key="index" class="message-wrapper">
        <div v-if="shouldShowTimestamp(index)" class="message-timestamp">
          <span class="timestamp-badge">{{ formatMessageTime(msg.timestamp) }}</span>
        </div>

        <div v-if="msg.role === 'user'" class="message user-message">
          <div class="message-avatar user-avatar">🐱</div>
          <div class="message-content user-content">{{ msg.content }}</div>
        </div>

        <div v-else class="message system-message">
          <div class="message-avatar system-avatar">🤖</div>
          <div class="message-content system-content">

        <!-- 周报特殊样式 -->
        <div v-if="msg.isReport" class="report-content">
          <div class="markdown-content report-markdown" v-html="renderMarkdown(msg.content)"></div>

          <!-- Word 下载按钮 -->
          <div v-if="msg.reportData?.word_available" class="report-download-actions">
            <el-button
              type="primary"
              size="small"
              @click="downloadWordReport(1, msg.reportData.time_range || 'this_week')"
              :icon="Download"
            >
               下载 Word 版本
            </el-button>
          </div>
        </div>
<!-- 普通消息 -->
<div v-else class="message-text markdown-content" v-html="renderMarkdown(msg.content)"></div>

<div v-if="msg.taskPreview && !msg.confirmed" class="task-preview">


              <el-alert :title="`识别到任务：${msg.taskPreview.title || '未命名'}`" type="info" :closable="false" show-icon>
                <template #default>
                  <div class="preview-details">
                    <p v-if="msg.taskPreview.start_time && msg.taskPreview.end_time">🕐 时间：{{ formatDateTime(msg.taskPreview.start_time) }} - {{ formatDateTime(msg.taskPreview.end_time) }}</p>
                    <p v-if="msg.taskPreview.deadline">📅 截止时间：{{ formatDateTime(msg.taskPreview.deadline) }}</p>
                    <p v-if="msg.taskPreview.duration">⏱️ 预估时长：{{ msg.taskPreview.duration }}分钟</p>
                    <p v-if="msg.taskPreview.priority">🎯 优先级：{{ getPriorityText(msg.taskPreview.priority) }}</p>
                  </div>
                </template>
              </el-alert>

              <!-- ⭐ 冲突详情展示 - 时间轴对比卡片 -->
              <div v-if="msg.hasConflict" class="conflict-timeline-card">
                <div class="conflict-header">
                  <span class="conflict-icon"></span>
                  <span class="conflict-title">时间冲突提醒</span>
                  <span class="conflict-count">{{ msg.conflicts?.length || 0 }} 个任务重叠</span>
                </div>

                <div class="timeline-visualization">
                  <div class="timeline-header">
                    <span class="timeline-label">时间轴对比</span>
                  </div>
                  <div class="timeline-bars">
                    <div v-for="(conflict, idx) in msg.conflicts" :key="idx" class="conflict-bar-group">
                      <div class="conflict-bar existing-task">
                        <span class="bar-label">{{ conflict.conflicting_task_title }}</span>
                        <span class="bar-time">{{ formatTime(conflict.conflicting_time.start) }} - {{ formatTime(conflict.conflicting_time.end) }}</span>
                      </div>
                      <div class="conflict-bar new-task">
                        <span class="bar-label">{{ msg.taskPreview?.title || '新任务' }}</span>
                        <span class="bar-time">{{ formatTime(msg.taskPreview?.start_time) }} - {{ formatTime(msg.taskPreview?.end_time) }}</span>
                        <span class="overlap-badge">⚡ 重叠</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="conflict-summary">
                  <el-icon class="summary-icon"><WarningFilled /></el-icon>
                  <span class="summary-text">
                    检测到与 <strong>{{ msg.conflicts[0]?.conflicting_task_title }}</strong> 等 {{ msg.conflicts.length }} 个任务时间重叠
                  </span>
                </div>
              </div>

              <div v-if="!msg.hasConflict" class="preview-actions simple-confirm">
                <el-button type="primary" size="small" @click="confirmAddTask(msg)" :loading="loading">
                  ✅ 确认添加
                </el-button>
                <el-button size="small" @click="modifyTask(msg)">✏️ 修改</el-button>
              </div>

              <!-- 非全屏模式的智能排程方案展示 -->
              <div v-else class="conflict-resolution-panel">
                <!-- 推荐方案卡片 -->
                <div v-if="msg.recommendedSolution" class="recommended-solution-card">
                  <div class="card-header">
                    <div class="header-left">
                      <span class="recommend-badge">🤖 智能推荐</span>
                      <span class="solution-score">评分: {{ msg.recommendedSolution.score }}</span>
                    </div>
                  </div>

                  <div class="card-body">
                    <div class="solution-time">
                      📅 {{ formatSolutionTime(msg.recommendedSolution.start_time) }} - {{ formatSolutionTime(msg.recommendedSolution.end_time) }}
                    </div>

                    <div class="solution-advantages">
                      <p v-for="(reason, idx) in msg.recommendedSolution.reasons" :key="idx" class="advantage-item">
                        ✓ {{ reason }}
                      </p>
                    </div>
                  </div>

                  <div class="insight-trigger" @click.stop="openSolutionDetail(msg, msg.recommendedSolution)">
                    <el-icon class="insight-icon"><InfoFilled /></el-icon>
                  </div>

                  <div class="card-actions">
                    <el-button
                      type="success"
                      size="large"
                      @click="useRecommendedSolution(msg)"
                      :loading="loading"
                      class="use-recommended-btn"
                    >
                      ✅ 使用此方案
                    </el-button>
                  </div>
                </div>

                <!-- 备选方案列表 -->
                <div v-if="msg.alternativeSolutions && msg.alternativeSolutions.length > 0" class="alternative-solutions">
                  <p class="alternatives-title">📦 其他可选方案：</p>

                  <div
                    v-for="(solution, idx) in msg.alternativeSolutions.slice(0, 2)"
                    :key="idx"
                    class="alternative-solution-item"
                  >
                    <div class="alt-header">
                      <div class="alt-header-left">
                        <span class="alt-badge">方案{{ idx + 2 }}</span>
                        <span class="alt-time">{{ formatSolutionTime(solution.start_time) }} - {{ formatSolutionTime(solution.end_time) }}</span>
                        <span class="alt-score">评分: {{ solution.score }}</span>
                      </div>
                    </div>

                    <div class="alt-body">
                      <div class="alt-advantages">
                        <span v-if="solution.reasons && solution.reasons.length > 0" class="advantage-text">
                          ✓ {{ solution.reasons[0] }}
                        </span>
                      </div>

                      <div v-if="solution.summary" class="alt-summary">
                        <span class="alt-summary-icon">💬</span>
                        <span class="alt-summary-text">{{ solution.summary }}</span>
                      </div>
                    </div>

                    <div class="insight-trigger" @click.stop="openSolutionDetail(msg, solution)">
                      <el-icon class="insight-icon"><InfoFilled /></el-icon>
                    </div>

                    <el-button
                      size="small"
                      plain
                      @click="useAlternativeSolution(msg, solution)"
                      :loading="loading"
                      class="alt-action-btn"
                    >
                      选择此方案
                    </el-button>
                  </div>
                </div>

                <!-- 其他操作 -->
                <div class="other-actions">
                  <el-divider />
                  <div class="action-buttons-row">
                    <el-button
                      type="warning"
                      size="small"
                      @click="ignoreConflict(msg)"
                      :loading="loading"
                    >
                      ⚠️ 忽略冲突，强制创建
                    </el-button>
                    <el-button
                      type="danger"
                      size="small"
                      @click="cancelAddTask(msg)"
                    >
                      ❌ 取消添加
                    </el-button>
                  </div>
                </div>
              </div>

              <!-- 详情面板 -->
              <SolutionDetailPanel
                v-if="detailPanelVisible"
                :visible="detailPanelVisible"
                :solution="currentSolution"
                :task-preview="currentTaskPreview"
                @close="closeSolutionDetail"
                @adopt="handleAdoptSolution"
              />

              <!-- 任务已成功添加后的反馈展示 -->
              <div v-if="msg.taskCreated && msg.createdTask" class="task-success-feedback">
                <div class="compact-task-card">
                  <div class="compact-card-header">
                    <span class="success-icon">✅</span>
                    <span class="success-text">任务已添加</span>
                    <el-button type="warning" size="small" plain @click="modifyTaskAfterConfirm(msg)">✏️ 修改</el-button>
                  </div>
                  <div class="compact-card-body">
                    <span class="task-info">{{ msg.createdTask.title }}</span>
                    <span v-if="msg.createdTask.start_time" class="task-info">🕐 {{ formatTime(msg.createdTask.start_time) }}-{{ formatTime(msg.createdTask.end_time) }}</span>
                    <span v-if="msg.createdTask.duration" class="task-info">⏱️ {{ msg.createdTask.duration }}分钟</span>
                    <span v-if="msg.createdTask.priority" class="task-info">🎯 {{ getPriorityText(msg.createdTask.priority) }}</span>
                  </div>
                </div>
              </div>

              <div v-if="msg.suggestions && msg.suggestions.length > 0" class="suggestions">
                <p class="suggestions-title">💡 建议：</p>
                <ul>
                  <li v-for="(suggestion, idx) in msg.suggestions" :key="idx">{{ suggestion }}</li>
                </ul>
              </div>

              <!-- P0: 连续性标记警告 -->
              <div v-if="msg.can_complete_continuously === false" class="continuity-warning">
                <el-alert
                  title="⚠️ 任务无法连续完成"
                  type="warning"
                  :closable="false"
                  show-icon
                  description="当前时段较为碎片化，建议查看下方拆分方案或调整任务时长"
                />
              </div>

              <!-- 负荷警告 -->
              <div v-if="msg.load_warning" class="continuity-warning">
                <el-alert
                  title="📊 当天任务接近饱和"
                  type="info"
                  :closable="false"
                  show-icon
                  :description="msg.load_warning"
                />
              </div>

              <!-- P1: 拆分建议展示 -->
              <div v-if="msg.split_suggestions && msg.split_suggestions.length > 0" class="split-suggestions">
                <p class="split-title">📋 任务拆分建议：</p>
                <div class="split-timeline">
                  <div
                    v-for="(segment, idx) in msg.split_suggestions"
                    :key="idx"
                    class="split-segment-card"
                  >
                    <div class="segment-header">
                      <span class="segment-number">段 {{ segment.segment }}</span>
                      <el-tag size="small" type="info">{{ segment.reason }}</el-tag>
                    </div>
                    <div class="segment-time">
                      🕐 {{ formatTime(segment.start_time) }} - {{ formatTime(segment.end_time) }}
                      <span class="segment-duration">（{{ segment.duration }}分钟）</span>
                    </div>
                  </div>
                </div>
              </div>

              <ReportChart v-if="msg.chartData" :chart-data="msg.chartData" />
            </div> <!-- 闭合 system-content -->
          </div> <!-- 闭合 system-message -->
        </div> <!-- 闭合 message-wrapper -->

        <div v-if="loading" class="typing-indicator">
          <span>🤖</span>
          <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>
        </div>
      </div>
    </div> <!-- 闭合 chat-messages -->

    <div class="chat-input-area">
      <transition name="voice-panel">
        <div v-if="isVoiceInput" class="voice-input-overlay">
          <div class="voice-panel-content">
            <el-button class="close-voice-btn" circle size="small" @click="stopVoiceInput">
              <el-icon><Close /></el-icon>
            </el-button>
            <div class="waveform-wrapper">
              <canvas ref="waveformCanvas" width="300" height="60"></canvas>
            </div>
            <p class="voice-status">{{ voiceStatus }}</p>
          </div>
        </div>
      </transition>

      <el-input v-model="inputMessage" type="textarea" :rows="3" placeholder="输入消息，例如：&#10;• 明天下午3点开会&#10;• 查看我的任务&#10;• 添加数学作业，周三截止" @keydown.enter.ctrl="sendMessage" :disabled="loading" resize="none" />
      <div class="input-actions">
        <span class="hint-text">按 Ctrl+Enter 发送</span>
        <div class="action-buttons">
          <el-button type="success" circle @click="toggleVoiceInput" :class="{ 'recording': isVoiceInput }" title="语音输入">
            <el-icon><Microphone /></el-icon>
          </el-button>
          <el-button type="primary" @click="sendMessage" :loading="loading" :disabled="!inputMessage.trim()">发送</el-button>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { FullScreen, Close, Microphone, InfoFilled, Download, WarningFilled, Lightning } from '@element-plus/icons-vue'

import { taskApi } from '../api/taskApi'
import { useTaskStore } from '../stores/taskStore'
import { marked } from 'marked'

// ⭐ marked v11+ 新 API：使用 use() 方法配置 GFM
marked.use({
  gfm: true,
  breaks: true
})

import ReportChart from './ReportChart.vue'

import SolutionDetailPanel from './SolutionDetailPanel.vue'
import SkeletonLoader from './SkeletonLoader.vue'
import ChatWindowSkeleton from './ChatWindowSkeleton.vue'
import { websocketService } from '../services/websocketService'

const taskStore = useTaskStore()
const messagesContainerRef = ref(null)
const loading = ref(false)
const inputMessage = ref('')
const isFullscreen = ref(false)
const isVoiceInput = ref(false)

let recognition = null
let audioContext = null
let analyser = null
let microphone = null
let animationId = null
let dataArray = null
const waveformCanvas = ref(null)
const voiceStatus = ref('点击开始录音')
const hasPermission = ref(false)

// 详情面板状态
const detailPanelVisible = ref(false)
const currentSolution = ref({})
const currentTaskPreview = ref({})
const currentMessage = ref(null)

const userNickname = computed(() => {
  return taskStore.preferences?.user_nickname || ''
})

const assistantNickname = computed(() => {
  return taskStore.preferences?.assistant_nickname || ''
})

const assistantDisplayName = computed(() => {
  return assistantNickname.value ? `${assistantNickname.value}·` : ''
})

const messages = ref([
  {
    role: 'system',
    content: '您好！我是智能任务规划助手。我可以帮您：\n• 添加任务（例如："明天下午3点开会"）\n• 查询日程（例如："查看我的任务"）\n• 修改设置（例如："设置免安排时间"）\n\n请问有什么可以帮您的？',
    timestamp: new Date().toISOString()
  }
])


// ... existing code ...
// ⭐ 滚动状态检测
const isUserScrolling = ref(false)
const hasNewMessage = ref(false)
const lastMessageCount = ref(0)

let scrollTimer = null

// ⭐ 防止重复提交周报任务的标记
const isGeneratingReport = ref(false)

const isLoading = ref(true)


function renderMarkdown(content) {
  if (!content) return ''

  const result = marked.parse(content)

  // ⭐ 调试：检测表格渲染情况
  if (content.includes('|') && content.includes('\n')) {
    console.log('📊 [表格诊断] 检测到 Markdown 表格')
    console.log('  - 输入内容前 200 字符:', content.substring(0, 200))
    console.log('  - 输出包含 <table>:', result.includes('<table>'))
    console.log('  - 输出包含 <thead>:', result.includes('<thead>'))
    console.log('  - 输出包含 <tbody>:', result.includes('<tbody>'))
    console.log('  - 输出 HTML 前 300 字符:', result.substring(0, 300))
  }

  return result
}



function shouldShowTimestamp(index) {
  if (index === 0) return true
  const currentMsg = messages.value[index]
  const prevMsg = messages.value[index - 1]
  if (!currentMsg.timestamp || !prevMsg.timestamp) return false
  const currentTime = new Date(currentMsg.timestamp)
  const prevTime = new Date(prevMsg.timestamp)
  const diffMinutes = (currentTime - prevTime) / (1000 * 60)
  return diffMinutes >= 5
}

function formatMessageTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  if (isFullscreen.value) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
}

function handleKeyDown(event) {
  if (event.key === 'Escape' && isFullscreen.value) {
    toggleFullscreen()
  }
  if (event.ctrlKey && event.shiftKey && event.key === 'F') {
    event.preventDefault()
    toggleFullscreen()
  }
}

// ... existing code ...
async function sendMessage() {
  if (!inputMessage.value.trim() || loading.value) return

  const message = inputMessage.value.trim()

  // ⭐ 检测是否是生成周报的请求
  const isReportRequest = message.includes('生成周报') || message.includes('周报') || message.includes('报告')

  // ⭐ 如果正在生成周报，阻止重复提交
  if (isReportRequest && isGeneratingReport.value) {
    ElMessage.warning('周报正在生成中，请稍等片刻～')
    return
  }

  // ⭐ 如果是周报请求，先检查 WebSocket 连接状态
  if (isReportRequest) {
    if (!websocketService.isConnected) {
      ElMessage.warning('⚠️ WebSocket 未连接，请刷新页面后重试')
      console.warn('❌ WebSocket 未连接，无法接收周报推送')
      return
    }
    console.log('✅ WebSocket 已连接，可以发送周报请求')
  }

  inputMessage.value = ''
  loading.value = true

  // ⭐ 标记为正在生成周报
  if (isReportRequest) {
    isGeneratingReport.value = true
  }

  messages.value.push({
    role: 'user',
    content: message,
    timestamp: new Date().toISOString()
  })

  try {
    const response = await taskApi.sendMessage(message, 1)

    if (response.success) {
      const systemMsg = {
        role: 'system',
        content: response.reply,
        timestamp: new Date().toISOString()
      }

      if (response.data?.time_adjusted) {
        systemMsg.timeAdjusted = true
        systemMsg.adjustmentReason = response.data.adjustment_reason
      }

      if (response.task_preview) {
        systemMsg.taskPreview = response.task_preview
        systemMsg.confirmed = false
      }

      if (response.has_conflict) {
        systemMsg.hasConflict = true
        systemMsg.conflicts = response.conflicts || []
        systemMsg.recommendedSolution = response.recommendedSolution || null
        systemMsg.alternativeSolutions = response.alternativeSolutions || []
        systemMsg.confirmed = false
      }

      if (response.scheduled_time) {
        systemMsg.scheduledTime = response.scheduled_time
      }

      // ⭐ 修复：任务已自动创建（无冲突），标记消息状态
      if (response.task_created) {
        systemMsg.taskCreated = true
        systemMsg.createdTask = response.data?.task || {}
        systemMsg.confirmed = true
      }

      messages.value.push(systemMsg)
      await scrollToBottom()

      // ⭐ 修复：任务已自动创建，刷新日历
      if (response.task_created) {
        await taskStore.fetchTasks(1, null, true)
      }

      // ⭐ 如果是周报请求且后端返回 async=true，保持标记直到收到 WebSocket 推送
      if (isReportRequest && response.async) {
        console.log('✅ 周报任务已提交，等待 WebSocket 推送...')
      } else {
        // 非异步任务或普通任务，立即释放标记
        if (isReportRequest) {
          isGeneratingReport.value = false
        }
      }
    }
  } catch (error) {
    ElMessage.error('发送失败: ' + error.message)
    // ⭐ 失败时也要释放标记
    if (isReportRequest) {
      isGeneratingReport.value = false
    }
  } finally {
    loading.value = false
  }
}
// ... existing code ...

function toggleVoiceInput() {
  if (isVoiceInput.value) {
    stopVoiceInput()
  } else {
    startVoiceInput()
  }
}

async function startVoiceInput() {
  try {
    isVoiceInput.value = true
    voiceStatus.value = '正在初始化...'

    initSpeechRecognition()

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    hasPermission.value = true

    setupAudioVisualization(stream)

    if (recognition) {
      recognition.start()
      voiceStatus.value = '正在聆听...'
    }

    await nextTick()
    drawWaveform()

    ElMessage.success('语音输入已启动，请说话')
  } catch (error) {
    console.error('语音输入启动失败:', error)
    if (error.name === 'NotAllowedError') {
      ElMessage.error('麦克风权限被拒绝，请允许访问麦克风')
      hasPermission.value = false
    } else {
      ElMessage.error('语音输入启动失败: ' + error.message)
    }
    isVoiceInput.value = false
  }
}

function stopVoiceInput() {
  isVoiceInput.value = false
  voiceStatus.value = '点击开始录音'

  if (recognition) {
    recognition.stop()
  }

  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  if (microphone) {
    microphone.disconnect()
    microphone = null
  }

  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
}

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition

  if (!SpeechRecognition) {
    ElMessage.warning('您的浏览器不支持语音识别功能，请使用 Chrome 或 Edge 浏览器')
    return
  }

  recognition = new SpeechRecognition()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.lang = 'zh-CN'

  recognition.onresult = (event) => {
    let interim = ''
    let final = ''

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript
      if (event.results[i].isFinal) {
        final += transcript
      } else {
        interim += transcript
      }
    }

    if (interim || final) {
      const currentText = inputMessage.value
      if (final) {
        inputMessage.value = currentText ? currentText + final : final
      }
      if (interim) {
        voiceStatus.value = '识别中: ' + interim
      }
    }
  }

  recognition.onerror = (event) => {
    console.error('语音识别错误:', event.error)
    if (event.error === 'no-speech') {
      voiceStatus.value = '未检测到语音，请重试'
    } else if (event.error === 'not-allowed') {
      ElMessage.error('语音识别权限被拒绝')
      stopVoiceInput()
    }
  }

  recognition.onend = () => {
    if (isVoiceInput.value) {
      recognition.start()
    }
  }
}

function setupAudioVisualization(stream) {
  audioContext = new (window.AudioContext || window.webkitAudioContext)()
  analyser = audioContext.createAnalyser()
  analyser.fftSize = 256

  microphone = audioContext.createMediaStreamSource(stream)
  microphone.connect(analyser)

  const bufferLength = analyser.frequencyBinCount
  dataArray = new Uint8Array(bufferLength)
}

function drawWaveform() {
  if (!waveformCanvas.value || !analyser) return

  const canvas = waveformCanvas.value
  const ctx = canvas.getContext('2d')
  const WIDTH = canvas.width
  const HEIGHT = canvas.height

  function render() {
    if (!isVoiceInput.value) return

    animationId = requestAnimationFrame(render)

    analyser.getByteFrequencyData(dataArray)

    ctx.clearRect(0, 0, WIDTH, HEIGHT)

    const average = dataArray.reduce((a, b) => a + b) / dataArray.length
    const volume = average / 255

    const barWidth = (WIDTH / dataArray.length) * 2.5
    let x = 0

    for (let i = 0; i < dataArray.length; i++) {
      const barHeight = (dataArray[i] / 255) * HEIGHT * 0.8

      const hue = 200 + (volume * 60)
      const saturation = 70 + (volume * 30)
      const lightness = 50 + (volume * 20)

      ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`
      ctx.fillRect(x, HEIGHT - barHeight, barWidth, barHeight)

      x += barWidth + 1
    }

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(0, HEIGHT / 2)
    ctx.lineTo(WIDTH, HEIGHT / 2)
    ctx.stroke()
  }

  render()
}

async function confirmAddTask(msg) {
  if (!msg.taskPreview) return

  loading.value = true
  try {
    const response = await taskApi.sendMessage('确认', 1)

    if (response.success) {
      ElMessage.success(response.reply || '任务已添加')
      msg.confirmed = true
      await taskStore.fetchTasks(1, null, true)  // ⭐ forceRefresh 跳过缓存
      msg.confirmed = true
      messages.value.push({
        role: 'system',
        content: response.reply,
        timestamp: new Date().toISOString()
      })
      await scrollToBottom()
    }
  } catch (error) {
    ElMessage.error('自动调整失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

async function ignoreConflict(msg) {
  if (!msg.taskPreview) return

  loading.value = true
  try {
    const response = await taskApi.sendMessage('忽略冲突', 1)

    if (response.success) {
      ElMessage.success(response.reply || '已忽略冲突并添加任务')
      await taskStore.fetchTasks(1, null, true)
      msg.confirmed = true
      messages.value.push({
        role: 'system',
        content: response.reply,
        timestamp: new Date().toISOString()
      })
      await scrollToBottom()
    }
  } catch (error) {
    ElMessage.error('添加任务失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

function cancelAddTask(msg) {
  msg.confirmed = true
  messages.value.push({
    role: 'system',
    content: '❌ 已取消添加任务',
    timestamp: new Date().toISOString()
  })
  ElMessage.info('已取消')
  scrollToBottom()
}

function modifyTask(msg) {
  if (!msg.taskPreview) return

  inputMessage.value = `修改任务：${msg.taskPreview.title}，`
  msg.confirmed = false
  ElMessage.info('请在输入框中说明需要修改的内容')
}

function modifyTaskAfterConfirm(msg) {
  if (!msg.createdTask) return

  msg.taskPreview = { ...msg.createdTask }
  msg.taskData = { ...msg.createdTask }
  msg.taskCreated = false
  msg.confirmed = false

  inputMessage.value = `修改任务：${msg.createdTask.title}，`
  ElMessage.info('任务已恢复为可编辑状态，请在下方输入框说明修改内容')
}

function clearChat() {
  messages.value = [
    {
      role: 'system',
      content: '对话已清空。请问有什么可以帮您的？',
      timestamp: new Date().toISOString()
    }
  ]
  ElMessage.success('对话已清空')
}


function getPriorityText(priority) {
  const texts = {
    high: '高优先级',
    medium: '中优先级',
    low: '低优先级'
  }
  return texts[priority] || priority
}

function formatDateTime(datetime) {
  if (!datetime) return '无'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatTime(datetime) {
  if (!datetime) return '无'
  const date = new Date(datetime)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
// ⭐ 滚动到底部函数
async function scrollToBottom() {
  await nextTick()
  if (messagesContainerRef.value) {
    messagesContainerRef.value.scrollTop = messagesContainerRef.value.scrollHeight
  }
}

// ⭐ 处理消息容器滚动事件
function handleMessagesScroll(event) {
  const container = event.target
  const scrollTop = container.scrollTop
  const scrollHeight = container.scrollHeight
  const clientHeight = container.clientHeight

  // 判断用户是否正在向上滚动（距离底部超过 100px）
  isUserScrolling.value = scrollHeight - scrollTop - clientHeight > 100

  // 如果用户滚动到底部，隐藏新消息提示
  if (!isUserScrolling.value) {
    hasNewMessage.value = false
  }

  // 清除之前的定时器
  if (scrollTimer) {
    clearTimeout(scrollTimer)
  }

  // 设置防抖定时器，停止滚动 500ms 后重新检查位置
  scrollTimer = setTimeout(() => {
    const currentScrollTop = container.scrollTop
    const currentScrollHeight = container.scrollHeight
    const currentClientHeight = container.clientHeight

    isUserScrolling.value = currentScrollHeight - currentScrollTop - currentClientHeight > 100
  }, 500)
}

// ⭐ 滚动到新消息位置
function scrollToNewMessage() {
  hasNewMessage.value = false
  isUserScrolling.value = false
  scrollToBottom()
}

// ⭐ 监听消息变化（从 onMounted 中移出来）
watch(messages, (newVal) => {
  if (newVal.length > lastMessageCount.value) {
    // 有新消息到达
    if (isUserScrolling.value) {
      hasNewMessage.value = true
    } else {
      scrollToBottom()
    }
    lastMessageCount.value = newVal.length
  }
}, { deep: true })


async function initNickname() {
  try {
    await taskStore.fetchPreferences()

    if (assistantNickname.value) {
      const confirmMsg = `我已经确认，您给我起的名字是「${assistantNickname.value}」。${userNickname.value ? `我会称呼您为「${userNickname.value}」。` : ''}请问有什么可以帮您的？`

      messages.value[0] = {
        role: 'system',
        content: confirmMsg,
        timestamp: new Date().toISOString()
      }
    }
  } catch (error) {
    console.error('获取称谓失败:', error)
  }
}

// 打开详情面板
function openSolutionDetail(msg, solution) {
  currentMessage.value = msg
  currentSolution.value = solution
  currentTaskPreview.value = msg.taskPreview || {}
  detailPanelVisible.value = true
}

// 关闭详情面板
function closeSolutionDetail() {
  detailPanelVisible.value = false
  currentSolution.value = {}
  currentTaskPreview.value = {}
  currentMessage.value = null
}

// 采纳方案
async function handleAdoptSolution(solution) {
  if (!currentMessage.value) return

  try {
    await useAlternativeSolution(currentMessage.value, solution)
  } catch (error) {
    console.error('采纳方案失败:', error)
  }
}

// 卡片悬停处理（预留）
function handleCardHover(msg, type, idx = 0) {
  console.log('Card hover:', type, idx)
}

async function useRecommendedSolution(msg) {
  if (!msg.taskPreview || !msg.recommendedSolution) return
  // ⭐ 防重复点击：检查是否已在处理中或已确认
  if (msg._adopting || msg.confirmed) return
  msg._adopting = true

  loading.value = true
  try {
    const response = await taskStore.confirmTask({
      action: 'auto_adjust',
      task_data: {
        ...msg.taskPreview,
        preferred_start_time: msg.recommendedSolution.start_time,
        preferred_end_time: msg.recommendedSolution.end_time
      },
      user_id: 1
    })

    if (response && response.success) {
      ElMessage.success(response.message || '任务已成功添加')
      await taskStore.fetchTasks(1, null, true)  // ⭐ forceRefresh 跳过缓存
      msg.confirmed = true

      messages.value.push({
        role: 'system',
        content: `✅ 任务「${response.task?.title || msg.taskPreview.title}」已添加到 ${formatSolutionTime(response.task?.start_time)}-${formatSolutionTime(response.task?.end_time)}`,
        timestamp: new Date().toISOString(),
        createdTask: response.task
      })
      await scrollToBottom()
    } else {
      ElMessage.error(response?.message || '添加任务失败')
    }
  } catch (error) {
    ElMessage.error('添加任务失败: ' + error.message)
  } finally {
    loading.value = false
    msg._adopting = false
  }
}

async function useAlternativeSolution(msg, solution) {
  if (!msg.taskPreview || !solution) return
  // ⭐ 防重复点击：检查是否已在处理中或已确认
  if (msg._adopting || msg.confirmed) return
  msg._adopting = true

  loading.value = true
  try {
    const response = await taskStore.confirmTask({
      action: 'auto_adjust',
      task_data: {
        ...msg.taskPreview,
        preferred_start_time: solution.start_time,
        preferred_end_time: solution.end_time
      },
      user_id: 1
    })

    if (response && response.success) {
      ElMessage.success(response.message || '任务已成功添加')
      await taskStore.fetchTasks(1, null, true)  // ⭐ forceRefresh 跳过缓存
      msg.confirmed = true

      messages.value.push({
        role: 'system',
        content: `✅ 任务「${response.task?.title || msg.taskPreview.title}」已添加到 ${formatSolutionTime(response.task?.start_time)}-${formatSolutionTime(response.task?.end_time)}`,
        timestamp: new Date().toISOString(),
        createdTask: response.task
      })
      await scrollToBottom()
    } else {
      ElMessage.error(response?.message || '添加任务失败')
    }
  } catch (error) {
    ElMessage.error('添加任务失败: ' + error.message)
  } finally {
    loading.value = false
    msg._adopting = false
  }
}

function formatSolutionTime(datetime) {
  if (!datetime) return '无'
  const date = new Date(datetime)
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hours}:${minutes}`
}


// ⭐ 下载 Word 格式的周报
function downloadWordReport(userId, timeRange) {
  const url = `/api/reports/weekly/${userId}/download?time_range=${timeRange}`
  window.open(url, '_blank')
  ElMessage.success('正在下载 Word 报告...')
}

onMounted(async () => {
  await scrollToBottom()
  await initNickname()

  isLoading.value = false
  window.addEventListener('keydown', handleKeyDown)

  // ... existing code ...
  // ⭐ 注册 WebSocket 周报消息处理（确保只注册一次）
  if (!websocketService.reportCallback) {
    websocketService.setReportCallback((data) => {
      console.log(' ChatWindow 收到周报:', data)

      // ⭐ 释放周报生成标记
      isGeneratingReport.value = false

      // 在聊天窗口中显示完整的 Markdown 报告
      messages.value.push({
        role: 'system',
        content: data.markdown || '报告生成失败',
        timestamp: new Date().toISOString(),
        isReport: true,
        reportData: data
      })

      // ⭐ 只有用户在底部时才自动滚动，否则显示新消息提示
      if (!isUserScrolling.value) {
        scrollToBottom()
      } else {
        hasNewMessage.value = true
      }
    })
    console.log('✅ 周报回调已注册')
  } else {
    console.log('⚠️ 周报回调已存在，跳过重复注册')
  }

})


onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  document.body.style.overflow = ''

  if (isVoiceInput.value) {
    stopVoiceInput()
  }
})
</script>

<style scoped>
.chat-window {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fullscreen-mode {
  max-width: 900px;
  width: 90%;
  max-height: 90vh;
  margin: 0 auto;
  position: relative;
  z-index: 2;
}

.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fullscreen-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.fullscreen-chat-container {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.fullscreen-mode :deep(.el-card__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  height: calc(90vh - 56px);
  overflow: hidden;
}

.message-timestamp {
  display: flex;
  justify-content: center;
  margin: 15px 0;
}

.timestamp-badge {
  background: rgba(0, 0, 0, 0.08);
  color: #909399;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.fullscreen-fade-enter-active,
.fullscreen-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.fullscreen-fade-enter-from,
.fullscreen-fade-leave-to {
  opacity: 0;
}

.fullscreen-fade-enter-from .fullscreen-chat-container {
  transform: scale(0.9);
  opacity: 0;
}

.fullscreen-fade-leave-to .fullscreen-chat-container {
  transform: scale(0.9);
  opacity: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.fullscreen-btn {
  opacity: 0.7;
  transition: opacity 0.2s;
}

.fullscreen-btn:hover {
  opacity: 1;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
}

.message {
  display: flex;
  gap: 12px;
  max-width: 80%;
}

.user-message {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.system-message {
  align-self: flex-start;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.user-avatar {
  background: #f5f5f5;
}

.system-avatar {
  background: #e6f7ff;
}

.message-content {
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.6;
}

.user-content {
  background: #95de64;
  color: #135200;
}

.system-content {
  background: white;
  border: 1px solid #e8e8e8;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.markdown-content {
  white-space: normal;
}

.markdown-content :deep(h1) {
  font-size: 1.5em;
  font-weight: 600;
  margin: 0.5em 0;
  color: #303133;
}

.markdown-content :deep(h2) {
  font-size: 1.3em;
  font-weight: 600;
  margin: 0.5em 0;
  color: #303133;
}

.markdown-content :deep(h3) {
  font-size: 1.1em;
  font-weight: 600;
  margin: 0.5em 0;
  color: #303133;
}

.markdown-content :deep(p) {
  margin: 0.5em 0;
  line-height: 1.6;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: #303133;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

.markdown-content :deep(li) {
  margin: 0.3em 0;
  line-height: 1.6;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
}

.markdown-content :deep(thead) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.markdown-content :deep(th) {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 13px;
  letter-spacing: 0.5px;
}

.markdown-content :deep(td) {
  padding: 10px 16px;
  border-bottom: 1px solid #e0e0e0;
}

.markdown-content :deep(tr:last-child td) {
  border-bottom: none;
}

.markdown-content :deep(tbody tr:hover) {
  background: #f5f5f5;
  transition: background 0.2s ease;
}

.markdown-content :deep(tbody tr:nth-child(even)) {
  background: #f8f9fa;
}

.markdown-content :deep(tbody tr:nth-child(even):hover) {
  background: #f0f0f0;
}


.markdown-content :deep(hr) {
  border: none;
  border-top: 1px solid #e8e8e8;
  margin: 1em 0;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #409eff;
  padding-left: 1em;
  margin: 0.5em 0;
  color: #606266;
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
}

.markdown-content :deep(code) {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #e63946;
}

.markdown-content :deep(pre) {
  background: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5em 0;
}

.markdown-content :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

.task-preview {
  margin-top: 12px;
}

.preview-details p {
  margin: 4px 0;
  font-size: 14px;
}

.conflict-item {
  margin: 8px 0;
}

.conflict-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.preview-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.conflict-actions {
  justify-content: space-between;
}

.suggestions {
  margin-top: 12px;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
}

.suggestions-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.suggestions ul {
  margin: 0;
  padding-left: 20px;
}

.suggestions li {
  margin: 4px 0;
  font-size: 14px;
}

.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #e8e8e8;
  background: white;
  position: relative;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.hint-text {
  font-size: 12px;
  color: #909399;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 18px;
  width: fit-content;
  align-self: flex-start;
}

.typing-dots span {
  animation: typing 1.4s infinite;
  font-size: 20px;
  color: #909399;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    opacity: 0.3;
  }
  30% {
    opacity: 1;
  }
}

.voice-input-overlay {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 12px 16px;
  z-index: 100;
  border-radius: 12px;
  min-width: 280px;
  margin-bottom: 8px;
}

.voice-panel-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.close-voice-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  background: rgba(255, 255, 255, 0.9);
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.close-voice-btn:hover {
  background: white;
  transform: scale(1.1);
}

.waveform-wrapper {
  width: 100%;
  max-width: 280px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 6px;
}

.waveform-wrapper canvas {
  width: 100%;
  height: 60px;
  display: block;
}

.voice-status {
  color: white;
  font-size: 13px;
  margin: 0;
  text-align: center;
  min-height: 18px;
  line-height: 1.4;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.el-button.recording {
  background: #f56c6c;
  border-color: #f56c6c;
  animation: mic-pulse 1.5s infinite;
}

@keyframes mic-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(245, 108, 108, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(245, 108, 108, 0);
  }
}

.voice-panel-enter-active,
.voice-panel-leave-active {
  transition: all 0.3s ease;
}

.voice-panel-enter-from,
.voice-panel-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.compact-task-card {
  margin-top: 8px;
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  border-radius: 8px;
  padding: 10px 12px;
}

.compact-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.success-icon {
  font-size: 14px;
}

.success-text {
  color: #67C23A;
  font-weight: 600;
  font-size: 13px;
  flex: 1;
}

.compact-card-body {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #606266;
}

.task-info {
  background: rgba(255, 255, 255, 0.6);
  padding: 2px 6px;
  border-radius: 4px;
}

.time-adjustment-notice {
  margin-top: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  animation: shimmer 2s ease-in-out infinite;
}

.adjustment-icon {
  font-size: 24px;
  animation: bounce 1s ease infinite;
}

.adjustment-content {
  flex: 1;
}

.adjustment-title {
  font-weight: 600;
  font-size: 14px;
  margin: 0 0 4px 0;
}

.adjustment-detail {
  font-size: 12px;
  margin: 0;
  opacity: 0.9;
}

.adjustment-badge {
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s ease infinite;
}

@keyframes shimmer {
  0%, 100% {
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }
  50% {
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
  }
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.adjustment-slide-enter-active {
  animation: slide-in 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.conflict-detail-alert {
  margin-top: 10px;
}

.conflict-detail-content {
  padding: 8px 0;
}

.conflict-section {
  margin-bottom: 8px;
}

.section-title {
  font-weight: 600;
  color: #e6a23c;
  margin-bottom: 8px;
  font-size: 14px;
}

.conflict-item-detailed {
  background: rgba(230, 162, 60, 0.1);
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 8px;
}

.conflict-task-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.task-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.task-time {
  color: #909399;
  font-size: 12px;
}

.conflict-reason {
  color: #e6a23c;
  font-size: 13px;
  margin: 0;
}

.conflict-resolution-panel {
  margin-top: 12px;
}

/* ⭐ 新增：时间轴对比卡片 */
.conflict-timeline-card {
  background: linear-gradient(135deg, #fff5f5 0%, #fff0f0 100%);
  border: 2px solid #ffcdd2;
  border-radius: 12px;
  padding: 16px;
  margin-top: 12px;
  box-shadow: 0 4px 12px rgba(255, 82, 82, 0.1);
}

.conflict-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.conflict-icon {
  width: 24px;
  height: 24px;
  background: #f56c6c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse-conflict 2s ease-in-out infinite;
}

@keyframes pulse-conflict {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(245, 108, 108, 0.2); }
}

.conflict-icon::before {
  content: '!';
  color: white;
  font-weight: bold;
  font-size: 14px;
}

.conflict-title {
  font-size: 16px;
  font-weight: 600;
  color: #f56c6c;
}

.conflict-count {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.timeline-visualization {
  background: white;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.timeline-header {
  margin-bottom: 8px;
}

.timeline-label {
  font-size: 13px;
  color: #909399;
  font-weight: 500;
}

.timeline-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conflict-bar-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.conflict-bar {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  transition: all 0.2s ease;
}

.conflict-bar.existing-task {
  border-left: 4px solid #909399;
  background: #f5f7fa;
}

.conflict-bar.new-task {
  border-left: 4px solid #f56c6c;
  background: linear-gradient(90deg, rgba(245, 108, 108, 0.08) 0%, transparent 100%);
}

.bar-label {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  flex: 1;
}

.bar-time {
  font-size: 12px;
  color: #909399;
  font-family: 'Courier New', monospace;
}

.overlap-badge {
  background: #f56c6c;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  animation: flash 1.5s ease-in-out infinite;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.conflict-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.6);
  padding: 10px 12px;
  border-radius: 8px;
}

.conflict-summary .summary-icon {
  color: #f56c6c;
  font-size: 18px;
}

.summary-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.summary-text strong {
  color: #f56c6c;
}

.recommended-solution-card {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 2px solid #409eff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
  transition: all 0.3s ease;
  position: relative;
}

.recommended-solution-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.25);
}

/* 洞察图标 */
.insight-trigger {
  position: absolute;
  top: 12px;
  right: 12px;
  opacity: 0;
  transform: translateY(8px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  z-index: 10;
}

.recommended-solution-card:hover .insight-trigger,
.alternative-solution-item:hover .insight-trigger {
  opacity: 1;
  transform: translateY(0);
}

.insight-icon {
  width: 28px;
  height: 28px;
  color: #409eff;
  filter: drop-shadow(0 0 6px rgba(64, 158, 255, 0.4));
  animation: breathe 2s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% {
    filter: drop-shadow(0 0 4px rgba(64, 158, 255, 0.3));
  }
  50% {
    filter: drop-shadow(0 0 8px rgba(64, 158, 255, 0.6));
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.recommend-badge {
  background: #409eff;
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.solution-score {
  color: #409eff;
  font-weight: 600;
  font-size: 14px;
}

.card-body {
  margin-bottom: 12px;
}

.solution-time {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.solution-advantages {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.advantage-item {
  color: #67c23a;
  font-size: 13px;
  margin: 0;
  padding-left: 4px;
}

/* ⭐ 新增：方案优势标题 */
.advantages-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

/* ⭐ 新增：为什么推荐区域 */
.solution-summary {
  margin-top: 12px;
  padding: 12px;
  background: linear-gradient(135deg, #fff9e6 0%, #fff3cc 100%);
  border-left: 4px solid #ffd666;
  border-radius: 8px;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.summary-header .summary-icon {
  color: #faad14;
  font-size: 16px;
}

.summary-title {
  font-size: 13px;
  font-weight: 600;
  color: #614700;
}

.summary-content {
  font-size: 13px;
  color: #614700;
  line-height: 1.6;
  margin: 0;
}

.card-actions {
  display: flex;
  justify-content: center;
}

.use-recommended-btn {
  width: 100%;
  font-weight: 600;
}

.alternative-solutions {
  margin-bottom: 16px;
}

.alternatives-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
  font-weight: 500;
}

.alternative-solution-item {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  transition: all 0.2s ease;
  position: relative;
}

.alternative-solution-item:hover {
  background: #fafafa;
  border-color: #dcdfe6;
}

.alt-badge {
  background: #909399;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.alt-time {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.alt-score {
  color: #909399;
  font-size: 12px;
}

.alt-advantages {
  margin-bottom: 8px;
}

.advantage-text {
  color: #606266;
  font-size: 13px;
}

/* ⭐ 新增：备选方案总结 */
.alt-summary {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(64, 158, 255, 0.06);
  border-radius: 6px;
  border-left: 3px solid #b3d8ff;
}

.alt-summary-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 2px;
}

.alt-summary-text {
  font-size: 12px;
  color: #409eff;
  line-height: 1.5;
}

/* ⭐ 新增：备选方案按钮优化 */
.alt-action-btn {
  margin-top: 8px;
  width: 100%;
}

.other-actions {
  margin-top: 12px;
}

.action-buttons-row {
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.action-buttons-row .el-button {
  flex: 1;
}

.simple-confirm {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

/* ========== 周报紧凑模式 ========== */

.report-markdown {
  font-size: 13px;
  line-height: 1.6;
  max-width: 100%;
  overflow-wrap: break-word;
}

/* ⭐ 临时调试：强制表格显示 */
.report-markdown :deep(table) {
  display: table !important;
  visibility: visible !important;
  opacity: 1 !important;
  width: 100% !important;
  border-collapse: collapse !important;
  margin: 12px 0 !important;
  font-size: 12px !important;
  background: #fff !important;
 }

.report-markdown :deep(thead) {
  display: table-header-group !important;
  visibility: visible !important;
}

.report-markdown :deep(tbody) {
  display: table-row-group !important;
  visibility: visible !important;
}

.report-markdown :deep(tr) {
  display: table-row !important;
  visibility: visible !important;
}

.report-markdown :deep(th),

.report-markdown :deep(td) {
  display: table-cell !important;
  visibility: visible !important;
  padding: 6px 8px !important;
  border: 1px solid #DCDFE6 !important;
  text-align: left !important;
}


/* ⭐ 新消息到达提示 */
.new-message-indicator {
  position: sticky;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 8px;
  text-align: center;
  cursor: pointer;
  border-top: 1px solid #EBEEF5;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #409EFF;
  font-size: 13px;
}

.new-message-indicator:hover {
  background: rgba(236, 245, 255, 0.95);
}

.new-message-indicator .arrow-icon {
  animation: bounce 1s infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

/* ⭐ 周报下载按钮样式 */
.report-download-actions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed #DCDFE6;
  display: flex;
  justify-content: center;
}

.report-download-actions .el-button {
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
  transition: all 0.3s ease;
}

.report-download-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

/* ⭐ 冲突时间轴对比卡片 */
.conflict-timeline-card {
  background: linear-gradient(135deg, #fff5f5 0%, #fff0f0 100%);
  border: 2px solid #ffcdd2;
  border-radius: 12px;
  padding: 16px;
  margin-top: 12px;
  box-shadow: 0 4px 12px rgba(255, 82, 82, 0.1);
}

.conflict-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.conflict-icon {
  width: 24px;
  height: 24px;
  background: #f56c6c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse-conflict 2s ease-in-out infinite;
}

.conflict-icon::before {
  content: '!';
  color: white;
  font-weight: bold;
  font-size: 14px;
}

@keyframes pulse-conflict {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.15); box-shadow: 0 0 0 8px rgba(245, 108, 108, 0.2); }
}

.conflict-title {
  font-size: 15px;
  font-weight: 600;
  color: #c0392b;
}

.conflict-count {
  margin-left: auto;
  font-size: 13px;
  color: #e74c3c;
  background: rgba(231, 76, 60, 0.1);
  padding: 2px 10px;
  border-radius: 12px;
  font-weight: 500;
}

/* 时间轴可视化 */
.timeline-visualization {
  margin-bottom: 12px;
}

.timeline-header {
  margin-bottom: 8px;
}

.timeline-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.timeline-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conflict-bar-group {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid #f0d0d0;
}

.conflict-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  position: relative;
}

.conflict-bar.existing-task {
  border-bottom: 1px dashed #e8d0d0;
  padding-bottom: 8px;
  margin-bottom: 4px;
}

.conflict-bar.existing-task::before {
  content: '';
  width: 8px;
  height: 8px;
  background: #e6a23c;
  border-radius: 2px;
  flex-shrink: 0;
}

.conflict-bar.new-task {
  position: relative;
}

.conflict-bar.new-task::before {
  content: '';
  width: 8px;
  height: 8px;
  background: #f56c6c;
  border-radius: 2px;
  flex-shrink: 0;
}

.bar-label {
  font-weight: 500;
  font-size: 13px;
  color: #303133;
  min-width: 60px;
}

.bar-time {
  font-size: 12px;
  color: #909399;
  flex: 1;
}

.overlap-badge {
  font-size: 11px;
  color: #f56c6c;
  font-weight: 600;
  background: rgba(245, 108, 108, 0.1);
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.conflict-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(245, 108, 108, 0.08);
  border-radius: 8px;
  border-left: 3px solid #f56c6c;
}

.conflict-summary .summary-icon {
  color: #f56c6c;
  font-size: 15px;
  flex-shrink: 0;
}

.conflict-summary .summary-text {
  font-size: 13px;
  color: #c0392b;
  line-height: 1.5;
}

/* ⭐ header-left */
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ⭐ 方案优势标题 */
.advantages-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

/* ⭐ 为什么推荐区域 */
.solution-summary {
  margin-top: 12px;
  padding: 12px;
  background: linear-gradient(135deg, #fff9e6 0%, #fff3cc 100%);
  border-left: 4px solid #ffd666;
  border-radius: 8px;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.summary-header .summary-icon {
  color: #faad14;
  font-size: 16px;
}

.summary-title {
  font-size: 13px;
  font-weight: 600;
  color: #614700;
}

.summary-content {
  font-size: 13px;
  color: #614700;
  line-height: 1.6;
  margin: 0;
}

/* ⭐ 备选方案总结 */
.alt-summary {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(64, 158, 255, 0.06);
  border-radius: 6px;
  border-left: 3px solid #b3d8ff;
}

.alt-summary-icon {
  font-size: 14px;
  flex-shrink: 0;
  margin-top: 2px;
}

.alt-summary-text {
  font-size: 12px;
  color: #409eff;
  line-height: 1.5;
}

/* ⭐ 备选方案按钮优化 */
.alt-action-btn {
  margin-top: 8px;
  width: 100%;
}

/* ⭐ 备选方案头部布局 */
.alt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.alt-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* ⭐ 备选方案主体 */
.alt-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* P0: 连续性警告 */
.continuity-warning {
  margin-top: 12px;
}

.continuity-warning .el-alert {
  border-radius: 10px;
  background: linear-gradient(135deg, #fdf6ec 0%, #fef0e6 100%);
  border: 1px solid #faecd8;
}

/* P1: 拆分建议 */
.split-suggestions {
  margin-top: 12px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%);
  border: 1px solid #b3d8ff;
  border-radius: 10px;
}

.split-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin: 0 0 10px 0;
}

.split-timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.split-segment-card {
  padding: 10px 12px;
  background: white;
  border: 1px solid #e8f0fe;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.split-segment-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.segment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.segment-number {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}

.segment-time {
  font-size: 13px;
  color: #606266;
  margin-left: 4px;
}

.segment-duration {
  color: #909399;
  font-size: 12px;
}

</style>





