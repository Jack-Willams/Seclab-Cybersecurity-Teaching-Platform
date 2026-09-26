<template>
  <div class="hidden lg:flex flex-col justify-center items-center w-1/2 p-8 bg-gradient-to-br 
              from-primary/10 via-secondary/10 to-accent/10 relative overflow-hidden">
    <!-- 背景装饰 -->
    <div class="absolute inset-0">
      <div class="absolute inset-0 bg-gradient-to-br from-base-100/10 to-transparent"></div>
    </div>

    <!-- 内容区域 -->
    <div class="relative z-10 text-center max-w-xl mx-auto">
      <!-- Logo -->
      <div class="mb-8 magictime spaceInDown">
        <div class="inline-block">
          <h1 class="text-5xl font-bold">
            Sec <span class="text-primary animate-pulse">Lab</span>
          </h1>
        </div>
      </div>

      <!-- 标语 -->
      <div class="space-y-6 mb-12 magictime spaceInUp">
        <h2 class="text-3xl font-bold bg-clip-text text-transparent 
                   bg-gradient-to-r from-primary via-secondary to-accent">
          网络安全实验平台
        </h2>
        <p class="text-xl text-base-content/70 leading-relaxed">
          从基础到进阶，系统化的安全实验课程
        </p>
      </div>

      <!-- 特性列表 -->
      <div class="grid gap-6 max-w-md mx-auto">
        <div v-for="(feature, index) in features" 
             :key="index"
             class="flex items-center gap-4 p-4 rounded-lg bg-base-100/50 backdrop-blur-sm
                    border border-base-200 group magictime vanishIn hover:magic-hover"
             :style="{ animationDelay: `${index * 0.2}s` }">
          <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center
                      group-hover:scale-110 transition-transform duration-300">
            <i :class="['fas', feature.icon, 'text-2xl text-primary']"></i>
          </div>
          <div class="flex-1">
            <h3 class="font-semibold mb-1">{{ feature.title }}</h3>
            <p class="text-sm text-base-content/70">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部装饰 -->
    <div class="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-base-100/20 to-transparent"></div>
  </div>
</template>

<script setup lang="ts">
const features = [
  {
    icon: 'fa-graduation-cap',
    title: '系统化学习',
    description: '精心设计的课程体系，循序渐进的学习路径'
  },
  {
    icon: 'fa-laptop-code',
    title: '实战演练',
    description: '真实环境模拟，动手实践提升安全技能'
  },
  {
    icon: 'fa-shield-alt',
    title: '安全保障',
    description: '标准化的实验环境，确保学习过程安全可控'
  }
]
</script>

<style scoped>


/* 渐入动画 */
.grid > div {
  animation: slideUp 0.5s ease-out forwards;
  opacity: 0;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 悬浮效果 */
.grid > div:hover {
  box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.1);
}

/* Magic.css 自定义悬浮效果 */
.magic-hover {
  animation: puffIn 0.3s ease-out;
}

/* 自定义动画 */
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.animate-float {
  animation: float 3s ease-in-out infinite;
}

/* Logo 特效 */
.text-primary {
  position: relative;
  display: inline-block;
}

.text-primary::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  width: 100%;
  height: 2px;
  background: oklch(var(--p));
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.3s ease;
}

.text-primary:hover::after {
  transform: scaleX(1);
  transform-origin: left;
}
</style>
