<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  getApiErrorMessage,
  getGeneratedQuestionSummary,
  getTeacherCourseList,
  getTeacherGeneratedQuestionRecords,
  getTeachingClasses,
  setGeneratedQuestionTypical,
  type TeacherGeneratedQuestionRecord,
  type TeacherGeneratedQuestionSummary,
  type TeachingClassDto,
} from '../../../api'
import type { Course } from '../../../types/course'

const records = ref<TeacherGeneratedQuestionRecord[]>([])
const classes = ref<TeachingClassDto[]>([])
const courses = ref<Course[]>([])
const total = ref(0)
const loading = ref(true)
const isLoaded = ref(false)
const error = ref('')
const selected = ref<TeacherGeneratedQuestionRecord | null>(null)
const summary = ref<TeacherGeneratedQuestionSummary | null>(null)
const summaryLoading = ref(false)
const page = ref(1)
const filters = ref({ teachingClassId: '', courseId: '', answerResult: '', typicalOnly: false, dateFrom: '', dateTo: '' })
let refreshTimer: number | undefined

const selectedClassName = computed(() => classes.value.find((item) => item.teachingClassId === Number(filters.value.teachingClassId))?.className || '')
const typeText = (value?: string | null) => ({ single_choice: '单选题', fill_blank: '填空题', short_answer: '简答题' }[value || ''] || value || '未分类')
const resultText = (item: TeacherGeneratedQuestionRecord) => !item.latestAttempt ? '未作答' : item.latestAttempt.isCorrect === true ? '正确' : item.latestAttempt.isCorrect === false ? '错误' : '已作答'
// 原来返回 green/red/gray/amber 自定义类名，现在直接给 daisyUI 的 badge 修饰类
const resultBadge = (item: TeacherGeneratedQuestionRecord) => !item.latestAttempt
  ? 'badge-ghost'
  : item.latestAttempt.isCorrect === true ? 'badge-success' : item.latestAttempt.isCorrect === false ? 'badge-error' : 'badge-warning'
const formatTime = (value?: string | null) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'

const loadRecords = async (quiet = false) => {
  if (!quiet) loading.value = true
  error.value = ''
  try {
    const data = await getTeacherGeneratedQuestionRecords({
      teachingClassId: filters.value.teachingClassId ? Number(filters.value.teachingClassId) : undefined,
      courseId: filters.value.courseId ? Number(filters.value.courseId) : undefined,
      answerResult: filters.value.answerResult as '' | 'correct' | 'incorrect' | 'attempted' | 'unanswered',
      typicalOnly: filters.value.typicalOnly,
      dateFrom: filters.value.dateFrom || undefined,
      dateTo: filters.value.dateTo || undefined,
      page: page.value,
      size: 20,
    })
    records.value = data.items; total.value = data.total
  } catch (err) { error.value = getApiErrorMessage(err, '生成题记录加载失败，请稍后重试。') }
  finally {
    loading.value = false
    setTimeout(() => { isLoaded.value = true }, 100)
  }
}

const loadSummary = async () => {
  if (!filters.value.teachingClassId) { summary.value = null; return }
  summaryLoading.value = true
  try { summary.value = await getGeneratedQuestionSummary(Number(filters.value.teachingClassId)) }
  catch { summary.value = null }
  finally { summaryLoading.value = false }
}

const applyFilters = async () => { page.value = 1; await Promise.all([loadRecords(), loadSummary()]) }
const resetFilters = () => { filters.value = { teachingClassId: '', courseId: '', answerResult: '', typicalOnly: false, dateFrom: '', dateTo: '' }; summary.value = null; void applyFilters() }
const toggleTypical = async (item: TeacherGeneratedQuestionRecord) => {
  const next = !item.isTypical
  try { await setGeneratedQuestionTypical(item.generatedQuestionId, next); item.isTypical = next; if (selected.value?.generatedQuestionId === item.generatedQuestionId) selected.value.isTypical = next }
  catch (err) { error.value = getApiErrorMessage(err, '代表题标记失败。') }
}
const goPage = (next: number) => { page.value = next; void loadRecords() }

onMounted(async () => {
  const [classResult, courseResult] = await Promise.allSettled([getTeachingClasses(), getTeacherCourseList()])
  classes.value = classResult.status === 'fulfilled' ? classResult.value : []
  courses.value = courseResult.status === 'fulfilled' ? courseResult.value : []
  await loadRecords()
  refreshTimer = window.setInterval(() => void loadRecords(true), 30000)
})
onBeforeUnmount(() => { if (refreshTimer) window.clearInterval(refreshTimer) })
</script>

<template>
  <div class="mx-auto min-h-full max-w-[1540px] px-5 pb-14 pt-8 lg:px-10">
    <header
      class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between"
      :class="{ 'animate-fade-in': isLoaded }"
    >
      <div>
        <h1 class="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-3xl font-bold text-transparent">
          生成题记录
        </h1>
        <p class="mt-1.5 text-sm text-base-content/70">学生端生成题目后直接同步到这里，教师可查看题目及作答情况。</p>
      </div>
      <button class="btn btn-outline btn-sm gap-2 self-start" @click="loadRecords()">
        <i class="fas fa-rotate" :class="{ 'animate-spin': loading }"></i>刷新记录
      </button>
    </header>

    <section class="card mb-5 bg-base-100 shadow-lg" :class="{ 'animate-slide-up': isLoaded }">
      <div class="card-body gap-4 p-5">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">教学班</span></div>
            <select v-model="filters.teachingClassId" class="select select-bordered select-sm">
              <option value="">全部教学班</option>
              <option v-for="item in classes" :key="item.teachingClassId" :value="item.teachingClassId">{{ item.className }}</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">课程</span></div>
            <select v-model="filters.courseId" class="select select-bordered select-sm">
              <option value="">全部课程</option>
              <option v-for="item in courses" :key="item.id" :value="item.id">{{ item.name }}</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">作答情况</span></div>
            <select v-model="filters.answerResult" class="select select-bordered select-sm">
              <option value="">全部</option>
              <option value="correct">回答正确</option>
              <option value="incorrect">回答错误</option>
              <option value="attempted">已作答</option>
              <option value="unanswered">未作答</option>
            </select>
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">生成日期从</span></div>
            <input v-model="filters.dateFrom" type="date" class="input input-sm input-bordered" />
          </label>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">到</span></div>
            <input v-model="filters.dateTo" type="date" class="input input-sm input-bordered" />
          </label>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3">
          <label class="label cursor-pointer justify-start gap-2 py-0">
            <input v-model="filters.typicalOnly" type="checkbox" class="checkbox checkbox-primary checkbox-sm" />
            <span class="label-text text-xs">只看我标记的代表题</span>
          </label>
          <div class="flex gap-2">
            <button class="btn btn-ghost btn-sm" @click="resetFilters">重置</button>
            <button class="btn btn-primary btn-sm gap-2" @click="applyFilters"><i class="fas fa-magnifying-glass"></i>查询</button>
          </div>
        </div>
      </div>
    </section>

    <section
      v-if="filters.teachingClassId"
      class="card mb-5 bg-base-100 shadow-lg"
      :class="{ 'animate-slide-up': isLoaded }"
      style="animation-delay: .05s"
    >
      <div class="flex items-center justify-between gap-4 border-b border-base-200 p-5">
        <div>
          <h2 class="text-base font-semibold">{{ selectedClassName }} · 共性题目概览</h2>
          <p class="mt-0.5 text-xs text-base-content/60">系统按知识点聚合当前学生生成题与作答结果</p>
        </div>
        <span class="badge badge-ghost badge-sm">实时统计</span>
      </div>
      <div v-if="summaryLoading" class="flex justify-center py-10">
        <span class="loading loading-spinner loading-md text-primary"></span>
      </div>
      <div v-else-if="summary?.items.length" class="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="item in summary.items.slice(0, 4)"
          :key="String(item.knowledgePointId)"
          class="rounded-lg bg-base-200 p-4"
        >
          <strong class="block text-sm">{{ item.knowledgePointName }}</strong>
          <span class="mt-1 block text-xs text-base-content/60">{{ item.generatedQuestionCount }} 道题 · {{ item.studentCount }} 名学生</span>
          <span class="mt-2 inline-block text-xs font-semibold text-warning">错误作答 {{ Math.round(item.incorrectRate * 100) }}%</span>
        </div>
      </div>
      <div v-else class="flex min-h-[120px] items-center justify-center text-sm text-base-content/60">
        该教学班暂无可汇总的生成题。
      </div>
    </section>

    <section class="card bg-base-100 shadow-lg" :class="{ 'animate-slide-up': isLoaded }" style="animation-delay: .1s">
      <div class="border-b border-base-200 p-5">
        <h2 class="text-base font-semibold">题目记录</h2>
        <p class="mt-0.5 text-xs text-base-content/60">每 30 秒自动同步一次，共 {{ total }} 条</p>
      </div>

      <div v-if="error" class="p-5 pb-0">
        <div class="alert alert-error"><i class="fas fa-circle-exclamation"></i><span>{{ error }}</span></div>
      </div>

      <div v-if="loading" class="flex justify-center py-16">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <div v-else-if="!records.length" class="flex min-h-[240px] flex-col items-center justify-center gap-2 p-6 text-center">
        <i class="fas fa-wand-magic-sparkles text-4xl text-base-content/25"></i>
        <h3 class="text-lg font-semibold">暂无生成题记录</h3>
        <p class="text-sm text-base-content/70">学生在训练中生成题目后，会同步显示在这里。</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table table-zebra">
          <thead class="bg-base-200/60">
            <tr><th>题目</th><th>学生</th><th>教学班 / 课程</th><th>知识点</th><th class="text-center">作答</th><th>生成时间</th><th class="text-center">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="item in records" :key="item.generatedQuestionId">
              <td class="min-w-[230px]">
                <strong class="block max-w-[300px] truncate">{{ item.title }}</strong>
                <span class="mt-0.5 block text-xs text-base-content/60">{{ typeText(item.questionType) }} · {{ item.difficulty || '未标难度' }}</span>
              </td>
              <td>
                <strong class="block">{{ item.student.studentName }}</strong>
                <span class="text-xs text-base-content/60">{{ item.student.studentNumber || '无学号' }}</span>
              </td>
              <td>
                {{ item.teachingClassName }}
                <div class="text-xs text-base-content/60">{{ item.courseName || '未关联课程' }}</div>
              </td>
              <td>{{ item.knowledgePointName || '未标注' }}</td>
              <td class="text-center">
                <span class="badge badge-sm" :class="resultBadge(item)">{{ resultText(item) }}</span>
                <div v-if="item.latestAttempt" class="mt-1 text-xs text-base-content/60">{{ item.latestAttempt.score }} 分</div>
              </td>
              <td class="whitespace-nowrap text-base-content/70">{{ formatTime(item.generatedAt) }}</td>
              <td>
                <div class="flex justify-center gap-1 whitespace-nowrap">
                  <button class="btn btn-ghost btn-xs" @click="selected = item">查看</button>
                  <button
                    class="btn btn-xs gap-1"
                    :class="item.isTypical ? 'btn-warning' : 'btn-ghost'"
                    @click="toggleTypical(item)"
                  >
                    <i class="fas fa-star text-[10px]"></i>{{ item.isTypical ? '已标记' : '标为代表题' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="total > 20" class="flex items-center justify-end gap-3 border-t border-base-200 p-4">
        <div class="join">
          <button class="btn join-item btn-sm" :disabled="page === 1" @click="goPage(page - 1)">上一页</button>
          <button class="btn btn-active join-item btn-sm">第 {{ page }} 页</button>
          <button class="btn join-item btn-sm" :disabled="page * 20 >= total" @click="goPage(page + 1)">下一页</button>
        </div>
      </div>
    </section>

    <!-- 题目详情抽屉 -->
    <div v-if="selected" class="fixed inset-0 z-[70] bg-neutral/40" @click.self="selected = null">
      <aside class="absolute inset-y-0 right-0 flex w-[min(620px,92vw)] flex-col bg-base-100 shadow-2xl">
        <div class="flex items-start justify-between gap-4 border-b border-base-200 p-6">
          <div class="min-w-0">
            <span class="text-xs text-base-content/60">{{ selected.teachingClassName }} · {{ selected.student.studentName }}</span>
            <h2 class="mt-1.5 text-lg font-bold">{{ selected.title }}</h2>
          </div>
          <button class="btn btn-ghost btn-sm btn-circle" @click="selected = null">✕</button>
        </div>

        <div class="flex-1 overflow-auto p-6">
          <div class="flex flex-wrap items-center gap-2 text-xs text-base-content/60">
            <span class="badge badge-primary badge-sm">{{ typeText(selected.questionType) }}</span>
            <span>{{ selected.courseName || '未关联课程' }}</span>
            <span>·</span>
            <span>{{ selected.knowledgePointName || '未标注知识点' }}</span>
            <span>·</span>
            <span>{{ formatTime(selected.generatedAt) }}</span>
          </div>

          <section class="border-b border-base-200 py-5">
            <h3 class="mb-2.5 text-sm font-semibold">题目内容</h3>
            <p class="rounded-lg bg-base-200 p-3.5 text-sm leading-relaxed">{{ selected.stem }}</p>
            <ol v-if="selected.options.length" class="mt-3 list-decimal space-y-1 pl-5 text-xs leading-relaxed text-base-content/70">
              <li v-for="option in selected.options" :key="option">{{ option }}</li>
            </ol>
          </section>

          <section v-if="selected.generationReason" class="border-b border-base-200 py-5">
            <h3 class="mb-2.5 text-sm font-semibold">生成原因</h3>
            <p class="text-xs leading-relaxed text-base-content/70">{{ selected.generationReason }}</p>
          </section>

          <section v-if="selected.latestAttempt" class="border-b border-base-200 py-5">
            <h3 class="mb-2.5 text-sm font-semibold">学生最近作答</h3>
            <p class="text-xs leading-relaxed text-base-content/70">{{ selected.latestAttempt.answer }}</p>
            <div class="mt-2 text-xs text-primary">
              {{ resultText(selected) }} · {{ selected.latestAttempt.score }} 分 · {{ formatTime(selected.latestAttempt.submittedAt) }}
            </div>
          </section>

          <section class="py-5">
            <h3 class="mb-2.5 text-sm font-semibold">参考信息</h3>
            <p class="text-xs leading-relaxed text-base-content/70">
              <strong class="text-base-content">参考答案：</strong>{{ selected.referenceAnswer || selected.standardAnswer || '暂无' }}
            </p>
            <p class="mt-2 text-xs leading-relaxed text-base-content/70">
              <strong class="text-base-content">解析：</strong>{{ selected.explanation || '暂无' }}
            </p>
          </section>
        </div>

        <div class="border-t border-base-200 p-5">
          <button
            class="btn btn-sm gap-2"
            :class="selected.isTypical ? 'btn-warning' : 'btn-outline'"
            @click="toggleTypical(selected)"
          >
            <i class="fas fa-star text-xs"></i>{{ selected.isTypical ? '取消代表题标记' : '标为代表题' }}
          </button>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
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
</style>
