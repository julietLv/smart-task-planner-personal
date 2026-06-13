<template>
  <transition name="sprite-float">
    <div v-if="visible" class="assistant-sprite" :style="{ bottom: spritePosition + 'px' }">
      <!-- 精灵形象 -->
      <div class="sprite-avatar" @click="toggleMessage">
        <div class="sprite-body">
          <span class="sprite-emoji">{{ spriteEmoji }}</span>
        </div>
        <div class="sprite-badge" v-if="hasNewMessage">
          <span>!</span>
        </div>
      </div>

      <!-- 对话气泡 -->
      <transition name="bubble-pop">
        <div v-if="showMessage" class="sprite-bubble">
          <div class="bubble-content">
            <p>{{ message }}</p>
          </div>
          <div class="bubble-actions">
            <el-button size="small" text @click="closeSprite">
              知道了~
            </el-button>
            <el-button v-if="stats.pending > 0" size="small" type="primary" @click="goToTasks">
              去完成任务
            </el-button>
          </div>
          <div class="bubble-tail"></div>
        </div>
      </transition>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()
const visible = ref(false)
const showMessage = ref(false)
const hasNewMessage = ref(false)
const message = ref('')
const stats = ref({ total: 0, done: 0, pending: 0 })
const spritePosition = ref(100)
const spriteEmoji = ref('🧚')

let greetingTimer = null

async function fetchGreeting() {
  try {
    const response = await fetch('http://localhost:8080/api/chat/assistant/daily-greeting', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ user_id: 1 })
    })
    const data = await response.json()

    if (data.success) {
      message.value = data.message
      stats.value = data.stats

      // ⭐ 使用后端返回的表情
      if (data.sprite_emoji) {
        spriteEmoji.value = data.sprite_emoji
      }

      // 延迟显示，避免突兀
      setTimeout(() => {
        visible.value = true
        hasNewMessage.value = true

        // 3 秒后自动弹出对话
        setTimeout(() => {
          showMessage.value = true
          hasNewMessage.value = false
        }, 1500)
      }, 2000)
    }
  } catch (error) {
    console.error('获取问候失败:', error)
  }
}

function toggleMessage() {
  showMessage.value = !showMessage.value
}

function closeSprite() {
  showMessage.value = false
  setTimeout(() => {
    visible.value = false
  }, 500)
}

function goToTasks() {
  // 可以跳转到日历视图或其他操作
  ElMessage.info('正在为您加载任务列表...')
  closeSprite()
}

// 精灵浮动动画
function floatAnimation() {
  setInterval(() => {
    spritePosition.value = 100 + Math.sin(Date.now() / 1000) * 10
  }, 50)
}

onMounted(() => {
  fetchGreeting()
  floatAnimation()
})
</script>

<style scoped>
.assistant-sprite {
  position: fixed;
  right: 30px;
  z-index: 1000;
  transition: bottom 0.5s ease;
}

.sprite-avatar {
  position: relative;
  cursor: pointer;
  transition: transform 0.3s;
}

.sprite-avatar:hover {
  transform: scale(1.1);
}

.sprite-body {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transition: all 0.3s;
}

.sprite-body:hover {
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}

.sprite-emoji {
  font-size: 32px;
}

.sprite-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 20px;
  height: 20px;
  background: #f56c6c;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: bold;
  animation: pulse 2s infinite;
}

.sprite-bubble {
  position: absolute;
  bottom: 70px;
  right: 0;
  width: 280px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 2px solid #667eea;
}

.bubble-content p {
  margin: 0;
  font-size: 14px;
  color: #303133;
  line-height: 1.6;
}

.bubble-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  justify-content: flex-end;
}

.bubble-tail {
  position: absolute;
  bottom: -10px;
  right: 30px;
  width: 0;
  height: 0;
  border-left: 10px solid transparent;
  border-right: 10px solid transparent;
  border-top: 10px solid #667eea;
}

/* 动画 */
.sprite-float-enter-active {
  animation: float-in 0.5s ease;
}

.sprite-float-leave-active {
  animation: float-out 0.5s ease;
}

@keyframes float-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes float-out {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(20px);
  }
}

.bubble-pop-enter-active {
  animation: pop-in 0.3s ease;
}

@keyframes pop-in {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}
</style>
