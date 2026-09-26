<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import {
  getApiErrorMessage,
  regenerateKnowledgeExercise,
  reviewKnowledgeExercise,
  updateKnowledgeExercise,
  type KnowledgeExerciseDto,
  type KnowledgeExerciseReviewStatus,
} from '../../../../api'

const props = defineProps<{ classId: number; exercise: KnowledgeExerciseDto }>()
const emit = defineEmits<{ changed: [exercise: KnowledgeExerciseDto] }>()

const editing = ref(false)
const saving = ref(false)
const regenerating = ref(false)
const reviewing = ref<KnowledgeExerciseReviewStatus | null>(null)
const reviewComment = ref('')
const error = ref('')
const draft = reactive({ stem: '', standardAnswer: '', explanation: '', difficulty: 1, generationRationale: '' })

const roleLabel: Record<string, string> = { FOUNDATION: '基础例题', CONSOLIDATION: '巩固例题', TRANSFER: '迁移例题' }
const statusLabel: Record<string, string> = { PENDING_REVIEW: '待审核', APPROVED: '审核通过', NEEDS_REVISION: '需修改', REJECTED: '已驳回' }

function resetDraft() {
  Object.assign(draft, {
    stem: props.exercise.stem,
    standardAnswer: props.exercise.standardAnswer,
    explanation: props.exercise.explanation,
    difficulty: props.exercise.difficulty,
    generationRationale: props.exercise.generationRationale,
  })
  reviewComment.value = props.exercise.reviewComment || ''
}
watch(() => props.exercise, resetDraft, { immediate: true, deep: true })

async function save() {
  saving.value = true
  error.value = ''
  try {
    const updated = await updateKnowledgeExercise(props.classId, props.exercise.exerciseId, { ...draft })
    emit('changed', updated)
    editing.value = false
  } catch (reason) {
    error.value = getApiErrorMessage(reason, '例题保存失败，请稍后重试。')
  } finally {
    saving.value = false
  }
}

async function review(status: Exclude<KnowledgeExerciseReviewStatus, 'PENDING_REVIEW'>) {
  reviewing.value = status
  error.value = ''
  try {
    emit('changed', await reviewKnowledgeExercise(props.classId, props.exercise.exerciseId, status, reviewComment.value))
  } catch (reason) {
    error.value = getApiErrorMessage(reason, '审核状态保存失败，请稍后重试。')
  } finally {
    reviewing.value = null
  }
}

async function regenerate() {
  regenerating.value = true
  error.value = ''
  try {
    emit('changed', await regenerateKnowledgeExercise(props.classId, props.exercise.exerciseId))
    editing.value = false
  } catch (reason) {
    error.value = getApiErrorMessage(reason, '重新生成失败，请稍后重试。')
  } finally {
    regenerating.value = false
  }
}
</script>

<template>
  <article class="exercise-card" :data-exercise-id="exercise.exerciseId">
    <header>
      <div><span>{{ roleLabel[exercise.role] || exercise.role }}</span><small>难度 {{ exercise.difficulty }}/5 · 版本 {{ exercise.sourceVersion }}</small></div>
      <strong :class="`status-${exercise.reviewStatus.toLowerCase()}`">{{ statusLabel[exercise.reviewStatus] || exercise.reviewStatus }}</strong>
    </header>

    <form v-if="editing" class="exercise-editor" @submit.prevent="save">
      <label>题干<textarea v-model="draft.stem" rows="3" required></textarea></label>
      <label>标准答案<textarea v-model="draft.standardAnswer" rows="3" required></textarea></label>
      <label>解析<textarea v-model="draft.explanation" rows="2"></textarea></label>
      <label>生成目的<input v-model="draft.generationRationale" /></label>
      <label>难度<input v-model.number="draft.difficulty" type="number" min="1" max="5" /></label>
      <div class="editor-actions">
        <button type="button" class="btn btn-ghost btn-xs" @click="editing = false; resetDraft()">取消</button>
        <button class="btn btn-primary btn-xs" type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存修改' }}</button>
      </div>
      <p>修改后需重新审核。</p>
    </form>
    <template v-else>
      <h4>{{ exercise.stem }}</h4>
      <div class="exercise-answer"><span>标准答案</span><p>{{ exercise.standardAnswer }}</p></div>
      <div class="exercise-answer"><span>解析</span><p>{{ exercise.explanation || '暂无解析' }}</p></div>
      <p class="rationale">生成目的：{{ exercise.generationRationale || '未说明' }}</p>
    </template>

    <div v-if="!editing" class="review-box">
      <textarea v-model="reviewComment" rows="2" placeholder="审核意见（选填；标记需修改或驳回时建议填写）"></textarea>
      <div class="review-actions">
        <button type="button" class="btn btn-outline btn-xs" @click="editing = true">编辑</button>
        <button type="button" class="btn btn-outline btn-xs" :disabled="regenerating" @click="regenerate">{{ regenerating ? '生成中…' : '重新生成本题' }}</button>
        <button type="button" class="btn btn-outline btn-warning btn-xs" :disabled="Boolean(reviewing)" @click="review('NEEDS_REVISION')">需修改</button>
        <button type="button" class="btn btn-outline btn-error btn-xs" :disabled="Boolean(reviewing)" @click="review('REJECTED')">驳回</button>
        <button type="button" class="btn btn-success btn-xs" :disabled="Boolean(reviewing)" @click="review('APPROVED')">审核通过</button>
      </div>
    </div>
    <div v-if="error" class="exercise-error">{{ error }}</div>
  </article>
</template>

<style scoped>
.exercise-card{overflow:hidden;border:1px solid oklch(var(--bc) / .12);border-radius:8px;background:oklch(var(--b1))}.exercise-card>header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:11px 13px;background:oklch(var(--b2))}.exercise-card>header div{display:flex;align-items:baseline;gap:9px}.exercise-card>header span{color:oklch(var(--p));font-size:12px;font-weight:750}.exercise-card>header small{color:oklch(var(--bc) / .6);font-size:9px}.exercise-card>header strong{padding:3px 7px;border-radius:999px;font-size:9px}.status-approved{background:oklch(var(--bc) / .12);color:oklch(var(--su))}.status-pending_review{background:oklch(var(--bc) / .12);color:oklch(var(--wa))}.status-needs_revision{background:oklch(var(--bc) / .12);color:oklch(var(--er))}.status-rejected{background:oklch(var(--b2));color:oklch(var(--er))}.exercise-card>h4{margin:14px 14px 8px;color:oklch(var(--bc));font-size:13px;line-height:1.65}.exercise-answer{display:grid;grid-template-columns:70px 1fr;gap:8px;margin:0 14px;padding:8px 0;border-top:1px solid oklch(var(--bc) / .12)}.exercise-answer span{color:oklch(var(--bc) / .6);font-size:10px;font-weight:700}.exercise-answer p,.rationale{margin:0;color:oklch(var(--bc));font-size:10px;line-height:1.6}.rationale{margin:0 14px 12px;color:oklch(var(--bc) / .6)}.review-box{padding:11px 13px;border-top:1px solid oklch(var(--bc) / .12);background:oklch(var(--b1))}.review-box textarea,.exercise-editor textarea,.exercise-editor input{width:100%;padding:8px 9px;border:1px solid oklch(var(--bc) / .12);border-radius:5px;background:oklch(var(--b1));color:oklch(var(--bc));font-size:10px;resize:vertical}.review-actions,.editor-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:7px;margin-top:8px}.exercise-editor{display:grid;gap:8px;padding:13px}.exercise-editor label{display:grid;gap:4px;color:oklch(var(--bc) / .6);font-size:10px}.exercise-editor p{margin:0;color:oklch(var(--wa));font-size:9px}.exercise-error{padding:8px 12px;background:oklch(var(--b2));color:oklch(var(--er));font-size:9px}
</style>
