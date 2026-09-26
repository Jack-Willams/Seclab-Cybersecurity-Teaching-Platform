<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  getApiErrorMessage,
  getKnowledgePointAiAnalysis,
  startKnowledgePointAiAnalysis,
  type KnowledgeAiAnalysisDto,
  type KnowledgeExerciseDto,
  type TeachingClassStudentDto,
} from '../../../../api'
import IssuePersonalizedPracticeDialog from './IssuePersonalizedPracticeDialog.vue'
import KnowledgeExerciseReview from './KnowledgeExerciseReview.vue'

const props = withDefaults(defineProps<{
  classId: number
  courseId: number
  knowledgePointId: number
  knowledgePointName: string
  affectedStudents: Array<{ studentId: number; studentName: string }>
  allStudents: TeachingClassStudentDto[]
  initialAnalysis?: KnowledgeAiAnalysisDto | null
}>(), { initialAnalysis: null })
const emit = defineEmits<{ issued: [] }>()

const data = ref<KnowledgeAiAnalysisDto | null>(props.initialAnalysis)
const loading = ref(false)
const analysing = ref(false)
const error = ref('')
const issueOpen = ref(false)
let mounted = false

const approvedCount = computed(() => data.value?.exercises.filter((item) => item.reviewStatus === 'APPROVED').length || 0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getKnowledgePointAiAnalysis(props.classId, props.courseId, props.knowledgePointId)
  } catch (reason) {
    error.value = getApiErrorMessage(reason, 'AI 分析记录加载失败。')
  } finally {
    loading.value = false
  }
}

async function analyse() {
  analysing.value = true
  error.value = ''
  try {
    data.value = await startKnowledgePointAiAnalysis(props.classId, props.courseId, props.knowledgePointId)
  } catch (reason) {
    const failureMessage = getApiErrorMessage(reason, 'AI 分析失败，请稍后重试。')
    try {
      data.value = await getKnowledgePointAiAnalysis(props.classId, props.courseId, props.knowledgePointId)
    } catch {
      // 保留当前内存中的最近成功结果；提供方失败时不生成任何替代内容。
    }
    error.value = failureMessage
  } finally {
    analysing.value = false
  }
}

function replaceExercise(updated: KnowledgeExerciseDto) {
  if (!data.value) return
  data.value = { ...data.value, exercises: data.value.exercises.map((item) => item.exerciseId === updated.exerciseId ? updated : item) }
}

watch(() => [props.classId, props.courseId, props.knowledgePointId] as const, () => {
  data.value = props.initialAnalysis
  if (mounted) void load()
})
onMounted(() => {
  mounted = true
  if (!props.initialAnalysis) void load()
})
</script>

<template>
  <section class="ai-panel">
    <header class="ai-head">
      <h3>AI 分析与教师备课建议</h3>
      <button type="button" class="btn btn-primary btn-sm gap-2" :disabled="analysing" @click="analyse">
        <span v-if="analysing" class="loading loading-spinner loading-xs"></span>
        <i v-else class="fas fa-wand-magic-sparkles text-xs"></i>
        {{ analysing ? 'AI 分析中…' : data?.analysis ? '重新分析' : '开始 AI 分析' }}
      </button>
    </header>
    <div v-if="error" class="ai-error">{{ error }}</div>
    <div v-if="loading && !data" class="ai-state">
      <span class="loading loading-spinner loading-md text-primary"></span>正在读取分析记录…
    </div>
    <div v-else-if="!data?.analysis" class="ai-empty">
      <i class="fas fa-robot text-3xl text-base-content/25"></i>
      <strong>暂无本知识点 AI 分析</strong>
    </div>
    <template v-else>
      <section class="conclusion"><span>分析结论</span><p>{{ data.analysis.overallConclusion }}</p></section>
      <div class="advice-grid">
        <section><h4>普遍错误归因</h4><article v-for="item in data.analysis.commonMistakes" :key="item.title"><strong>{{ item.title }}</strong><p>{{ item.reason }}</p></article></section>
        <section><h4>下节课教学建议</h4><article v-for="item in data.analysis.teachingAdvice" :key="item.title"><strong>{{ item.title }}</strong><p>{{ item.action }}</p></article></section>
      </div>
      <section class="exercise-section">
        <header><h4>知识点例题</h4><strong>已审核通过 {{ approvedCount }}/{{ data.exercises.length }}</strong></header>
        <div class="exercise-list"><KnowledgeExerciseReview v-for="exercise in data.exercises" :key="exercise.exerciseId" :class-id="classId" :exercise="exercise" @changed="replaceExercise" /></div>
        <button class="btn btn-primary btn-sm ml-auto mt-3 flex gap-2" type="button" :disabled="approvedCount === 0" @click="issueOpen = true">
          <i class="fas fa-paper-plane text-xs"></i>下发已审核通过的练习
        </button>
      </section>
    </template>
    <IssuePersonalizedPracticeDialog
      :open="issueOpen"
      :class-id="classId"
      :course-id="courseId"
      :knowledge-point-id="knowledgePointId"
      :knowledge-point-name="knowledgePointName"
      :exercises="data?.exercises || []"
      :affected-students="affectedStudents"
      :all-students="allStudents"
      @close="issueOpen = false"
      @issued="emit('issued')"
    />
  </section>
</template>

<style scoped>
.ai-panel{padding:17px;border:1px solid oklch(var(--bc) / .12);border-radius:9px;background:oklch(var(--b2))}.ai-head{display:flex;align-items:center;justify-content:space-between;gap:15px}.ai-head span{color:oklch(var(--p));font-size:9px;font-weight:700}.ai-head h3{margin:4px 0 0;color:oklch(var(--bc));font-size:15px}/* 原来把 .ai-head button 和 .ai-error 并在一条规则里，等于给标题按钮套了错误红；按钮已改用 btn-primary，这里只留错误提示 */
.ai-error{display:grid;gap:3px;margin-top:12px;padding:9px;border-radius:6px;background:oklch(var(--b2));color:oklch(var(--er));font-size:10px}.ai-error small{color:oklch(var(--bc) / .6)}.ai-state,.ai-empty{display:grid;gap:8px;place-items:center;margin-top:13px;padding:26px;border-radius:7px;background:oklch(var(--b1));color:oklch(var(--bc) / .6);font-size:12px}.ai-empty strong{color:oklch(var(--bc));font-size:12px}.ai-empty p{margin:6px auto 0;max-width:470px;line-height:1.65}.conclusion{margin-top:13px;padding:12px;border-left:3px solid oklch(var(--p));background:oklch(var(--b1))}.conclusion span{color:oklch(var(--p));font-size:9px;font-weight:700}.conclusion p{margin:5px 0 0;color:oklch(var(--bc));font-size:11px;line-height:1.7}.advice-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.advice-grid>section{padding:12px;border:1px solid oklch(var(--bc) / .12);border-radius:7px;background:oklch(var(--b1))}.advice-grid h4,.exercise-section h4{margin:0;color:oklch(var(--bc));font-size:12px}.advice-grid article{margin-top:9px}.advice-grid strong{color:oklch(var(--bc));font-size:10px}.advice-grid p{margin:3px 0 0;color:oklch(var(--bc) / .6);font-size:9px;line-height:1.6}.exercise-section{margin-top:13px}.exercise-section>header{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:9px}.exercise-section>header p{margin:4px 0 0;color:oklch(var(--bc) / .6);font-size:9px}.exercise-section>header>strong{color:oklch(var(--su));font-size:10px}.exercise-list{display:grid;gap:9px}@media(max-width:650px){.ai-head,.exercise-section>header{align-items:flex-start;flex-direction:column}.advice-grid{grid-template-columns:1fr}}
</style>
