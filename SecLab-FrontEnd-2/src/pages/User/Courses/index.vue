<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import CourseOverView from './components/CourseOverView.vue'
import PageHero from '../../../components/PageHero.vue'
import type { CourseOverViewType } from './components/CourseOverView'
import { image, type CourseSummaryDto } from '../../../api'
import {
  catalogError,
  catalogSource,
  courseCatalog,
  ensureCourseCatalog,
  isCatalogRefreshing,
  refreshCourseCatalog,
} from '../../../composables/useCourseCatalog'

function mapStatus(status: string | null | undefined): 'in-progress' | 'completed' | 'available' | 'hidden' {
  if (!status) return 'available'

  switch (status.toLowerCase()) {
    case 'draft':
    case 'locked':
    case 'archived':
      return 'hidden'
    case 'in_progress':
    case 'in-progress':
      return 'in-progress'
    case 'completed':
      return 'completed'
    default:
      return 'available'
  }
}

function mapDifficulty(difficulty: number | null | undefined): 1 | 2 | 3 | 4 | 5 {
  if (!difficulty) return 3
  return Math.min(Math.max(difficulty, 1), 5) as 1 | 2 | 3 | 4 | 5
}

function mapApiDataToViewData(apiData: CourseSummaryDto[]): CourseOverViewType[] {
  return apiData
    .map((course) => {
      const status = mapStatus(course.status)
      if (status === 'hidden') {
        return null
      }

      return {
        id: course.id,
        name: course.name,
        image: image(course.imageUrl),
        description: course.description || '',
        status,
        category: course.type || 'web',
        difficulty: mapDifficulty(course.difficulty),
        estimatedHours: 8,
        tags: course.tags || [],
      }
    })
    .filter((course): course is CourseOverViewType => Boolean(course))
}

const isLoaded = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')

const categories = [
  { id: 'web', name: 'Web安全', icon: 'fa-globe' },
  { id: 'system', name: '系统安全', icon: 'fa-desktop' },
  { id: 'network', name: '网络安全', icon: 'fa-network-wired' },
  { id: 'crypto', name: '密码学', icon: 'fa-key' },
  { id: 'advanced', name: '高级威胁', icon: 'fa-shield-alt' },
  { id: 'binary', name: '二进制安全', icon: 'fa-microchip' },
]

// 乐观渲染：直接由课程目录派生，本地种子先上屏，远端回来后自动合并刷新
const courses = computed<CourseOverViewType[]>(() => mapApiDataToViewData(courseCatalog.value))

const stats = computed(() => ({
  total: courses.value.length,
  inProgress: courses.value.filter((c) => c.status === 'in-progress').length,
  completed: courses.value.filter((c) => c.status === 'completed').length,
  available: courses.value.filter((c) => c.status === 'available').length,
}))

const filteredCourses = computed(() => {
  return courses.value.filter((course) => {
    if (searchQuery.value && !course.name.toLowerCase().includes(searchQuery.value.toLowerCase())) {
      return false
    }
    if (selectedCategory.value && course.category !== selectedCategory.value) {
      return false
    }
    return true
  })
})

onMounted(() => {
  // 不 await：页面已经用本地目录渲染好了，远端只是后台校准
  ensureCourseCatalog()
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
})
</script>

<template>
  <div class="container-fluid px-4 py-4 overflow-x-hidden min-h-screen">
    <PageHero
      kicker="SEC LAB · 课程中心"
      title="探索课程"
      subtitle="发现精心设计的安全课程，开启你的学习之旅"
      :class="{ 'animate-fade-in': isLoaded }"
    >
      <template #status>
        <span v-if="isCatalogRefreshing" class="ml-2 text-xs text-base-content/50">
          <span class="loading loading-spinner loading-xs align-middle"></span>
          正在同步最新课程…
        </span>
      </template>
    </PageHero>

    <div class="stats shadow w-full mb-6 bg-base-100 backdrop-blur-sm" :class="{ 'animate-slide-up': isLoaded }">
      <div class="stat py-2">
        <div class="stat-figure text-primary">
          <i class="fas fa-book-open text-xl"></i>
        </div>
        <div class="stat-title text-xs">总课程</div>
        <div class="stat-value text-primary text-xl">{{ stats.total }}</div>
      </div>

      <div class="stat py-2">
        <div class="stat-figure text-info">
          <i class="fas fa-spinner text-xl"></i>
        </div>
        <div class="stat-title text-xs">进行中</div>
        <div class="stat-value text-info text-xl">{{ stats.inProgress }}</div>
      </div>

      <div class="stat py-2">
        <div class="stat-figure text-success">
          <i class="fas fa-check-circle text-xl"></i>
        </div>
        <div class="stat-title text-xs">已完成</div>
        <div class="stat-value text-success text-xl">{{ stats.completed }}</div>
      </div>

      <div class="stat py-2">
        <div class="stat-figure text-warning">
          <i class="fas fa-lock-open text-xl"></i>
        </div>
        <div class="stat-title text-xs">可开始</div>
        <div class="stat-value text-warning text-xl">{{ stats.available }}</div>
      </div>
    </div>

    <!-- 课程服务没起来时如实说明，但不挡着页面：列表用的是前端内置目录 -->
    <div v-if="catalogSource === 'local' && !isCatalogRefreshing" class="alert alert-warning py-2 mb-4 text-sm">
      <i class="fas fa-plug"></i>
      <span>课程服务未连接，当前显示内置课程目录{{ catalogError ? `（${catalogError}）` : '' }}。</span>
      <button class="btn btn-xs btn-ghost" @click="refreshCourseCatalog()">重试</button>
    </div>

    <div class="flex flex-col md:flex-row gap-3 mb-6" :class="{ 'animate-slide-up': isLoaded }" style="animation-delay: 0.2s">
      <div class="flex-1 relative">
        <input type="text" placeholder="搜索课程..." class="input input-sm input-bordered w-full pl-8 pr-3 bg-base-100/70 focus:bg-base-100 transition-all duration-300 shadow-sm hover:shadow focus:shadow-md" v-model="searchQuery" />
        <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-xs text-base-content/50"></i>
      </div>

      <div class="flex gap-1">
        <button v-for="category in categories" :key="category.id" class="btn btn-ghost btn-sm gap-1 text-xs" :class="{ 'btn-active': selectedCategory === category.id }" @click="selectedCategory = selectedCategory === category.id ? '' : category.id">
          <i :class="['fas', category.icon]"></i>
          <span>{{ category.name }}</span>
        </button>
      </div>
    </div>

    <div v-if="!courses.length" class="card bg-base-100 shadow-xl">
      <div class="card-body text-center py-10 text-base-content/60">
        暂无课程
      </div>
    </div>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4" :class="{ 'animate-fade-in': isLoaded }" style="animation-delay: 0.3s">
      <template v-if="filteredCourses.length">
        <div v-for="(course, index) in filteredCourses" :key="course.id" :style="{ animationDelay: `${index * 0.05}s` }" class="animate-slide-up">
          <CourseOverView :course="course" />
        </div>
      </template>
      <div v-else class="col-span-full text-center py-6">
        <div class="text-4xl mb-2 text-base-content/30">
          <i class="fas fa-search"></i>
        </div>
        <h3 class="text-lg font-semibold mb-1">未找到匹配的课程</h3>
        <p class="text-sm text-base-content/70">试试调整搜索条件</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container-fluid {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

html,
body {
  overflow-x: hidden;
  margin: 0;
  padding: 0;
  width: 100%;
}

.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stat {
  transition: all 0.3s ease;
}

.stat:hover {
  transform: translateY(-2px);
}

.stat-figure {
  transition: transform 0.3s ease;
}

.stat:hover .stat-figure {
  transform: scale(1.1);
}

.input {
  transition: all 0.3s ease;
}

.input:focus {
  outline: none;
  border-color: oklch(var(--p));
}

.btn-ghost {
  transition: all 0.3s ease;
}
</style>
