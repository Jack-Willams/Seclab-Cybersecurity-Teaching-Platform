<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getApiErrorMessage,
  getTeacherDashboard,
  type TeacherDashboardResponseDto,
  type TeacherDashboardSummaryDto,
} from '../../../api'

const router = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)
const dashboard = ref<TeacherDashboardResponseDto | null>(null)

const emptySummary: TeacherDashboardSummaryDto = {
  classCount: 0,
  studentCount: 0,
  activeStudentCount: 0,
  generatedQuestionCount: 0,
  attemptCount: 0,
  averageProfileScore: 0,
  averageTrainingScore: 0,
}

const summary = computed(() => dashboard.value?.summary || emptySummary)
const weakDimensions = computed(() => dashboard.value?.weakDimensions || [])
const recentActivities = computed(() => dashboard.value?.recentActivities || [])
const topStudents = computed(() => dashboard.value?.topStudents || [])
const hasData = computed(() => {
  const data = summary.value
  return data.classCount > 0 ||
    data.studentCount > 0 ||
    data.generatedQuestionCount > 0 ||
    data.attemptCount > 0 ||
    weakDimensions.value.length > 0 ||
    recentActivities.value.length > 0
})

const cards = computed(() => [
  { label: '班级数', value: summary.value.classCount, desc: '真实班级记录', tone: 'text-primary', icon: 'fa-chalkboard-user' },
  { label: '学生数', value: summary.value.studentCount, desc: '有效学生账号', tone: 'text-secondary', icon: 'fa-users' },
  { label: '活跃学生', value: summary.value.activeStudentCount, desc: '来自学习事件与训练记录', tone: 'text-success', icon: 'fa-user-check' },
  { label: '平均画像分', value: formatScore(summary.value.averageProfileScore), desc: '最新画像快照均值', tone: 'text-info', icon: 'fa-chart-line' },
  { label: '平均训练分', value: formatScore(summary.value.averageTrainingScore), desc: 'AI 训练作答均值', tone: 'text-accent', icon: 'fa-pen-to-square' },
  { label: 'AI 生成题', value: summary.value.generatedQuestionCount, desc: '个性化训练题数量', tone: 'text-warning', icon: 'fa-wand-magic-sparkles' },
  { label: '训练作答', value: summary.value.attemptCount, desc: '学生训练作答记录', tone: 'text-error', icon: 'fa-list-check' },
])

function formatScore(value: number | string | null | undefined) {
  const numeric = Number(value || 0)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : '0.0'
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '暂无时间'
}

function eventLabel(value: string) {
  const map: Record<string, string> = {
    TRAINING_GENERATED_QUESTION_SUBMIT: '提交训练题',
    GENERATED_QUESTION_SUBMIT: '提交训练题',
    QUESTION_SUBMIT: '提交题目',
    FLAG_SUBMIT: '提交靶场答案',
    LAB_START: '启动靶场',
    LAB_STOP: '结束靶场',
    AI_INTERACTION: 'AI 交互',
    HINT_REQUEST: '请求提示',
  }
  return map[value] || value || '学习事件'
}

async function fetchDashboard() {
  loading.value = true
  error.value = null
  try {
    dashboard.value = await getTeacherDashboard()
  } catch (err) {
    error.value = getApiErrorMessage(err, '数据加载失败，请重新加载。')
    dashboard.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void fetchDashboard()
})
</script>

<template>
  <div class="h-full overflow-y-auto bg-base-100 p-6">
    <div class="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-bold">教师首页</h1>
        <p class="mt-1 text-sm text-base-content/60">班级、画像、训练题与学习事件的真实数据概览</p>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-outline btn-sm" @click="router.push('/admin/class-profile')">班级管理</button>
        <button class="btn btn-primary btn-sm" @click="router.push('/admin/generated-questions')">AI 生成题记录</button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ error }}</span>
      <button class="btn btn-sm" @click="fetchDashboard">重新加载</button>
    </div>

    <div v-else-if="!hasData" class="rounded-lg border border-base-200 bg-base-100 p-10 text-center text-base-content/60 shadow-sm">
      暂无训练数据
    </div>

    <template v-else>
      <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div v-for="card in cards" :key="card.label" class="stats rounded-lg border border-base-200 bg-base-100 shadow-sm">
          <div class="stat">
            <div class="stat-figure" :class="card.tone">
              <i :class="['fas', card.icon, 'text-2xl']"></i>
            </div>
            <div class="stat-title">{{ card.label }}</div>
            <div class="stat-value text-2xl" :class="card.tone">{{ card.value }}</div>
            <div class="stat-desc">{{ card.desc }}</div>
          </div>
        </div>
      </div>

      <div class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div class="xl:col-span-2 rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-bold">班级薄弱维度</h2>
            <span class="text-xs text-base-content/50">基于全班学生最新画像聚合</span>
          </div>
          <div v-if="weakDimensions.length" class="space-y-4">
            <div v-for="item in weakDimensions" :key="item.dimension">
              <div class="mb-2 flex items-center justify-between text-sm">
                <span class="font-medium">{{ item.label }}</span>
                <span>{{ formatScore(item.averageScore) }} 分 · {{ item.studentCount }} 人低于 70</span>
              </div>
              <progress class="progress progress-primary h-3 w-full" :value="item.averageScore" max="100"></progress>
            </div>
          </div>
          <div v-else class="py-10 text-center text-base-content/60">暂无班级薄弱点数据</div>
        </div>

        <div class="rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
          <h2 class="mb-4 text-lg font-bold">高分学生</h2>
          <div v-if="topStudents.length" class="space-y-3">
            <div v-for="student in topStudents" :key="student.userId" class="flex items-center justify-between rounded-lg bg-base-200/60 p-3">
              <div>
                <button class="font-semibold text-primary hover:underline" @click="router.push(`/admin/student-profile/${student.userId}`)">
                  {{ student.username }}
                </button>
                <div class="text-xs text-base-content/60">训练作答 {{ student.attemptCount }} 次</div>
              </div>
              <div class="text-lg font-bold">{{ formatScore(student.overallScore) }}</div>
            </div>
          </div>
          <div v-else class="py-10 text-center text-base-content/60">暂无学生画像摘要</div>
        </div>
      </div>

      <div class="rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
        <h2 class="mb-4 text-lg font-bold">近期学习事件</h2>
        <div v-if="recentActivities.length" class="overflow-x-auto">
          <table class="table">
            <thead>
              <tr>
                <th>学生</th>
                <th>事件</th>
                <th>摘要</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recentActivities" :key="`${item.userId}-${item.createdAt}-${item.eventType}`">
                <td>{{ item.username }}</td>
                <td>{{ eventLabel(item.eventType) }}</td>
                <td>{{ item.summary }}</td>
                <td>{{ formatTime(item.createdAt) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="py-10 text-center text-base-content/60">暂无训练数据</div>
      </div>
    </template>
  </div>
</template>
