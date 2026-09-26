<template>
  <div class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all duration-500 group backdrop-blur-sm
              border border-base-200 hover:border-primary/20">
    <div class="card-body relative overflow-hidden">
      <!-- 背景装饰 -->
      <div class="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 
                  group-hover:opacity-100 transition-opacity duration-500"></div>
      
      <!-- 卡片内容 -->
      <div class="relative z-10">
        <!-- 标题区域 -->
        <div class="flex items-center gap-3 mb-4">
          <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center
                      group-hover:scale-110 transition-transform duration-500">
            <i :class="['fas', icon, 'text-xl text-primary']"></i>
          </div>
          <h2 class="card-title text-2xl">{{ title }}</h2>
        </div>

        <!-- 描述文本 -->
        <p class="text-base-content/70 leading-relaxed mb-6">{{ description }}</p>

        <!-- 操作按钮 -->
        <div class="card-actions justify-end">
          <button 
            class="btn gap-2 relative overflow-hidden" 
            :class="[buttonClass, {
              'hover:-translate-y-1 hover:shadow-lg': buttonClass === 'btn-primary'
            }]"
            @click="handleClick"
          >
            <span class="relative z-10">{{ buttonText }}</span>
            <i class="fas fa-arrow-right relative z-10"></i>
            
            <!-- 按钮动画效果 -->
            <div v-if="buttonClass === 'btn-primary'"
                 class="absolute inset-0 bg-gradient-to-r from-primary to-primary-focus 
                        opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            </div>
          </button>
        </div>
      </div>

      <!-- 角标装饰 -->
      <div v-if="highlight" 
           class="absolute -top-1 -right-1 w-16 h-16 overflow-hidden">
        <div class="absolute top-0 right-0 w-2 h-2 bg-primary transform rotate-45"></div>
        <div class="absolute top-0 right-0 w-2 h-2 bg-primary/50 blur-sm transform rotate-45"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Props } from './IntroductionCard';

const props = withDefaults(defineProps<Props>(), {
  buttonClass: 'btn-secondary',
  onClick: () => {},
  highlight: false
});

const handleClick = () => {
  props.onClick();
};
</script>

<style scoped>
.card {
  transform-style: preserve-3d;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.card:hover {
  transform: translateZ(20px);
}

/* 按钮悬浮效果 */
.btn {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.btn-primary {
  position: relative;
  overflow: hidden;
}

.btn-primary::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 300%;
  height: 300%;
  background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 50%);
  transform: translate(-50%, -50%) scale(0);
  opacity: 0;
  transition: transform 0.5s ease-out, opacity 0.3s ease-out;
}

.btn-primary:hover::after {
  transform: translate(-50%, -50%) scale(1);
  opacity: 1;
}

/* 图标动画 */
.fas {
  transition: transform 0.3s ease;
}

.card:hover .fas {
  transform: scale(1.1);
}

/* 禁用状态样式 */
.btn-secondary {
  opacity: 0.8;
  cursor: not-allowed;
}

.btn-secondary:hover {
  transform: none;
  box-shadow: none;
}
</style>