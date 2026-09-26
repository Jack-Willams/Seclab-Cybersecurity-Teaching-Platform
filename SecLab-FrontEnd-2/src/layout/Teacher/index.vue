<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearStoredAuthSession, getStoredCurrentUser } from '../../auth'
import { useTheme } from '../../composables/useTheme'
import AmbientBackdrop from '../../components/AmbientBackdrop.vue'

const route = useRoute()
const router = useRouter()
const mobileOpen = ref(false)
const currentUser = computed(() => getStoredCurrentUser())
// 教师端原来没有主题入口，教师必须先绕到学生端 Header 才能切换，这里补上
const { currentTheme, toggleTheme } = useTheme()

const navigation = [
  { label: '教学概览', to: '/teacher/overview', icon: 'home' },
  { label: '教学班', to: '/teacher/classes', icon: 'class' },
  { label: '教学分析', to: '/teacher/analysis', icon: 'analysis' },
  { label: '课程库', to: '/teacher/courses', icon: 'course' },
  { label: '生成题记录', to: '/teacher/generated-questions', icon: 'question' },
]

const active = (to: string) => route.path === to || route.path.startsWith(`${to}/`)
const logout = () => {
  clearStoredAuthSession()
  router.replace('/')
}

// 和学生端同一个问题：快速滚动时卡片从静止的光标下逐张扫过，每张瞬间命中一次 :hover，
// 触发 style.css 的 `.card:hover .cover img { scale(1.06) }`（以及课程库自己的 hover 缩放），
// 画面看着像抖了一下又弹回去。滚动期间关掉子树指针事件，:hover 就匹配不上。
const isScrolling = ref(false)
let scrollIdleTimer: ReturnType<typeof setTimeout> | undefined

const handleScroll = () => {
  isScrolling.value = true
  if (scrollIdleTimer) clearTimeout(scrollIdleTimer)
  scrollIdleTimer = setTimeout(() => {
    isScrolling.value = false
  }, 120)
}

onBeforeUnmount(() => {
  if (scrollIdleTimer) clearTimeout(scrollIdleTimer)
})
</script>

<template>
  <!-- 底色跟学生端对齐：页面地板用 base-300，面板留在 base-100，靠亮度差表达层级。
       relative 是 AmbientBackdrop 的定位参照（它是 absolute inset-0 z-0），不能去掉。 -->
  <div class="teacher-shell relative overflow-hidden bg-base-300 text-base-content">
    <!-- 暗色主题下的星点/柔光背景，和学生端同一个组件、同一套参数 -->
    <AmbientBackdrop />

    <button
      class="btn btn-ghost btn-sm btn-square fixed left-3 top-2.5 z-[35] border border-base-300 bg-base-100 lg:hidden"
      type="button"
      aria-label="打开导航"
      @click="mobileOpen = true"
    >
      <i class="fas fa-bars"></i>
    </button>
    <div
      v-if="mobileOpen"
      class="fixed inset-0 z-[39] bg-neutral/40 lg:hidden"
      @click="mobileOpen = false"
    ></div>

    <aside
      class="fixed inset-y-0 left-0 z-40 flex w-[238px] flex-col border-r border-base-300 bg-base-100 transition-transform duration-200 lg:translate-x-0"
      :class="mobileOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="flex h-[82px] items-center gap-3 border-b border-base-300 px-6">
        <div
          class="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-primary to-secondary text-lg font-extrabold text-primary-content shadow-sm"
        >
          S
        </div>
        <div class="min-w-0">
          <strong class="block text-[17px] tracking-wide">SecLab</strong>
          <span class="mt-0.5 block text-[11px] text-base-content/60">网络安全教学平台</span>
        </div>
      </div>

      <div class="px-7 pb-2.5 pt-7 text-[11px] font-bold tracking-[.12em] text-base-content/50">
        教师工作台
      </div>
      <nav class="px-3.5">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          class="nav-item my-1 flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-semibold transition-colors"
          :class="active(item.to)
            ? 'bg-primary/10 text-primary'
            : 'text-base-content/70 hover:bg-base-200 hover:text-primary'"
          @click="mobileOpen = false"
        >
          <svg v-if="item.icon === 'home'" viewBox="0 0 24 24"><path d="M3 11.5 12 4l9 7.5v8a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg>
          <svg v-else-if="item.icon === 'class'" viewBox="0 0 24 24"><path d="M4 5h16v12H4zM8 21h8M12 17v4M7 9h4M7 12h7"/></svg>
          <svg v-else-if="item.icon === 'course'" viewBox="0 0 24 24"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5a2.5 2.5 0 1 1 0-5H20M7 7h9"/></svg>
          <svg v-else-if="item.icon === 'analysis'" viewBox="0 0 24 24"><path d="M4 19V9M10 19V5M16 19v-7M3 19h18M16 7l3-3M19 4v4M19 4h-4"/></svg>
          <svg v-else viewBox="0 0 24 24"><path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/></svg>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="mt-auto border-t border-base-300 px-4 py-3">
        <button
          class="btn btn-ghost btn-sm mb-1 w-full justify-start gap-3 font-normal text-base-content/70"
          type="button"
          :aria-label="currentTheme === 'night' ? '切换到亮色模式' : '切换到暗色模式'"
          @click="toggleTheme"
        >
          <i :class="['fas', currentTheme === 'night' ? 'fa-sun' : 'fa-moon']"></i>
          <span>{{ currentTheme === 'night' ? '亮色模式' : '暗色模式' }}</span>
        </button>

        <div class="flex items-center gap-2.5 pt-2">
          <div class="grid h-9 w-9 flex-none place-items-center rounded-full bg-primary/15 font-bold text-primary">
            {{ (currentUser?.realName || currentUser?.username || '教').slice(0, 1) }}
          </div>
          <div class="min-w-0 flex-1">
            <strong class="block truncate text-[13px]">
              {{ currentUser?.realName || currentUser?.username || '教师' }}
            </strong>
            <span class="block truncate text-[11px] text-base-content/60">教师账号</span>
          </div>
          <button
            class="btn btn-ghost btn-xs text-base-content/60 hover:text-error"
            type="button"
            title="退出登录"
            @click="logout"
          >
            退出
          </button>
        </div>
      </div>
    </aside>

    <main
      class="teacher-main relative z-10 min-h-0 overflow-y-auto overflow-x-hidden pt-12 lg:ml-[238px] lg:pt-0"
      :class="{ 'is-scrolling': isScrolling }"
      @scroll.passive="handleScroll"
    >
      <RouterView v-slot="{ Component }">
        <transition name="page" mode="out-in" appear>
          <!-- key 用 path，和学生端一致：只换参数的跳转命中同一个路由记录，
               不加 key 组件会被复用、onMounted 不再执行 -->
          <component :is="Component" :key="route.path" />
        </transition>
      </RouterView>
    </main>
  </div>
</template>

<style scoped>
/* 原来这个 style 块没写 scoped，还往 :root 挂了 5 个全局变量，会漏到学生端和管理端 */
.teacher-shell {
  height: 100vh;
  height: 100dvh;
}
.teacher-main {
  height: 100vh;
  height: 100dvh;
}
.nav-item svg {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* 切页动画：和 layout/User/index.vue 完全同一套参数，两端观感一致。
   只过渡 opacity/transform 两个合成器属性 —— 写成 `transition: all` 的话，
   下面 .page-leave-active 的 position:absolute 会把布局属性也拖进过渡，
   学生端那边实测过一次切页要 2.2 秒。 */
.page-leave-active {
  transition: opacity 0.26s cubic-bezier(0.4, 0, 1, 1), transform 0.26s cubic-bezier(0.4, 0, 1, 1);
  /* 绝对定位让离场页脱离文档流，新页才能立刻占位、不闪跳。
     定位参照是 .teacher-main 上的 relative。 */
  position: absolute;
  inset: 0;
}

.page-enter-active {
  transition: opacity 0.34s cubic-bezier(0, 0, 0.2, 1), transform 0.34s cubic-bezier(0, 0, 0.2, 1);
}

.page-enter-from {
  opacity: 0;
  transform: scale(0.97) translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }
}
</style>
