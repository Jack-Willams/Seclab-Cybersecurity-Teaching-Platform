<script setup lang="ts">
import Toast from './components/Toast.vue';
import FloatingChatButton from './components/FloatingChatButton.vue';
import { useRoute } from 'vue-router';
import { computed } from 'vue';

const route = useRoute();

// 在特定页面不显示悬浮聊天按钮；教师端整体不展示学生向的 AI 助手入口
const shouldShowChatButton = computed(() => {
  const path = route.path;
  return !path.startsWith('/teacher')
    && !path.includes('/user/chat')
    && !path.includes('/user/floating-chat-demo');
});
</script>

<template>
  <div class="fixed w-full h-full bg-base-100">
    <RouterView>
    </RouterView>
    <Toast />
    <!-- 全局悬浮聊天按钮 -->
    <FloatingChatButton v-if="shouldShowChatButton" />
  </div>
</template>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
</style>
