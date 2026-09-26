<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ref, computed, onMounted } from 'vue'
import IntroductionCard from './component/IntroductionCard.vue'
import { useTheme } from '../../composables/useTheme'

const router = useRouter()

// 暗色下由 layout 的 AmbientBackdrop 提供底色（星点/网格/柔光）。
// 本页原来给根节点刷了一层不透明的 base-100→base-200 渐变，正好把那层星空整个盖掉，
// 于是首页看起来还是旧版那个纯渐变底 —— 所以 night 下这里必须让位、保持透明。
// light 主题不渲染 AmbientBackdrop，渐变留着，否则首页会是一片死白。
const { currentTheme } = useTheme()
const isNight = computed(() => currentTheme.value === 'night')
const isLoaded = ref(false)
const showParticles = ref(false)

const navigateToCourses = () => {
  router.push('/user/courses')
}

const navigateToModules = () => {
  router.push('/user/modules')
}

const navigateToCommunity = () => {
  router.push('/user/community')
}

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
  setTimeout(() => {
    showParticles.value = true
  }, 500)
})

// 定义卡片数据
const cards = [
  {
    title: '课程学习',
    description: '探索我们精心设计的课程体系，从基础到进阶，循序渐进地掌握网络安全知识。',
    svgPath: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    buttonText: '开始学习',
    buttonClass: 'btn-primary',
    onClick: navigateToCourses,
    icon: 'fa-book-open',
    highlight: true
  },
  {
    title: '实践演练',
    description: '通过真实的案例和模拟环境，将理论知识转化为实践技能。',
    svgPath: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    buttonText: '开始实践',
    buttonClass: 'btn-primary',
    onClick: navigateToModules,
    icon: 'fa-laptop-code',
    highlight: true
  },
  {
    title: '学习社区',
    description: '加入我们的学习社区，与其他学习者交流经验，分享心得。',
    svgPath: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
    buttonText: '进入社区',
    buttonClass: 'btn-primary',
    onClick: navigateToCommunity,
    icon: 'fa-users'
    // highlight: true
  }
]

// 生成随机粒子
const particles = Array.from({ length: 50 }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  y: Math.random() * 100,
  size: Math.random() * 4 + 1,
  speed: Math.random() * 2 + 1
}))
</script>

<template>
  <div
    class="min-h-screen flex flex-col items-center justify-center relative overflow-hidden"
    :class="isNight ? 'bg-transparent' : 'bg-gradient-to-br from-base-100 to-base-200'"
  >
    <!-- 粒子背景 -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <!-- 渐变光晕：暗色下 AmbientBackdrop 已经有三团柔光了，再叠这三个 blur-3xl
           既把星点洗白、又多一遍离屏模糊，纯浪费 —— 只在 light 主题下留着 -->
      <div v-if="!isNight" class="absolute inset-0 opacity-30">
        <div
          v-for="i in 3"
          :key="`gradient-${i}`"
          class="absolute rounded-full blur-3xl"
          :class="`bg-${i === 1 ? 'primary' : i === 2 ? 'secondary' : 'accent'}/20`"
          :style="{
            width: `${400 + i * 100}px`,
            height: `${400 + i * 100}px`,
            left: `${30 + i * 20}%`,
            top: `${20 + i * 15}%`,
            transform: `rotate(${i * 45}deg)`,
            animation: `float ${10 + i * 2}s ease-in-out infinite`,
            animationDelay: `${i * -2}s`
          }"
        ></div>
      </div>

      <!-- 动态粒子 -->
      <div
        v-if="showParticles"
        v-for="particle in particles"
        :key="particle.id"
        class="absolute w-1 h-1 bg-primary/30 rounded-full"
        :style="{
          left: `${particle.x}%`,
          top: `${particle.y}%`,
          width: `${particle.size}px`,
          height: `${particle.size}px`,
          animation: `particleFloat ${particle.speed * 5}s infinite linear`
        }"
      ></div>
    </div>

    <!-- 主要内容 -->
    <div class="relative z-10 w-full max-w-7xl mx-auto px-4">
      <!-- 欢迎区域 -->
      <div class="text-center mb-16" :class="{ 'animate-slide-down': isLoaded }">
        <div class="inline-block mb-6">
          <div class="text-sm font-semibold text-primary/80 mb-2 tracking-wider uppercase"><i class="fas fa-shield-alt mr-2"></i>Sec Lab</div>
          <h1 class="text-6xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-primary via-secondary to-accent leading-tight">开启你的安全实验之旅</h1>
        </div>
        <p class="text-xl text-base-content/80 max-w-3xl mx-auto leading-relaxed">在这里，你将开启一段精彩的网络安全学习之旅。我们提供专业的课程内容和实践机会， 帮助你掌握必要的网络安全技能。</p>
      </div>

      <!-- 功能卡片区域 -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 relative">
        <div
          v-for="(card, index) in cards"
          :key="index"
          class="transform"
          :class="{
            'animate-slide-up': isLoaded,
            'hover:z-10': card.highlight
          }"
          :style="{
            animationDelay: `${index * 0.2}s`,
            transform: `perspective(1000px) rotateY(${(index - 1) * 5}deg)`
          }"
        >
          <IntroductionCard v-bind="card" />
        </div>
      </div>
    </div>

    <!-- 底部装饰 -->
    <div class="absolute bottom-0 left-0 right-0">
      <div class="h-32 bg-gradient-to-t from-base-300/20 to-transparent"></div>
      <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/20 to-transparent"></div>
    </div>
  </div>
</template>

<style scoped>
.animate-float {
  animation: float 10s ease-in-out infinite;
}

.animate-slide-down {
  animation: slideDown 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(10deg);
  }
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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

@keyframes particleFloat {
  0% {
    transform: translateY(0) translateX(0);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    transform: translateY(-100vh) translateX(50px);
    opacity: 0;
  }
}

/* 渐变文字效果 */
.text-gradient {
  background: linear-gradient(to right, oklch(var(--p)), oklch(var(--s)));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 卡片容器样式 */
.grid {
  perspective: 1000px;
}

/* 添加悬浮效果 */
.grid > div {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.grid > div:hover {
  transform: perspective(1000px) translateZ(30px) !important;
}

/* 渐变文字增强 */
.text-transparent {
  opacity: 0.95;
  text-shadow: 0 0 30px oklch(var(--p) / 0.3);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .text-6xl {
    font-size: 3rem;
  }

  .grid > div {
    transform: none !important;
  }
}
</style>
