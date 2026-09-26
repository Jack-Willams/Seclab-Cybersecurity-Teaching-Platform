<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  avatarUrl,
  getApiErrorMessage,
  getTeacherClassAiAnalysis,
  getTeacherClasses,
  getTeacherClassStudents,
  type TeacherClassAiAnalysisDto,
  type TeacherClassDto,
  type TeacherClassStudentDto,
} from '../../../api'

const router = useRouter()
const loading = ref(false)
const studentsLoading = ref(false)
const error = ref<string | null>(null)
const studentsError = ref<string | null>(null)
const classAiError = ref<string | null>(null)
const classes = ref<TeacherClassDto[]>([])
const selectedClassId = ref<number | null>(null)
const students = ref<TeacherClassStudentDto[]>([])
const classAiAnalysis = ref<TeacherClassAiAnalysisDto | null>(null)
const classAiLoading = ref(false)
let classRequestVersion = 0

const selectedClass = computed(() => classes.value.find((item) => item.classId === selectedClassId.value) || null)
const classAiSuggestions = computed(() => classAiAnalysis.value?.suggestions || [])
const weakDimensions = computed(() => {
  const dimensions = [
    { dimension: 'knowledge_mastery', key: 'knowledgeMasteryScore', label: '知识掌握' },
    { dimension: 'troubleshooting', key: 'troubleshootingScore', label: '排障能力' },
    { dimension: 'autonomy', key: 'autonomyScore', label: '自主探索' },
    { dimension: 'ai_collaboration', key: 'aiCollaborationScore', label: 'AI 协同' },
    { dimension: 'engagement', key: 'engagementScore', label: '学习投入' },
  ] as const

  if (!students.value.length) return []

  return dimensions
    .map((dimension) => {
      const scores = students.value.map((student) => Number(student[dimension.key] || 0))
      const average = scores.reduce((sum, score) => sum + score, 0) / scores.length
      return {
        dimension: dimension.dimension,
        label: dimension.label,
        averageScore: Number(average.toFixed(1)),
        lowCount: scores.filter((score) => score < 70).length,
      }
    })
    .sort((a, b) => a.averageScore - b.averageScore)
})
function formatScore(value: number | string | null | undefined) {
  const numeric = Number(value || 0)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : '0.0'
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '暂无记录'
}

// 之前用的是 image()，那个拼的是 user-service 的 /images/view/，
// 而头像实际在 image-service 的 /api/images/files/ 下，一直是裂图。
function studentAvatar(student: TeacherClassStudentDto) {
  return avatarUrl(student.avatarUrl)
}

function priorityLabel(value?: string | null) {
  if (value === 'high') return '优先安排'
  if (value === 'medium') return '持续跟进'
  if (value === 'low') return '观察维护'
  return '教学建议'
}

function buildLocalClassFallback(): TeacherClassAiAnalysisDto {
  const weakItems = weakDimensions.value.filter((item) => item.lowCount > 0).slice(0, 3)
  const sourceItems = weakItems.length ? weakItems : weakDimensions.value.slice(0, 1)
  return {
    scope: 'class',
    generatedBy: 'rule_fallback',
    fallbackUsed: true,
    generatedAt: new Date().toISOString(),
    overallComment: 'AI 班级分析暂不可用，已展示系统规则建议。',
    suggestions: sourceItems.map((item) => ({
      dimension: item.dimension,
      label: item.label,
      averageScore: item.averageScore,
      affectedStudentCount: item.lowCount,
      evidence: `${item.label}班级均分 ${formatScore(item.averageScore)} 分，${item.lowCount} 名学生低于 70 分。`,
      inClassAction: `建议教师安排${item.label}专项讲评，结合示范流程和随堂练习检查全班掌握情况。`,
      afterClassFollowUp: `建议课后对${item.label}低于 70 分的学生布置短复盘，收集关键步骤、错误原因和下一次改进点。`,
      priority: item.averageScore < 50 || item.lowCount >= 3 ? 'high' : 'medium',
    })),
  }
}

async function fetchClasses() {
  loading.value = true
  error.value = null
  try {
    const response = await getTeacherClasses()
    classes.value = response.items || []
    if (!selectedClassId.value && classes.value.length) {
      selectedClassId.value = classes.value[0].classId
      await fetchStudents(classes.value[0].classId)
    }
  } catch (err) {
    error.value = getApiErrorMessage(err, '班级数据加载失败，请重新加载。')
  } finally {
    loading.value = false
  }
}

async function fetchStudents(classId: number) {
  const requestVersion = ++classRequestVersion
  selectedClassId.value = classId
  studentsLoading.value = true
  studentsError.value = null
  classAiError.value = null
  classAiAnalysis.value = null
  classAiLoading.value = false
  students.value = []
  try {
    const response = await getTeacherClassStudents(classId)
    if (requestVersion !== classRequestVersion || selectedClassId.value !== classId) return
    students.value = response.items || []
    void fetchClassAiAnalysis(classId, requestVersion)
  } catch (err) {
    if (requestVersion !== classRequestVersion || selectedClassId.value !== classId) return
    studentsError.value = getApiErrorMessage(err, '班级学生数据加载失败，请重新加载。')
  } finally {
    if (requestVersion === classRequestVersion && selectedClassId.value === classId) {
      studentsLoading.value = false
    }
  }
}

async function fetchClassAiAnalysis(classId: number, requestVersion: number) {
  if (requestVersion !== classRequestVersion || selectedClassId.value !== classId) return
  classAiLoading.value = true
  classAiError.value = null
  try {
    const response = await getTeacherClassAiAnalysis(classId)
    if (requestVersion !== classRequestVersion || selectedClassId.value !== classId) return
    classAiAnalysis.value = response
  } catch (err) {
    if (requestVersion !== classRequestVersion || selectedClassId.value !== classId) return
    classAiError.value = getApiErrorMessage(err, 'AI 班级分析暂不可用，已展示系统规则建议。')
    classAiAnalysis.value = buildLocalClassFallback()
  } finally {
    if (requestVersion === classRequestVersion && selectedClassId.value === classId) {
      classAiLoading.value = false
    }
  }
}

function openStudentProfile(studentId: number) {
  router.push(`/admin/student-profile/${studentId}`)
}

onMounted(() => {
  void fetchClasses()
})
</script>

<template>
  <div class="h-full overflow-y-auto bg-base-100 p-6">
    <div class="mb-6 flex flex-col gap-2">
      <h1 class="text-2xl font-bold">班级管理与学生画像</h1>
      <p class="text-sm text-base-content/60">班级列表、学生画像摘要、训练情况和薄弱维度均来自真实后端数据</p>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ error }}</span>
      <button class="btn btn-sm" @click="fetchClasses">重新加载</button>
    </div>

    <div v-else-if="!classes.length" class="rounded-lg border border-base-200 p-10 text-center text-base-content/60 shadow-sm">
      暂无班级数据
    </div>

    <template v-else>
      <div class="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <button
          v-for="cls in classes"
          :key="cls.classId"
          class="rounded-lg border bg-base-100 p-5 text-left shadow-sm transition hover:border-primary"
          :class="selectedClassId === cls.classId ? 'border-primary ring-1 ring-primary/30' : 'border-base-200'"
          @click="fetchStudents(cls.classId)"
        >
          <div class="mb-4 flex items-start justify-between gap-3">
            <div>
              <div class="text-lg font-bold">{{ cls.className }}</div>
              <div class="mt-1 text-xs text-base-content/50">最近活跃：{{ formatTime(cls.lastActiveAt) }}</div>
            </div>
            <span class="badge badge-primary">{{ cls.activeStudentCount }}/{{ cls.studentCount }} 活跃</span>
          </div>
          <div class="grid grid-cols-3 gap-3 text-sm">
            <div class="rounded-md bg-base-200/70 p-3">
              <div class="text-base-content/50">学生数</div>
              <div class="text-lg font-bold">{{ cls.studentCount }}</div>
            </div>
            <div class="rounded-md bg-base-200/70 p-3">
              <div class="text-base-content/50">画像均分</div>
              <div class="text-lg font-bold text-primary">{{ formatScore(cls.averageProfileScore) }}</div>
            </div>
            <div class="rounded-md bg-base-200/70 p-3">
              <div class="text-base-content/50">训练均分</div>
              <div class="text-lg font-bold text-secondary">{{ formatScore(cls.averageTrainingScore) }}</div>
            </div>
          </div>
        </button>
      </div>

      <div v-if="selectedClass" class="mb-6 rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
        <div class="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-bold">{{ selectedClass.className }} 班级共性关注</h2>
            <p class="text-xs text-base-content/50">基于全班学生最新画像聚合，用于班级层教学安排</p>
          </div>
          <span class="badge badge-outline">{{ students.length }} 名学生</span>
        </div>
        <div v-if="studentsLoading" class="py-8 text-center">
          <span class="loading loading-spinner text-primary"></span>
        </div>
        <div v-else-if="weakDimensions.length" class="grid grid-cols-1 gap-4 md:grid-cols-5">
          <div v-for="item in weakDimensions" :key="item.label" class="rounded-md bg-base-200/60 p-4">
            <div class="mb-2 text-sm text-base-content/60">{{ item.label }}</div>
            <div class="text-2xl font-bold">{{ formatScore(item.averageScore) }}</div>
            <div class="mt-2 text-xs text-base-content/60">{{ item.lowCount }} 人低于 70</div>
          </div>
        </div>
        <div v-else class="py-8 text-center text-base-content/60">暂无学生训练记录</div>
        <div class="mt-5 rounded-md bg-base-200/50 p-4">
          <div class="mb-2 flex items-center justify-between gap-3">
            <div class="font-semibold">AI 班级教学安排建议</div>
            <span v-if="classAiAnalysis?.fallbackUsed || classAiError" class="badge badge-warning badge-sm">系统规则兜底</span>
          </div>
          <div v-if="classAiLoading" class="flex items-center gap-2 py-3 text-sm text-base-content/60">
            <span class="loading loading-spinner loading-xs"></span>
            正在生成班级教学分析
          </div>
          <div v-else-if="classAiAnalysis" class="space-y-3 text-sm">
            <div v-if="classAiAnalysis.fallbackUsed || classAiError" class="rounded-md bg-warning/10 p-3 text-warning-content">
              AI 班级分析暂不可用，已展示系统规则建议。
            </div>
            <p class="text-base-content/70">{{ classAiAnalysis.overallComment }}</p>
            <div v-if="classAiSuggestions.length" class="space-y-3">
              <div v-for="item in classAiSuggestions" :key="`${item.dimension}-${item.label}`" class="rounded-md bg-base-100 p-3">
                <div class="mb-2 flex items-center justify-between gap-3">
                  <div class="font-semibold text-base-content">
                    {{ item.label }}
                    <span class="text-xs font-normal text-base-content/55">
                      均分 {{ formatScore(item.averageScore) }} · 影响 {{ item.affectedStudentCount }} 人
                    </span>
                  </div>
                  <span class="badge badge-outline badge-sm">{{ priorityLabel(item.priority) }}</span>
                </div>
                <p class="text-base-content/60">{{ item.evidence }}</p>
                <p class="mt-2 text-primary">课上：{{ item.inClassAction }}</p>
                <p class="mt-1 text-secondary">课后：{{ item.afterClassFollowUp }}</p>
              </div>
            </div>
            <div v-else class="text-base-content/60">暂无班级教学安排建议</div>
          </div>
          <div v-else class="text-sm text-base-content/60">暂无班级教学安排建议</div>
        </div>
      </div>

      <div class="rounded-lg border border-base-200 bg-base-100 p-5 shadow-sm">
        <h2 class="mb-4 text-lg font-bold">学生画像列表</h2>
        <div v-if="studentsLoading" class="py-10 text-center">
          <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
        <div v-else-if="studentsError" class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
          <span>{{ studentsError }}</span>
          <button v-if="selectedClassId" class="btn btn-sm" @click="fetchStudents(selectedClassId)">重新加载</button>
        </div>
        <div v-else-if="!students.length" class="py-10 text-center text-base-content/60">暂无学生训练记录</div>
        <div v-else class="overflow-x-auto">
          <table class="table">
            <thead>
              <tr>
                <th>学生</th>
                <th>总体分</th>
                <th>知识</th>
                <th>排障</th>
                <th>自主</th>
                <th>AI 协同</th>
                <th>投入</th>
                <th>训练次数</th>
                <th>平均训练分</th>
                <th>最近活跃</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="student in students" :key="student.userId">
                <td>
                  <div class="flex items-center gap-3">
                    <div class="avatar">
                      <div class="h-10 w-10 rounded-full bg-base-200">
                        <img
                          v-if="studentAvatar(student)"
                          :src="studentAvatar(student)"
                          :alt="`${student.nickname || student.username} 的头像`"
                          class="h-full w-full object-cover"
                        >
                        <div v-else class="flex h-full w-full items-center justify-center">
                          <i class="fas fa-user text-base-content/40"></i>
                        </div>
                      </div>
                    </div>
                    <div>
                      <div class="font-semibold">{{ student.nickname || student.username }}</div>
                      <div class="text-xs text-base-content/50">{{ student.username }}</div>
                    </div>
                  </div>
                </td>
                <td class="font-bold text-primary">{{ formatScore(student.overallScore) }}</td>
                <td>{{ formatScore(student.knowledgeMasteryScore) }}</td>
                <td>{{ formatScore(student.troubleshootingScore) }}</td>
                <td>{{ formatScore(student.autonomyScore) }}</td>
                <td>{{ formatScore(student.aiCollaborationScore) }}</td>
                <td>{{ formatScore(student.engagementScore) }}</td>
                <td>{{ student.generatedQuestionAttemptCount || student.trainingQuestionSubmitCount }}</td>
                <td>{{ formatScore(student.averageTrainingScore) }}</td>
                <td>{{ formatTime(student.lastActiveAt) }}</td>
                <td>
                  <button class="btn btn-primary btn-xs" @click="openStudentProfile(student.userId)">查看详情</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
