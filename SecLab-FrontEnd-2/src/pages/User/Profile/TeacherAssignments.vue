<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import {
  getApiErrorMessage,
  getStudentTeacherAssignments,
  startStudentTeacherAssignment,
  type StudentTeacherAssignmentDto,
} from '../../../api'

const props = withDefaults(defineProps<{ userId: number; initialAssignments?: StudentTeacherAssignmentDto[] | null }>(), { initialAssignments: null })
const emit = defineEmits<{ openSession: [trainingSessionId: string] }>()
const assignments = ref<StudentTeacherAssignmentDto[]>(props.initialAssignments ? [...props.initialAssignments] : [])
const loading = ref(false)
const startingId = ref<number | null>(null)
const error = ref('')

async function loadAssignments() {
  if (!props.userId) return
  loading.value = true
  error.value = ''
  try {
    assignments.value = (await getStudentTeacherAssignments(props.userId)).items
  } catch (cause) {
    error.value = getApiErrorMessage(cause, '教师布置任务加载失败。')
  } finally {
    loading.value = false
  }
}

async function startAssignment(item: StudentTeacherAssignmentDto) {
  if (item.trainingSessionId) {
    emit('openSession', item.trainingSessionId)
    return
  }
  startingId.value = item.interventionId
  error.value = ''
  try {
    const result = await startStudentTeacherAssignment(props.userId, item.interventionId)
    await loadAssignments()
    if (result.trainingSessionId) emit('openSession', result.trainingSessionId)
  } catch (cause) {
    error.value = getApiErrorMessage(cause, '专项训练生成失败，请稍后重试。')
  } finally {
    startingId.value = null
  }
}

function statusLabel(item: StudentTeacherAssignmentDto) {
  if (item.assignmentStatus === 'COMPLETED') return '已完成'
  if (item.isOverdue) return '已逾期'
  if (item.assignmentStatus === 'STARTED') return '进行中'
  return '待开始'
}

watch(() => props.userId, () => void loadAssignments())
onMounted(() => { if (!props.initialAssignments) void loadAssignments() })
</script>

<template>
  <!-- 表头/圆角/描边跟个人中心的 .panel 对齐，避免这一块看起来像另一个应用 -->
  <section class="overflow-hidden rounded-[18px] border border-base-content/10 bg-base-100">
    <div class="flex flex-wrap items-start justify-between gap-4 border-b border-base-content/10 px-6 pb-[1.125rem] pt-[1.375rem]">
      <div>
        <span class="block text-[0.6875rem] font-bold tracking-[0.14em] text-base-content/45">课堂任务</span>
        <h2 class="mt-1 text-[1.375rem] font-bold tracking-[-0.02em] text-base-content">老师布置的个性化练习</h2>
      </div>
      <span v-if="assignments.length" class="shrink-0 pt-1.5 text-xs tabular-nums text-base-content/60">
        {{ assignments.length }} 项
      </span>
    </div>
    <div class="flex flex-col gap-4 p-6">
      <div v-if="error" class="alert alert-error py-3 text-sm">{{ error }}</div>
      <div v-if="loading" class="text-sm text-base-content/50">正在读取教师布置任务…</div>
      <div v-else class="grid gap-3 lg:grid-cols-2">
        <!-- bg-base-50 原来是个不存在的 token（daisyUI 只有 base-100/200/300），一直没生效 -->
        <article v-for="item in assignments" :key="item.interventionId" class="rounded-2xl border border-base-content/10 bg-base-200/40 p-4">
          <div class="flex items-start justify-between gap-3">
            <div><div class="text-xs text-base-content/50">{{ item.className }} · {{ item.teacherName || '任课教师' }}</div><h3 class="mt-1 font-semibold text-base-content">{{ item.title }}</h3></div>
            <span class="badge badge-sm" :class="item.assignmentStatus === 'COMPLETED' ? 'badge-success' : item.isOverdue ? 'badge-error' : item.assignmentStatus === 'STARTED' ? 'badge-info' : 'badge-warning'">{{ statusLabel(item) }}</span>
          </div>
          <p class="mt-3 text-sm leading-6 text-base-content/65">{{ item.description || `围绕${item.knowledgePointName || '当前薄弱知识点'}完成专项训练。` }}</p>
          <div class="mt-3 flex flex-wrap gap-2 text-xs text-base-content/50"><span v-if="item.courseName" class="badge badge-ghost badge-sm">实验：{{ item.courseName }}</span><span v-if="item.knowledgePointName" class="badge badge-outline badge-sm">知识点：{{ item.knowledgePointName }}</span></div>
          <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-base-content/55"><span>{{ item.questionCount }} 题</span><span>预计 {{ item.estimatedMinutes }} 分钟</span><span :class="{ 'text-error font-medium': item.isOverdue }">截止 {{ new Date(item.dueAt).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span></div>
          <div v-if="item.resultSummary" class="mt-3 rounded-lg bg-success/10 px-3 py-2 text-xs text-success"><strong>作答结果</strong><span class="ml-3">完成 {{ item.resultSummary.attemptCount }} 次 · 答对 {{ item.resultSummary.correctCount }} 次 · 平均 {{ item.resultSummary.averageScore }} 分</span></div>
          <button class="btn btn-primary btn-sm mt-4" :disabled="startingId === item.interventionId" @click="startAssignment(item)">{{ startingId === item.interventionId ? '正在准备…' : item.assignmentStatus === 'COMPLETED' ? '查看作答结果' : item.trainingSessionId ? '继续练习' : '开始练习' }}</button>
        </article>
        <div v-if="!assignments.length" class="rounded-2xl border border-dashed border-base-content/20 bg-base-200/30 p-9 text-center lg:col-span-2">
          <i class="fas fa-chalkboard-user text-2xl text-base-content/25"></i>
          <div class="mt-3 text-sm font-semibold text-base-content/75">暂无个性化练习</div>
          <p class="mt-1 text-[0.8125rem] text-base-content/50">老师在班级里布置练习后，会出现在这里并可直接开始作答。</p>
        </div>
      </div>
    </div>
  </section>
</template>
