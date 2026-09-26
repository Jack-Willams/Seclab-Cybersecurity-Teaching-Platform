<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Course } from '../../../types/course'
import { useRouter } from 'vue-router'
import type { Experiment } from '../../../types/experiment'
import {
  addCourseModule,
  deleteTeacherCourse,
  getApiErrorMessage,
  getTeacherCourseList,
  getTeacherLabList,
  removeCourseModule,
} from '../../../api'
import { showToast } from '../../../common'

const router = useRouter()

const isLoaded = ref(false)
const pageLoading = ref(false)
const pageError = ref('')
const pageNotice = ref('')

const courses = ref<Course[]>([])

const applyCourseExperimentCounts = () => {
  courses.value = courses.value.map((course) => ({
    ...course,
    experimentCount: (courseExperiments.value.get(course.id) || []).length,
  }))
}

const fetchCourses = async () => {
  pageLoading.value = true
  pageError.value = ''
  try {
    courses.value = await getTeacherCourseList()
    rebuildCourseExperimentMap()
  } catch (error) {
    console.error('获取课程列表失败:', error)
    courses.value = []
    pageError.value = getApiErrorMessage(error, '课程列表加载失败，请稍后重试。')
  } finally {
    pageLoading.value = false
  }
}

// 搜索和筛选条件
const filters = ref({
  search: '',
  category: '',
  difficulty: '',
  status: ''
})

// 课程分类
const categories = ['Web安全', '系统安全', '密码学', '网络攻防', '移动安全']

// 过滤后的课程列表
const filteredCourses = computed(() => {
  return courses.value.filter((course) => {
    if (filters.value.search && !course.name.toLowerCase().includes(filters.value.search.toLowerCase())) {
      return false
    }
    if (filters.value.category && course.category !== filters.value.category) {
      return false
    }
    if (filters.value.difficulty && course.difficulty !== parseInt(filters.value.difficulty)) {
      return false
    }
    if (filters.value.status && course.status !== filters.value.status) {
      return false
    }
    return true
  })
})

// 获取难度星级显示
const getDifficultyStars = (difficulty: number) => '★'.repeat(difficulty) + '☆'.repeat(5 - difficulty)

// 获取状态标签样式
const getStatusBadgeClass = (status: Course['status']) => ({
  'badge-success': status === 'published',
  'badge-warning': status === 'draft',
  'badge-error': status === 'archived'
})

// 获取状态文本
const getStatusText = (status: Course['status']) =>
  ({
    published: '已发布',
    draft: '草稿',
    archived: '已归档'
  }[status])

// 处理课程操作
const handleCreateCourse = () => {
  router.push('/admin/course/create')
}

const handleEdit = (course: Course) => {
  router.push(`/admin/course/${course.id}/edit`)
}

const handleDelete = async (course: Course) => {
  const confirmed = window.confirm(`确定要删除课程“${course.name}”吗？`)
  if (!confirmed) {
    return
  }

  try {
    await deleteTeacherCourse(course.id)
    showToast('课程删除成功')
    await Promise.all([fetchCourses(), fetchExperiments()])
  } catch (error) {
    console.error('删除课程失败:', error)
    showToast(getApiErrorMessage(error, '课程删除失败，请稍后重试'))
  }
}

// 实验管理相关状态
const experimentList = ref<Experiment[]>([])
const currentCourse = ref<Course | null>(null)
const showExperimentModal = ref(false)
const loading = ref(false)

// 课程关联的实验列表
const courseExperiments = ref<Map<number, number[]>>(new Map())

const rebuildCourseExperimentMap = () => {
  const nextMap = new Map<number, number[]>()
  courses.value.forEach((course) => nextMap.set(course.id, []))
  experimentList.value.forEach((experiment) => {
    const courseIds = experiment.courseIds?.length
      ? experiment.courseIds
      : experiment.courseId
        ? [experiment.courseId]
        : []
    courseIds.forEach((courseId) => {
      const experimentIds = nextMap.get(courseId)
      if (experimentIds) experimentIds.push(experiment.id)
    })
  })
  courseExperiments.value = nextMap
  applyCourseExperimentCounts()
}

const fetchCourseExperimentMap = async () => {
  try {
    experimentList.value = await getTeacherLabList()
    rebuildCourseExperimentMap()
  } catch (error) {
    console.error('获取课程实验关联失败:', error)
    courseExperiments.value = new Map(courses.value.map((course) => [course.id, []]))
    applyCourseExperimentCounts()
    pageNotice.value = getApiErrorMessage(error, '课程实验关联加载失败，请稍后刷新重试。')
  }
}

// 获取实验列表
const fetchExperiments = async () => {
  loading.value = true
  pageNotice.value = ''
  try {
    experimentList.value = await getTeacherLabList()
    rebuildCourseExperimentMap()
  } catch (error) {
    console.error('获取实验列表失败:', error)
    experimentList.value = []
    pageNotice.value = getApiErrorMessage(error, '实验列表加载失败，当前仅显示真实课程数据。')
  } finally {
    loading.value = false
  }
}

// 打开实验管理弹窗
const openExperimentModal = async (course: Course) => {
  currentCourse.value = course
  showExperimentModal.value = true
  if (!experimentList.value.length) {
    await fetchExperiments()
  }
}

// 获取该课程关联的实验列表
const getCourseExperiments = computed(() => {
  if (!currentCourse.value) return []
  const courseId = currentCourse.value.id
  return experimentList.value.filter(exp => {
    const experimentIds = courseExperiments.value.get(courseId) || []
    return experimentIds.includes(exp.id)
  })
})

// 获取可添加的实验列表（未关联当前课程的实验）
const getAvailableExperiments = computed(() => {
  if (!currentCourse.value) return []
  const courseId = currentCourse.value.id
  return experimentList.value.filter(exp => {
    const experimentIds = courseExperiments.value.get(courseId) || []
    return !experimentIds.includes(exp.id)
  })
})

// 添加实验到课程
const addExperimentToCourse = async (experimentId: number) => {
  if (!currentCourse.value) return
  try {
    loading.value = true
    await addCourseModule(currentCourse.value.id, experimentId)
    showToast('实验添加成功')
    await fetchExperiments()
  } catch (error) {
    console.error('添加实验失败:', error)
    showToast(getApiErrorMessage(error, '实验添加失败，请稍后重试'))
  } finally {
    loading.value = false
  }
}

// 从课程中移除实验
const removeExperimentFromCourse = async (experimentId: number) => {
  if (!currentCourse.value) return
  try {
    loading.value = true
    await removeCourseModule(currentCourse.value.id, experimentId)
    showToast('实验移除成功')
    await fetchExperiments()
  } catch (error) {
    console.error('移除实验失败:', error)
    showToast(getApiErrorMessage(error, '实验移除失败，请稍后重试'))
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([fetchCourses(), fetchCourseExperimentMap()])
  setTimeout(() => {
    isLoaded.value = true
  }, 100)
})
</script>

<template>
  <div class="container mx-auto p-4 min-h-screen">
    <!-- 页面标题 -->
    <div class="flex justify-between items-center mb-6" :class="{ 'animate-fade-in': isLoaded }">
      <h1 class="text-2xl font-bold">课程管理</h1>
      <button class="btn btn-primary" @click="handleCreateCourse">
        <i class="fas fa-plus mr-2"></i>
        创建课程
      </button>
    </div>

    <div v-if="pageError" class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ pageError }}</span>
      <button class="btn btn-sm" @click="fetchCourses">重新加载</button>
    </div>
    <div v-else-if="pageNotice" class="alert alert-warning mb-6">
      <span>{{ pageNotice }}</span>
    </div>

    <!-- 搜索和筛选 -->
    <div class="card bg-base-100 shadow-xl mb-6" :class="{ 'animate-slide-up': isLoaded }" style="animation-delay: 0.2s">
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">搜索</span>
            </label>
            <input type="text" class="input input-bordered" placeholder="搜索课程名称" v-model="filters.search" />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">分类</span>
            </label>
            <select class="select select-bordered" v-model="filters.category">
              <option value="">全部</option>
              <option v-for="category in categories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">难度</span>
            </label>
            <select class="select select-bordered" v-model="filters.difficulty">
              <option value="">全部</option>
              <option v-for="n in 5" :key="n" :value="n">{{ n }} 星</option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">状态</span>
            </label>
            <select class="select select-bordered" v-model="filters.status">
              <option value="">全部</option>
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="archived">已归档</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 课程列表 -->
    <div v-if="pageLoading" class="flex justify-center py-10">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>
    <div v-else-if="!filteredCourses.length && !courses.length" class="card bg-base-100 shadow-xl">
      <div class="card-body text-center py-10 text-base-content/60">
        暂无课程
      </div>
    </div>
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8" :class="{ 'animate-fade-in': isLoaded }" style="animation-delay: 0.3s">
      <div v-for="(course, index) in filteredCourses" :key="course.id" class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all duration-500 group backdrop-blur-sm" :style="{ animationDelay: `${index * 0.1}s` }" :class="{ 'animate-slide-up': isLoaded }">
        <!-- 课程封面 -->
        <figure class="relative overflow-hidden aspect-video">
          <img :src="course.cover" :alt="course.name" class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" />
          <div class="absolute inset-0 bg-gradient-to-t from-base-100 to-transparent opacity-60"></div>
          <div class="absolute top-2 right-2">
            <div class="badge" :class="getStatusBadgeClass(course.status)">
              {{ getStatusText(course.status) }}
            </div>
          </div>
        </figure>

        <div class="card-body">
          <!-- 课程信息 -->
          <h2 class="card-title group-hover:text-primary transition-colors">
            {{ course.name }}
            <div class="text-sm font-normal text-yellow-500">
              {{ getDifficultyStars(course.difficulty) }}
            </div>
          </h2>
          <p class="text-base-content/70">{{ course.description }}</p>

          <!-- 课程统计 -->
          <div class="flex gap-4 my-2 text-sm text-base-content/60">
            <div class="flex items-center gap-1">
              <i class="fas fa-users text-primary/70"></i>
              <span>{{ course.studentCount }} 名学生</span>
            </div>
            <div class="flex items-center gap-1">
              <i class="fas fa-flask text-primary/70"></i>
              <span>{{ course.experimentCount }} 个实验</span>
              <button 
                class="btn btn-xs btn-circle btn-ghost hover:bg-primary/20"
                @click.stop="openExperimentModal(course)"
                title="添加实验">
                <i class="fas fa-plus text-primary"></i>
              </button>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions justify-end mt-4">
            <div class="flex gap-2">
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform"
                      @click.stop="openExperimentModal(course)">
                <i class="fas fa-flask"></i>
                实验
              </button>
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform"
                      @click.stop="handleEdit(course)">
                <i class="fas fa-edit"></i>
                编辑
              </button>
              <button class="btn btn-sm btn-ghost gap-1 group-hover:scale-105 transition-transform text-error"
                      @click.stop="handleDelete(course)">
                <i class="fas fa-trash"></i>
                删除
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 实验管理弹窗 -->
    <dialog :open="showExperimentModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <div class="flex justify-between items-center mb-4">
          <h3 class="font-bold text-lg">
            {{ currentCourse?.name }} - 实验管理
          </h3>
          <button class="btn btn-sm btn-circle btn-ghost" @click="showExperimentModal = false">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div v-if="loading" class="flex justify-center py-8">
          <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
        <div v-else>
          <!-- 当前课程关联的实验列表 -->
          <div v-if="getCourseExperiments.length > 0" class="mb-6">
            <h4 class="font-semibold text-base mb-2 flex items-center gap-2">
              <i class="fas fa-link text-primary"></i>
              已关联实验
            </h4>
            <div class="space-y-3">
              <div v-for="experiment in getCourseExperiments" :key="experiment.id" 
                   class="bg-base-200 rounded-lg p-3 flex justify-between items-center">
                <div>
                  <div class="font-medium">{{ experiment.name }}</div>
                  <div class="text-sm text-base-content/60">{{ experiment.description }}</div>
                  <div class="flex gap-2 items-center mt-1">
                    <span class="text-yellow-500 text-xs">{{ getDifficultyStars(experiment.difficulty) }}</span>
                    <span class="badge badge-sm" :class="getStatusBadgeClass(experiment.status)">
                      {{ getStatusText(experiment.status) }}
                    </span>
                  </div>
                </div>
                <button class="btn btn-sm btn-ghost hover:bg-error/20" 
                        @click="removeExperimentFromCourse(experiment.id)"
                        title="移除实验">
                  <i class="fas fa-unlink text-error"></i>
                </button>
              </div>
            </div>
          </div>
          <div v-else class="alert alert-info mb-6">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>该课程暂未关联任何实验</span>
          </div>

          <!-- 可添加的实验列表 -->
          <div>
            <h4 class="font-semibold text-base mb-2 flex items-center gap-2">
              <i class="fas fa-plus-circle text-primary"></i>
              添加实验
            </h4>
            <div v-if="getAvailableExperiments.length > 0" class="space-y-3">
              <div v-for="experiment in getAvailableExperiments" :key="experiment.id" 
                   class="bg-base-200 rounded-lg p-3 flex justify-between items-center">
                <div>
                  <div class="font-medium">{{ experiment.name }}</div>
                  <div class="text-sm text-base-content/60">{{ experiment.description }}</div>
                  <div class="flex gap-2 items-center mt-1">
                    <span class="text-yellow-500 text-xs">{{ getDifficultyStars(experiment.difficulty) }}</span>
                    <span class="badge badge-sm" :class="getStatusBadgeClass(experiment.status)">
                      {{ getStatusText(experiment.status) }}
                    </span>
                  </div>
                </div>
                <button class="btn btn-sm btn-primary" 
                        @click="addExperimentToCourse(experiment.id)">
                  <i class="fas fa-plus"></i>
                  添加
                </button>
              </div>
            </div>
            <div v-else class="alert">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="stroke-current shrink-0 w-6 h-6"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <span>已添加全部可用实验</span>
            </div>
          </div>
        </div>

        <div class="modal-action">
          <button class="btn" @click="showExperimentModal = false">关闭</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showExperimentModal = false">关闭</button>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.container {
  max-width: 1400px;
  height: 100%;
  overflow-y: auto;
}

.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
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
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 卡片悬停效果 */
.card {
  cursor: pointer;
  transform-style: preserve-3d;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: center;
  will-change: transform;
  border: 1px solid rgba(0, 0, 0, 0.1);
  position: relative;
}

.card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border-color: rgba(0, 242, 254, 0.3);
  background: linear-gradient(45deg, rgba(0, 242, 254, 0.05), rgba(79, 172, 254, 0.05));
}

/* 图标动画 */
.fas {
  transition: transform 0.3s ease;
}

.card:hover .fas {
  transform: scale(1.1);
}

/* 标签动画 */
.badge {
  transition: all 0.3s ease;
}

.badge:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>
