<template>
  <div class="chat-skeleton">
    <div class="skeleton-messages">
      <div v-for="i in 3" :key="i" class="skeleton-message" :class="{ 'is-user': i % 2 === 0 }">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-bubble">
          <SkeletonLoader width="180px" height="16px" />
          <SkeletonLoader width="120px" height="16px" style="margin-top: 8px" />
        </div>
      </div>
    </div>
    <div class="skeleton-input">
      <SkeletonLoader width="100%" height="40px" />
    </div>
  </div>
</template>

<script setup>
import SkeletonLoader from './SkeletonLoader.vue'
</script>

<style scoped>
.chat-skeleton {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.skeleton-messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-message {
  display: flex;
  gap: 12px;
}

.skeleton-message.is-user {
  flex-direction: row-reverse;
}

.skeleton-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f0f0f0;
  flex-shrink: 0;
}

.skeleton-bubble {
  background: #f0f0f0;
  border-radius: 12px;
  padding: 12px 16px;
  max-width: 70%;
}

.skeleton-input {
  margin-top: 16px;
}
</style>
