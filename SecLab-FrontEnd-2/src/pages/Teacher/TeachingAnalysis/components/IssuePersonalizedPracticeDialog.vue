<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createTeachingClassIntervention,
  getApiErrorMessage,
  type KnowledgeExerciseDto,
  type TeachingClassStudentDto,
} from '../../../../api'

const props = defineProps<{
  open: boolean
  classId: number
  courseId: number
  knowledgePointId: number
  knowledgePointName: string
  exercises: readonly KnowledgeExerciseDto[]
  affectedStudents: Array<{ studentId: number; studentName: string }>
  allStudents: TeachingClassStudentDto[]
}>()
const emit = defineEmits<{ close: []; issued: [] }>()

const scope = ref<'affected' | 'all' | 'custom'>('affected')
const customStudentIds = ref<number[]>([])
const title = ref('')
const description = ref('')
const dueAt = ref('')
const submitting = ref(false)
const error = ref('')
const isBrowser = typeof window !== 'undefined'

const approvedExercises = computed(() => props.exercises.filter((item) => item.reviewStatus === 'APPROVED'))
const affectedIds = computed(() => props.affectedStudents.map((item) => Number(item.studentId)).filter(Boolean))
const selectedStudentIds = computed(() => {
  if (scope.value === 'all') return props.allStudents.map((item) => Number(item.studentId)).filter(Boolean)
  if (scope.value === 'custom') return customStudentIds.value
  return affectedIds.value
})

watch(() => props.open, (open) => {
  if (!open) return
  scope.value = 'affected'
  customStudentIds.value = [...affectedIds.value]
  title.value = `${props.knowledgePointName}个性化练习`
  description.value = `针对本实验“${props.knowledgePointName}”知识点的专项练习，请按时完成。`
  error.value = ''
}, { immediate: true })

async function issue() {
  if (!approvedExercises.value.length) {
    error.value = '至少需要一题审核通过的例题。'
    return
  }
  if (!selectedStudentIds.value.length) {
    error.value = '至少选择一名学生。'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await createTeachingClassIntervention(props.classId, {
      title: title.value.trim(),
      actionType: 'TARGETED_PRACTICE',
      studentIds: selectedStudentIds.value,
      courseId: props.courseId,
      knowledgePointId: props.knowledgePointId,
      description: description.value.trim(),
      approvedExerciseIds: approvedExercises.value.map((item) => item.exerciseId),
      dueAt: dueAt.value ? new Date(dueAt.value).toISOString() : null,
    })
    emit('issued')
    emit('close')
  } catch (reason) {
    error.value = getApiErrorMessage(reason, '练习下发失败，请稍后重试。')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body" :disabled="!isBrowser">
    <div v-if="open" class="issue-layer">
      <button type="button" class="issue-backdrop" aria-label="关闭下发练习窗口" @click="emit('close')"></button>
      <section class="issue-dialog" role="dialog" aria-modal="true" aria-labelledby="issue-title">
        <header><h3 id="issue-title">下发个性化练习</h3><button type="button" aria-label="关闭" @click="emit('close')">×</button></header>
        <form @submit.prevent="issue">
          <label>任务名称<input v-model="title" required /></label>
          <label>学生说明<textarea v-model="description" rows="2"></textarea></label>
          <fieldset><legend>下发范围</legend><div class="scope-options"><label><input v-model="scope" type="radio" value="affected" />本知识点出错学生（{{ affectedIds.length }} 人）</label><label><input v-model="scope" type="radio" value="all" />全班学生（{{ allStudents.length }} 人）</label><label><input v-model="scope" type="radio" value="custom" />自定义学生</label></div></fieldset>
          <fieldset v-if="scope === 'custom'"><legend>选择学生（{{ customStudentIds.length }} 人）</legend><div class="student-options"><label v-for="student in allStudents" :key="student.studentId"><input v-model="customStudentIds" type="checkbox" :value="student.studentId" />{{ student.studentName || student.studentNumber }}</label></div></fieldset>
          <label>截止时间<input v-model="dueAt" type="datetime-local" /></label>
          <section class="snapshot-box"><div><strong>将下发的题目</strong><span>{{ approvedExercises.length }} 题</span></div><ul><li v-for="exercise in approvedExercises" :key="exercise.exerciseId">{{ exercise.stem }}</li></ul></section>
          <div v-if="error" class="issue-error">{{ error }}</div>
          <div class="issue-actions">
            <button type="button" class="btn btn-ghost btn-sm" @click="emit('close')">取消</button>
            <button class="btn btn-primary btn-sm" type="submit" :disabled="submitting || !approvedExercises.length">
              <span v-if="submitting" class="loading loading-spinner loading-xs"></span>
              {{ submitting ? '下发中…' : `确认下发给 ${selectedStudentIds.length} 人` }}
            </button>
          </div>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.issue-layer{position:fixed;inset:0;z-index:1300}.issue-backdrop{position:absolute;inset:0;width:100%;border:0;background:rgba(16,30,49,.46)}.issue-dialog{position:absolute;top:50%;left:50%;width:min(620px,92vw);max-height:90vh;overflow:auto;transform:translate(-50%,-50%);border-radius:10px;background:oklch(var(--b1));box-shadow:0 20px 55px rgba(17,37,64,.3)}.issue-dialog>header{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;border-bottom:1px solid oklch(var(--bc) / .12)}.issue-dialog>header span{color:oklch(var(--p));font-size:9px;font-weight:700}.issue-dialog h3{margin:4px 0 0;color:oklch(var(--bc));font-size:17px}.issue-dialog>header button{border:0;background:none;color:oklch(var(--bc) / .6);font-size:22px;cursor:pointer}.issue-dialog form{display:grid;gap:12px;padding:18px 20px}.issue-dialog form>label{display:grid;gap:5px;color:oklch(var(--bc));font-size:10px}.issue-dialog input,.issue-dialog textarea{padding:9px;border:1px solid oklch(var(--bc) / .12);border-radius:6px;font-size:11px}.issue-dialog fieldset{margin:0;padding:11px;border:1px solid oklch(var(--bc) / .12);border-radius:7px}.issue-dialog legend{padding:0 5px;color:oklch(var(--bc));font-size:10px}.scope-options{display:flex;flex-wrap:wrap;gap:14px}.scope-options label,.student-options label{display:flex;align-items:center;gap:5px;color:oklch(var(--bc));font-size:10px}.student-options{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;max-height:130px;overflow:auto}.snapshot-box{padding:12px;border:1px solid oklch(var(--bc) / .12);border-radius:7px;background:oklch(var(--b2))}.snapshot-box>div{display:flex;justify-content:space-between;color:oklch(var(--su));font-size:11px}.snapshot-box ul{margin:8px 0;padding-left:18px;color:oklch(var(--bc));font-size:10px;line-height:1.7}.snapshot-box p{margin:7px 0 0;color:oklch(var(--bc) / .6);font-size:9px}.issue-actions{display:flex;justify-content:flex-end;gap:8px}.issue-error{padding:8px;border-radius:5px;background:oklch(var(--b2));color:oklch(var(--er));font-size:10px}@media(max-width:600px){.student-options{grid-template-columns:repeat(2,1fr)}}
</style>
