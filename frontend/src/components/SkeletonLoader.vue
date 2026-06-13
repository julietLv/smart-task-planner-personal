<template>
  <div class="skeleton-loader" :style="{ width, height }">
    <div class="skeleton-animation"></div>
  </div>
</template>

<script setup>
defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '20px' }
})
</script>

<style scoped>
.skeleton-loader {
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.skeleton-animation {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
