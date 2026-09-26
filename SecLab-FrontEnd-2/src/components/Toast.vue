<template>
  <teleport to="body">
    <div v-if="visible" class="toast">
      <div class="alert" :class="{'alert-info': true, 'alert-error': isError}">
        <div class="flex items-center">
          <i class="fas" :class="isError ? 'fa-exclamation-circle' : 'fa-info-circle'"></i>
          <span class="ml-2 font-medium">{{ message }}</span>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useToast } from '../common';

const { toastMessage, toastVisible } = useToast();

const message = computed(() => toastMessage.value);
const visible = computed(() => toastVisible.value);
const isError = computed(() => message.value.includes('失败') || message.value.includes('错误'));
</script>

<style scoped>
.toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
  min-width: 320px;
  max-width: 90%;
  animation: toast-appear 0.3s ease-out;
}

.alert {
  background-color: rgba(255, 255, 255, 0.95);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border-radius: 8px;
  padding: 1rem 1.5rem;
  font-size: 1.1rem;
  border-left: 4px solid;
  color: #111827 !important;
}

.alert-info {
  border-color: oklch(var(--p));
  color: #111827 !important;
}

.alert-error {
  border-color: oklch(var(--er));
  background-color: rgba(254, 226, 226, 0.95);
  color: #111827 !important;
}

.alert :deep(*) {
  color: #111827 !important;
}

@keyframes toast-appear {
  0% {
    opacity: 0;
    transform: translate(-50%, -40%);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%);
  }
}
</style> 
