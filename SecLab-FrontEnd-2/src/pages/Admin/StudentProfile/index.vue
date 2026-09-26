<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getApiErrorMessage,
  getTeacherStudentAiAnalysis,
  getTeacherStudentProfile,
  type TeacherStudentAiAnalysisDto,
  type TeacherStudentProfileResponseDto,
} from '../../../api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref<string | null>(null)
const data = ref<TeacherStudentProfileResponseDto | null>(null)
const aiAnalysis = ref<TeacherStudentAiAnalysisDto | null>(null)
const aiAnalysisLoading = ref(false)
const aiAnalysisError = ref<string | null>(null)
let requestVersion = 0

const targetUserId = computed(() => Number(route.params.id || 0))
const latest = computed(() => data.value?.latestProfile || null)
const dashboard = computed(() => data.value?.dashboard || null)
const attempts = computed(() => data.value?.recentAttempts || [])
const recommendations = computed(() => data.value?.recommendations || [])
const profile = computed(() => dashboard.value?.learningProfile)
const aiFocusAreas = computed(() => aiAnalysis.value?.focusAreas || [])

const dimensions = computed(() => [
  { label: '知识掌握', value: latest.value?.knowledge_mastery_score || 0, icon: 'fa-book-open', tone: 'text-primary' },
  { label: '排障能力', value: latest.value?.troubleshooting_score || 0, icon: 'fa-screwdriver-wrench', tone: 'text-secondary' },
  { label: '自主探索', value: latest.value?.autonomy_score || 0, icon: 'fa-compass', tone: 'text-accent' },
  { label: 'AI 协同', value: latest.value?.ai_collaboration_score || 0, icon: 'fa-robot', tone: 'text-info' },
  { label: '学习投入', value: latest.value?.engagement_score || 0, icon: 'fa-fire', tone: 'text-success' },
])

function formatScore(value: number | string | null | undefined) {
  const numeric = Number(value || 0)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : '0.0'
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '暂无记录'
}

function boolText(value?: boolean | null) {
  if (value === true) return '正确'
  if (value === false) return '需复盘'
  return '待判定'
}

function priorityLabel(value?: string | null) {
  if (value === 'high') return '重点关注'
  if (value === 'medium') return '持续跟进'
  if (value === 'low') return '保持观察'
  return '个人建议'
}

function buildLocalFallbackAnalysis(): TeacherStudentAiAnalysisDto {
  return {
    scope: 'student',
    generatedBy: 'rule_fallback',
    fallbackUsed: true,
    generatedAt: new Date().toISOString(),
    overallComment: 'AI 分析暂不可用，已展示系统规则建议。',
    focusAreas: recommendations.value.map((item) => ({
      dimension: item.dimension,
      label: item.label,
      score: item.score,
      evidence: item.evidence || item.summary,
      teacherAction: item.teacherAction || item.summary,
      priority: item.priority || 'medium',
    })),
  }
}

async function fetchAiAnalysis(userId: number, version: number) {
  aiAnalysisLoading.value = true
  aiAnalysisError.value = null
  try {
    const response = await getTeacherStudentAiAnalysis(userId)
    if (version !== requestVersion || userId !== targetUserId.value) return
    aiAnalysis.value = response
  } catch (err) {
    if (version !== requestVersion || userId !== targetUserId.value) return
    aiAnalysisError.value = getApiErrorMessage(err, 'AI 分析暂不可用，已展示系统规则建议。')
    aiAnalysis.value = buildLocalFallbackAnalysis()
  } finally {
    if (version === requestVersion && userId === targetUserId.value) {
      aiAnalysisLoading.value = false
    }
  }
}

async function fetchProfile() {
  const userId = targetUserId.value
  const version = ++requestVersion
  data.value = null
  aiAnalysis.value = null
  aiAnalysisError.value = null
  aiAnalysisLoading.value = false

  if (!Number.isInteger(userId) || userId <= 0) {
    error.value = '无效的学生 ID'
    loading.value = false
    return
  }
  loading.value = true
  error.value = null
  try {
    const response = await getTeacherStudentProfile(userId)
    if (version !== requestVersion || userId !== targetUserId.value) return
    data.value = response
    void fetchAiAnalysis(userId, version)
  } catch (err) {
    if (version !== requestVersion || userId !== targetUserId.value) return
    error.value = getApiErrorMessage(err, '学生画像加载失败，请重新加载。')
  } finally {
    if (version === requestVersion && userId === targetUserId.value) {
      loading.value = false
    }
  }
}

watch(targetUserId, () => void fetchProfile(), { immediate: true })
</script>

<template>
  <div class="h-full overflow-y-auto bg-base-100 p-6">
    <div class="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-bold">学生画像详情</h1>
        <p class="mt-1 text-sm text-base-content/60">
          学生 ID：{{ targetUserId }} · 最近画像：{{ formatTime(latest?.computed_at) }}
        </p>
      </div>
      <button class="btn btn-ghost btn-sm" @click="router.back()">
        <i class="fas fa-arrow-left mr-2"></i>
        返回
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ error }}</span>
      <button class="btn btn-sm" @click="fetchProfile">重新加载</button>
    </div>

    <div v-else-if="!latest && !dashboard" class="rounded-lg border border-base-200 p-10 text-center text-base-content/60 shadow-sm">
      暂无学生画像数据
    </div>

    <template v-else>
      <div class="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <div class="stats rounded-lg border border-base-200 bg-base-100 shadow-sm">
          <div class="stat">
            <div class="stat-title">总体画像分</div>
            <div class="stat-value text-primary">{{ formatScore(latest?.overall_score) }}</div>
            <div class="stat-desc">最新画像快照</div>
          </div>
        </div>
        <div class="stats rounded-lg border border-base-200 bg-base-100 shadow-sm">
          <div class="stat">
            <div class="stat-title">完成课程</div>
            <div class="stat-value text-secondary">{{ dashboard?.userStats?.completedCourses || 0 }}</div>
            <div class="stat-desc">个人画像统计</div>
          </div>
        </div>
        <div class="stats rounded-lg border border-base-200 bg-base-100 shadow-sm">
          <div class="stat">
            <div class="stat-title">累计积分</div>
            <div class="stat-value text-accent">{{ dashboard?.userStats?.totalScore || 0 }}</div>
            <div class="stat-desc">训练与实验得分</div>
          </div>
        </div>
        <div class="stats rounded-lg border border-base-200 bg-base-100 shadow-sm">
          <div class="stat">
            <div class="stat-title">连续活跃</div>
            <div class="stat-value text-success">{{ dashboard?.userStats?.activeStreak || 0 }}</div>
            <div class="stat-desc">活跃天数</div>
          </div>
        </div>
      </div>

      <div class="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div class="xl:col-span-2 rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
          <h2 class="mb-4 text-lg font-bold">五维画像分</h2>
          <div class="space-y-4">
            <div v-for="item in dimensions" :key="item.label" class="rounded-md bg-base-200/50 p-4">
              <div class="mb-2 flex items-center justify-between">
                <div class="flex items-center gap-2 font-semibold">
                  <i :class="['fas', item.icon, item.tone]"></i>
                  {{ item.label }}
                </div>
                <span class="font-bold" :class="item.tone">{{ formatScore(item.value) }}</span>
              </div>
              <progress class="progress progress-primary h-3 w-full" :value="Number(item.value || 0)" max="100"></progress>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
          <h2 class="mb-4 text-lg font-bold">画像摘要</h2>
          <div class="space-y-4 text-sm">
            <div class="rounded-md bg-primary/10 p-4">
              <div class="mb-2 font-semibold text-primary">系统评价</div>
              <p>{{ profile?.evaluation || '暂无画像总结' }}</p>
            </div>
            <div class="rounded-md bg-info/10 p-4">
              <div class="mb-2 font-semibold text-info">近期关注</div>
              <p>{{ profile?.recentFocus || '暂无近期关注主题' }}</p>
            </div>
            <div class="rounded-md bg-base-200/70 p-4">
              <div class="mb-2 font-semibold">AI 个人教学干预建议</div>
              <div v-if="aiAnalysisLoading" class="flex items-center gap-2 text-base-content/60">
                <span class="loading loading-spinner loading-xs"></span>
                正在生成个人教学分析
              </div>
              <div v-else-if="aiAnalysis" class="space-y-3">
                <div v-if="aiAnalysis.fallbackUsed || aiAnalysisError" class="rounded-md bg-warning/10 p-3 text-warning-content">
                  AI 分析暂不可用，已展示系统规则建议。
                </div>
                <p class="text-base-content/75">{{ aiAnalysis.overallComment }}</p>
                <div v-if="aiFocusAreas.length" class="space-y-3">
                  <div v-for="item in aiFocusAreas" :key="item.dimension" class="rounded-md bg-base-100 p-3 text-base-content/75">
                    <div class="mb-2 flex items-center justify-between gap-3">
                      <span class="font-semibold text-base-content">
                        {{ item.label }}
                        <span v-if="item.score !== undefined && item.score !== null" class="text-xs font-normal text-base-content/55">
                          {{ formatScore(item.score) }} 分
                        </span>
                      </span>
                      <span class="badge badge-outline badge-sm">{{ priorityLabel(item.priority) }}</span>
                    </div>
                    <p class="text-xs text-base-content/60">{{ item.evidence }}</p>
                    <p class="mt-2 text-xs font-medium text-primary">{{ item.teacherAction }}</p>
                  </div>
                </div>
                <div v-else class="text-base-content/60">暂无个人干预建议</div>
              </div>
              <div v-else-if="recommendations.length" class="space-y-3">
                <div v-for="item in recommendations" :key="item.dimension" class="rounded-md bg-base-100 p-3 text-base-content/75">
                  <div class="mb-2 flex items-center justify-between gap-3">
                    <span class="font-semibold text-base-content">{{ item.label }}</span>
                    <span class="badge badge-outline badge-sm">{{ priorityLabel(item.priority) }}</span>
                  </div>
                  <p>{{ item.summary }}</p>
                  <p v-if="item.evidence" class="mt-2 text-xs text-base-content/55">{{ item.evidence }}</p>
                  <p v-if="item.teacherAction" class="mt-2 text-xs font-medium text-primary">{{ item.teacherAction }}</p>
                </div>
              </div>
              <div v-else class="text-base-content/60">暂无个人干预建议</div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div class="rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
          <h2 class="mb-4 text-lg font-bold">技能与标签</h2>
          <div class="mb-5 space-y-3">
            <div v-for="skill in profile?.skills || []" :key="skill.name">
              <div class="mb-1 flex justify-between text-sm">
                <span>{{ skill.name }}</span>
                <span>{{ formatScore(skill.score) }}</span>
              </div>
              <progress class="progress progress-secondary h-3 w-full" :value="skill.score" max="100"></progress>
            </div>
            <div v-if="!(profile?.skills || []).length" class="text-base-content/60">暂无技能得分数据</div>
          </div>
          <div class="flex flex-wrap gap-2">
            <span v-for="tag in profile?.tags || []" :key="`${tag.text}-${tag.type}`" class="badge badge-outline">
              {{ tag.text }}
            </span>
            <span v-if="!(profile?.tags || []).length" class="text-sm text-base-content/60">暂无画像标签</span>
          </div>
        </div>

        <div class="rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
          <h2 class="mb-4 text-lg font-bold">最近训练作答</h2>
          <div v-if="attempts.length" class="overflow-x-auto">
            <table class="table table-sm">
              <thead>
                <tr>
                  <th>题目</th>
                  <th>题型</th>
                  <th>得分</th>
                  <th>结果</th>
                  <th>时间</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="attempt in attempts" :key="attempt.attemptId">
                  <td>{{ attempt.title }}</td>
                  <td>{{ attempt.questionType || '未知' }}</td>
                  <td class="font-bold">{{ formatScore(attempt.score) }}</td>
                  <td>{{ boolText(attempt.isCorrect) }}</td>
                  <td>{{ formatTime(attempt.submittedAt) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="py-10 text-center text-base-content/60">暂无学生训练记录</div>
        </div>
      </div>
    </template>
  </div>
</template>
