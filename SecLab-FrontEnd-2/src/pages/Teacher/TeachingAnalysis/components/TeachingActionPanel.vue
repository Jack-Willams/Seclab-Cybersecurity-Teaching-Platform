<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createTeachingClassIntervention,
  getApiErrorMessage,
  refreshTeachingClassIntervention,
  type KnowledgeRiskItemDto,
  type TeacherInterventionActionType,
  type TeacherInterventionDto,
  type TeachingClassStudentDto,
} from '../../../../api'

const props = defineProps<{
  classId: number
  students: TeachingClassStudentDto[]
  selectedRisk: KnowledgeRiskItemDto | null
  interventions: TeacherInterventionDto[]
}>()
const emit = defineEmits<{ changed: [] }>()

const actionType = ref<TeacherInterventionActionType>('FOCUS_GROUP')
const title = ref('')
const description = ref('')
const selectedStudentIds = ref<number[]>([])
const creating = ref(false)
const refreshingId = ref<number | null>(null)
const message = ref('')
const error = ref('')

watch(() => props.selectedRisk, (risk) => {
  if (!risk) return
  title.value = `${risk.knowledgePointName}专项辅导`
  description.value = `${risk.incorrectStudentCount}名学生在${risk.knowledgePointName}上出现错误，安排专项练习并在一周后复盘。`
  selectedStudentIds.value = risk.affectedStudents.map((item) => Number(item.studentId)).filter(Boolean)
}, { immediate: true })

const selectedCount = computed(() => selectedStudentIds.value.length)

async function createAction() {
  if (!title.value.trim() || !selectedStudentIds.value.length) {
    error.value = '请填写行动名称并至少选择一名学生。'
    return
  }
  creating.value = true
  error.value = ''
  message.value = ''
  try {
    await createTeachingClassIntervention(props.classId, {
      title: title.value.trim(),
      actionType: actionType.value,
      studentIds: selectedStudentIds.value,
      knowledgePointId: props.selectedRisk?.knowledgePointId,
      description: description.value.trim(),
      questionIds: props.selectedRisk?.representativeQuestions.map((item) => item.generatedQuestionId) || [],
    })
    message.value = '教学行动已创建。'
    emit('changed')
  } catch (cause) {
    error.value = getApiErrorMessage(cause, '教学行动创建失败，请稍后重试。')
  } finally {
    creating.value = false
  }
}

async function refreshAction(item: TeacherInterventionDto) {
  refreshingId.value = item.interventionId
  error.value = ''
  try {
    await refreshTeachingClassIntervention(props.classId, item.interventionId)
    message.value = '已更新训练完成情况和干预前后变化。'
    emit('changed')
  } catch (cause) {
    error.value = getApiErrorMessage(cause, '教学行动进度更新失败。')
  } finally {
    refreshingId.value = null
  }
}
</script>

<template>
  <section class="action-block">
    <div class="section-heading"><h2>教学行动</h2></div>
    <div class="action-layout">
      <form class="action-form" @submit.prevent="createAction">
        <label>行动类型<select v-model="actionType"><option value="FOCUS_GROUP">创建重点辅导小组</option><option value="LESSON_EXAMPLE">加入下节课典型案例</option></select></label>
        <label>行动名称<input v-model="title" placeholder="例如：SQL盲注专项辅导" /></label>
        <label>教学说明<textarea v-model="description" rows="3" placeholder="说明需要关注的问题和预期结果"></textarea></label>
        <fieldset><legend>参与学生（已选 {{ selectedCount }} 人）</legend><div class="student-checks"><label v-for="student in students" :key="student.studentId"><input v-model="selectedStudentIds" type="checkbox" :value="student.studentId" /><span>{{ student.studentName || student.studentNumber }}</span></label></div></fieldset>
        <div v-if="error" class="form-message error">{{ error }}</div><div v-if="message" class="form-message success">{{ message }}</div>
        <!-- primary-button 的配色原本来自 teacher-page.css，页面已不再引入该文件，改用 daisyUI 的 btn -->
        <button class="btn btn-primary btn-sm justify-self-start" type="submit" :disabled="creating">
          <span v-if="creating" class="loading loading-spinner loading-xs"></span>{{ creating ? '正在创建…' : '创建教学行动' }}
        </button>
      </form>
      <div class="action-history">
        <h3>行动追踪</h3>
        <article v-for="item in interventions" :key="item.interventionId">
          <div><strong>{{ item.title }}</strong><span>{{ item.status === 'ACTIVE' ? '进行中' : item.status === 'COMPLETED' ? '已完成' : '已取消' }}</span></div>
          <p>{{ item.description || '未填写教学说明' }}</p>
          <div class="progress-row"><span>{{ item.progress.completedCount }}/{{ item.progress.studentCount }} 人完成</span><progress :value="item.progress.completionRate" max="1"></progress><button type="button" class="btn btn-ghost btn-xs" :disabled="refreshingId === item.interventionId" @click="refreshAction(item)">{{ refreshingId === item.interventionId ? '更新中…' : '更新对照' }}</button></div>
          <div v-if="item.students.length" class="student-results">
            <div v-for="student in item.students" :key="student.studentId"><span>{{ student.studentName || student.studentNumber || `学生 ${student.studentId}` }}</span><strong>{{ student.assignmentStatus === 'COMPLETED' ? '已完成' : student.assignmentStatus === 'STARTED' ? '进行中' : '待开始' }}</strong><small v-if="student.resultSummary">答对 {{ student.resultSummary.correctCount }}/{{ student.resultSummary.attemptCount }} · 平均 {{ student.resultSummary.averageScore }} 分</small></div>
          </div>
          <small>对照时间：{{ new Date(item.dueAt).toLocaleDateString('zh-CN') }}</small>
        </article>
        <div v-if="!interventions.length" class="empty-inline">暂无教学行动</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.section-heading{margin-bottom:14px}h2,h3{margin:0;color:oklch(var(--bc));font-size:16px}.section-heading p{margin:5px 0 0;color:oklch(var(--bc) / .6);font-size:12px}.action-layout{display:grid;grid-template-columns:minmax(320px,.9fr) minmax(360px,1.1fr);gap:16px}.action-form,.action-history{padding:16px;border:1px solid oklch(var(--bc) / .12);border-radius:8px;background:oklch(var(--b1))}.action-form{display:grid;gap:12px}.action-form>label{display:grid;gap:5px;color:oklch(var(--bc));font-size:11px}.action-form input,.action-form select,.action-form textarea{width:100%;padding:9px 10px;border:1px solid oklch(var(--bc) / .12);border-radius:6px;background:oklch(var(--b1));color:oklch(var(--bc));font-size:12px}.action-form textarea{resize:vertical}.action-form fieldset{margin:0;padding:10px;border:1px solid oklch(var(--bc) / .12);border-radius:6px}.action-form legend{padding:0 5px;color:oklch(var(--bc));font-size:11px}.student-checks{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;max-height:128px;overflow:auto}.student-checks label{display:flex;align-items:center;gap:5px;color:oklch(var(--bc));font-size:10px}.student-checks input{width:auto}.action-history{display:grid;align-content:start;gap:10px}.action-history>h3{margin-bottom:2px}.action-history article{padding:12px;border:1px solid oklch(var(--bc) / .12);border-radius:7px;background:oklch(var(--b1))}.action-history article>div:first-child{display:flex;justify-content:space-between;gap:10px}.action-history strong{color:oklch(var(--bc));font-size:12px}.action-history article>div:first-child span{padding:2px 6px;border-radius:999px;background:oklch(var(--b2));color:oklch(var(--p));font-size:9px}.action-history p{margin:6px 0;color:oklch(var(--bc) / .6);font-size:10px;line-height:1.5}.action-history small{display:block;margin-top:7px;color:oklch(var(--bc) / .6);font-size:9px}.progress-row{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px;color:oklch(var(--bc) / .6);font-size:10px}.progress-row progress{width:100%;height:6px}.student-results{display:grid;gap:5px;margin-top:9px}.student-results>div{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;align-items:center;padding:7px 8px;border-radius:5px;background:oklch(var(--b2))}.student-results span{color:oklch(var(--bc));font-size:9px}.student-results strong{color:oklch(var(--su));font-size:9px}.student-results small{margin:0!important;color:oklch(var(--bc) / .6)!important;font-size:9px!important}.form-message{padding:8px;border-radius:5px;font-size:10px}.form-message.error{background:oklch(var(--b2));color:oklch(var(--er))}.form-message.success{background:oklch(var(--bc) / .12);color:oklch(var(--su))}.empty-inline{padding:28px;color:oklch(var(--bc) / .6);font-size:11px;text-align:center}
@media(max-width:1000px){.action-layout{grid-template-columns:1fr}}@media(max-width:650px){.student-checks{grid-template-columns:repeat(2,1fr)}}
</style>
