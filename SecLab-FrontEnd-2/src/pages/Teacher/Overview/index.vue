<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  getApiErrorMessage,
  getGeneratedQuestionSummary,
  getTeachingClassAnalysis,
  getTeachingClassCourses,
  getTeachingClasses,
  getTeachingClassStudents,
  type TeacherGeneratedQuestionSummary,
  type TeachingClassAnalysisDto,
  type TeachingClassCourseDto,
  type TeachingClassDto,
  type TeachingClassStudentDto,
} from '../../../api'

const classes = ref<TeachingClassDto[]>([])
const selectedId = ref<number | null>(null)
const students = ref<TeachingClassStudentDto[]>([])
const courses = ref<TeachingClassCourseDto[]>([])
const summary = ref<TeacherGeneratedQuestionSummary | null>(null)
const analysis = ref<TeachingClassAnalysisDto | null>(null)
const loading = ref(true)
const detailLoading = ref(false)
const error = ref('')
// 和学生端课程页一致：首屏渲染后再放动画，避免刷新时元素闪一下
const isLoaded = ref(false)

const selectedClass = computed(() => classes.value.find((item) => item.teachingClassId === selectedId.value) || null)
const recentStudents = computed(() => [...students.value]
  .filter((item) => item.recentActivityAt)
  .sort((a, b) => String(b.recentActivityAt).localeCompare(String(a.recentActivityAt)))
  .slice(0, 5))
const generatedCount = computed(() => summary.value?.items.reduce((total, item) => total + item.generatedQuestionCount, 0) || 0)

const formatDateTime = (value?: string | null) => value
  ? new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
  : '暂无记录'

const loadDetail = async () => {
  if (!selectedId.value) return
  detailLoading.value = true
  const classId = selectedId.value
  const [studentResult, courseResult, summaryResult, analysisResult] = await Promise.allSettled([
    getTeachingClassStudents(classId),
    getTeachingClassCourses(classId),
    getGeneratedQuestionSummary(classId),
    getTeachingClassAnalysis(classId),
  ])
  if (classId !== selectedId.value) return
  students.value = studentResult.status === 'fulfilled' ? studentResult.value : []
  courses.value = courseResult.status === 'fulfilled' ? courseResult.value : []
  summary.value = summaryResult.status === 'fulfilled' ? summaryResult.value : null
  analysis.value = analysisResult.status === 'fulfilled' ? analysisResult.value : null
  detailLoading.value = false
}

const loadClasses = async () => {
  loading.value = true
  error.value = ''
  try {
    classes.value = (await getTeachingClasses()).filter((item) => item.status !== 'ARCHIVED')
    if (!selectedId.value || !classes.value.some((item) => item.teachingClassId === selectedId.value)) {
      selectedId.value = classes.value[0]?.teachingClassId || null
    }
  } catch (err) {
    error.value = getApiErrorMessage(err, '教学班加载失败，请稍后重试。')
  } finally {
    loading.value = false
    setTimeout(() => { isLoaded.value = true }, 100)
  }
}

watch(selectedId, () => void loadDetail())
onMounted(() => void loadClasses())
</script>

<template>
  <div class="mx-auto min-h-full max-w-[1540px] px-5 pb-14 pt-8 lg:px-10">
    <header
      class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between"
      :class="{ 'animate-fade-in': isLoaded }"
    >
      <div>
        <h1 class="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-3xl font-bold text-transparent">
          教学概览
        </h1>
        <p class="mt-1.5 text-sm text-base-content/70">查看教学班当前进度、学生学习动态和最近一次班级分析。</p>
      </div>
      <select v-model="selectedId" class="select select-bordered select-sm w-full md:w-auto md:min-w-[340px]" aria-label="选择教学班">
        <option v-for="item in classes" :key="item.teachingClassId" :value="item.teachingClassId">
          {{ item.academicYear }}学年 第{{ item.semester }}学期 · {{ item.className }}
        </option>
      </select>
    </header>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else-if="error" class="alert alert-error">
      <i class="fas fa-circle-exclamation"></i>
      <span>{{ error }}</span>
      <button class="btn btn-sm" @click="loadClasses">重新加载</button>
    </div>

    <div v-else-if="!selectedClass" class="card bg-base-100 shadow-xl">
      <div class="card-body items-center py-14 text-center">
        <i class="fas fa-chalkboard-user mb-1 text-4xl text-base-content/25"></i>
        <h3 class="text-lg font-semibold">还没有教学班</h3>
        <p class="text-sm text-base-content/70">创建本学期的教学班后，教学进度和学生数据会显示在这里。</p>
        <RouterLink class="btn btn-primary btn-sm mt-2 gap-2" to="/teacher/classes">
          <i class="fas fa-plus"></i>创建教学班
        </RouterLink>
      </div>
    </div>

    <template v-else>
      <section class="card mb-4 bg-base-100 shadow-lg" :class="{ 'animate-slide-up': isLoaded }">
        <div class="card-body flex-row flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <span class="text-xs font-bold tracking-[.08em] text-primary">当前教学班</span>
            <h2 class="mt-1 text-2xl font-bold">{{ selectedClass.className }}</h2>
            <p class="mt-0.5 text-xs text-base-content/60">
              {{ selectedClass.teacherName || '任课教师' }} · {{ selectedClass.academicYear }}学年 第{{ selectedClass.semester }}学期
            </p>
          </div>
          <div class="badge badge-success badge-outline gap-2 py-3">
            <span class="inline-block h-1.5 w-1.5 rounded-full bg-success"></span>授课中
          </div>
        </div>
      </section>

      <div class="stats mb-6 w-full bg-base-100 shadow" :class="{ 'animate-slide-up': isLoaded }" style="animation-delay: .05s">
        <div class="stat py-3">
          <div class="stat-figure text-primary"><i class="fas fa-users text-xl"></i></div>
          <div class="stat-title text-xs">学生人数</div>
          <div class="stat-value text-xl text-primary">{{ selectedClass.studentCount }}</div>
          <div class="stat-desc text-xs">已导入名单</div>
        </div>
        <div class="stat py-3">
          <div class="stat-figure text-secondary"><i class="fas fa-book-open text-xl"></i></div>
          <div class="stat-title text-xs">教学课程</div>
          <div class="stat-value text-xl text-secondary">{{ selectedClass.courseCount }}</div>
          <div class="stat-desc text-xs">按顺序安排</div>
        </div>
        <div class="stat py-3">
          <div class="stat-figure text-info"><i class="fas fa-wand-magic-sparkles text-xl"></i></div>
          <div class="stat-title text-xs">学生生成题</div>
          <div class="stat-value text-xl text-info">{{ generatedCount }}</div>
          <div class="stat-desc text-xs">实时同步</div>
        </div>
        <div class="stat py-3">
          <div class="stat-figure text-accent"><i class="fas fa-clock text-xl"></i></div>
          <div class="stat-title text-xs">最近活动</div>
          <div class="stat-value text-base text-accent">{{ formatDateTime(selectedClass.lastActiveAt) }}</div>
          <div class="stat-desc text-xs">学生学习记录</div>
        </div>
      </div>

      <div
        class="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(310px,.85fr)]"
        :class="[{ 'animate-slide-up': isLoaded }, detailLoading ? 'opacity-60' : '']"
        style="animation-delay: .1s"
      >
        <section class="card bg-base-100 shadow-lg">
          <div class="flex items-center justify-between gap-4 border-b border-base-200 p-5">
            <div>
              <h2 class="text-base font-semibold">最近教学分析</h2>
              <p class="mt-0.5 text-xs text-base-content/60">分析操作集中在“教学分析”页面</p>
            </div>
            <RouterLink class="btn btn-ghost btn-xs gap-1 text-primary" :to="`/teacher/analysis?classId=${selectedClass.teachingClassId}`">
              进入教学分析<i class="fas fa-arrow-right text-[10px]"></i>
            </RouterLink>
          </div>
          <div v-if="analysis?.analysis" class="min-h-[190px] p-6">
            <span class="text-xs text-base-content/60">分析时间 {{ formatDateTime(analysis.generatedAt) }}</span>
            <p class="my-3 rounded-r-lg border-l-[3px] border-primary bg-base-200 px-4 py-3.5 text-sm leading-relaxed">
              {{ analysis.analysis.overallComment }}
            </p>
            <small class="text-xs text-base-content/60">
              共整理 {{ analysis.analysis.commonProblems?.length || 0 }} 项班级共性问题
            </small>
          </div>
          <div v-else class="flex min-h-[190px] flex-col items-center justify-center gap-2 p-8 text-center">
            <i class="fas fa-chart-simple text-3xl text-base-content/25"></i>
            <strong class="text-[15px]">尚未进行班级分析</strong>
            <p class="max-w-[540px] text-xs leading-relaxed text-base-content/60">
              学生数据会持续同步，需要时可前往“教学分析”手动生成结果。
            </p>
          </div>
        </section>

        <section class="card bg-base-100 shadow-lg">
          <div class="flex items-center justify-between gap-4 border-b border-base-200 p-5">
            <div>
              <h2 class="text-base font-semibold">教学安排</h2>
              <p class="mt-0.5 text-xs text-base-content/60">当前教学班关联的课程顺序</p>
            </div>
            <RouterLink to="/teacher/classes" class="btn btn-ghost btn-xs gap-1 text-primary">
              调整安排<i class="fas fa-arrow-right text-[10px]"></i>
            </RouterLink>
          </div>
          <div v-if="courses.length" class="course-rail px-5 pb-6 pt-4">
            <div v-for="(course, index) in courses" :key="course.courseId" class="rail-item flex gap-3 pb-5">
              <span class="rail-number z-10 grid h-6 w-6 flex-none place-items-center rounded-full bg-primary/15 text-[11px] font-bold text-primary">
                {{ index + 1 }}
              </span>
              <div class="min-w-0">
                <strong class="block pt-0.5 text-[13px]">{{ course.courseName }}</strong>
                <small class="mt-1 block text-[11px] text-base-content/60">
                  {{ course.plannedStartDate || '未设置日期' }}
                  <template v-if="course.plannedEndDate"> 至 {{ course.plannedEndDate }}</template>
                </small>
              </div>
            </div>
          </div>
          <div v-else class="flex min-h-[160px] flex-col items-center justify-center gap-2 text-sm text-base-content/60">
            <i class="fas fa-list-ol text-3xl text-base-content/25"></i>
            尚未安排课程
          </div>
        </section>
      </div>

      <section class="card mt-5 bg-base-100 shadow-lg" :class="{ 'animate-slide-up': isLoaded }" style="animation-delay: .15s">
        <div class="border-b border-base-200 p-5">
          <h2 class="text-base font-semibold">最近学生动态</h2>
          <p class="mt-0.5 text-xs text-base-content/60">来自学生端的学习活动时间</p>
        </div>
        <div v-if="recentStudents.length" class="overflow-x-auto">
          <table class="table table-zebra">
            <thead class="bg-base-200/60">
              <tr><th>学生</th><th>学号</th><th>行政班</th><th>最近活动</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in recentStudents" :key="item.studentId">
                <td class="font-semibold">{{ item.studentName || '未填写姓名' }}</td>
                <td>{{ item.studentNumber }}</td>
                <td>{{ item.administrativeClass || '—' }}</td>
                <td class="text-base-content/70">{{ formatDateTime(item.recentActivityAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="flex min-h-[140px] flex-col items-center justify-center gap-2 text-sm text-base-content/60">
          <i class="fas fa-user-clock text-3xl text-base-content/25"></i>
          暂无学生学习活动
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
/* 时间轴竖线：Tailwind 表达不了 ::after 的定位，留一条自定义规则 */
.rail-item:not(:last-child)::after {
  position: absolute;
  top: 25px;
  bottom: 2px;
  left: 12px;
  width: 1px;
  background: oklch(var(--bc) / .12);
  content: '';
}
.course-rail {
  position: relative;
}
.rail-item {
  position: relative;
}

/* 动画与学生端课程页保持一致 */
.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
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
</style>
