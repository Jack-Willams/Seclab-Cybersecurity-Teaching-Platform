<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  getApiErrorMessage,
  getTeachingClassKnowledgeRiskDetail,
  type KnowledgeRiskDetailDto,
  type KnowledgeRiskItemDto,
  type TeachingClassStudentDto,
} from '../../../../api'
import { classifyKnowledgeRisk, formatRiskRatePercent } from '../analysisPresentation'
import KnowledgeAiAnalysisPanel from './KnowledgeAiAnalysisPanel.vue'

const props = withDefaults(defineProps<{
  open: boolean
  classId: number
  courseId: number
  item: KnowledgeRiskItemDto | null
  initialDetail?: KnowledgeRiskDetailDto | null
  allStudents?: TeachingClassStudentDto[]
}>(), { initialDetail: null, allStudents: () => [] })

const emit = defineEmits<{
  close: []
  issued: []
}>()

const detail = ref<KnowledgeRiskDetailDto | null>(props.initialDetail)
const loading = ref(false)
const error = ref('')
const studentSearch = ref('')
const closeButton = ref<HTMLButtonElement | null>(null)
let mounted = false
let returnFocus: HTMLElement | null = null
const isBrowser = typeof window !== 'undefined'

const presentation = computed(() => classifyKnowledgeRisk(Number((detail.value || props.item)?.incorrectRate || 0)))
const filteredStudents = computed(() => {
  const students = detail.value?.affectedStudents || []
  const keyword = studentSearch.value.trim().toLowerCase()
  if (!keyword) return students
  return students.filter((student) => `${student.studentName || ''} ${student.studentId}`.toLowerCase().includes(keyword))
})

async function loadDetail(page = 1) {
  if (!props.open || !props.item) return
  loading.value = true
  error.value = ''
  try {
    detail.value = await getTeachingClassKnowledgeRiskDetail(
      props.classId,
      props.courseId,
      props.item.knowledgePointId,
      page,
      detail.value?.pagination.size || 20,
    )
  } catch (reason) {
    error.value = getApiErrorMessage(reason, '知识点详情加载失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function close() {
  emit('close')
  void nextTick(() => returnFocus?.focus())
}

function onKeydown(event: KeyboardEvent) {
  if (props.open && event.key === 'Escape') close()
}

watch(
  () => [props.open, props.item?.knowledgePointId, props.courseId] as const,
  ([open], previous) => {
    if (!mounted || !open) return
    if (!previous?.[0]) returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    studentSearch.value = ''
    detail.value = props.initialDetail
    void loadDetail()
    void nextTick(() => closeButton.value?.focus())
  },
)

onMounted(() => {
  mounted = true
  window.addEventListener('keydown', onKeydown)
  if (props.open) {
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    if (!props.initialDetail) void loadDetail()
    void nextTick(() => closeButton.value?.focus())
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body" :disabled="!isBrowser">
    <div v-if="open && item" class="drawer-layer">
      <button class="drawer-backdrop" type="button" aria-label="关闭知识点详情" @click="close"></button>
      <aside class="detail-drawer" role="dialog" aria-modal="true" :aria-labelledby="`knowledge-risk-title-${item.knowledgePointId}`">
        <header class="drawer-head">
          <div>
            <span>知识点详细情况</span>
            <h2 :id="`knowledge-risk-title-${item.knowledgePointId}`">{{ item.knowledgePointName }}</h2>
            <p>{{ item.knowledgeCategory }} · {{ item.courseName }}</p>
          </div>
          <button ref="closeButton" type="button" class="drawer-close" aria-label="关闭知识点详情" @click="close">×</button>
        </header>

        <div v-if="loading && !detail" class="drawer-state">
          <span class="loading loading-spinner loading-md text-primary"></span>正在加载知识点详情…
        </div>
        <!-- error-state 的红色原本来自 teacher-page.css，页面已不再引入该文件，改用 daisyUI 语义色 -->
        <div v-else-if="error && !detail" class="drawer-state text-error">
          {{ error }}<button type="button" class="btn btn-outline btn-sm" @click="loadDetail()">重新加载</button>
        </div>
        <div v-else class="drawer-content">
          <div v-if="error" class="inline-error">{{ error }} <button type="button" class="btn btn-ghost btn-xs" @click="loadDetail()">重试</button></div>
          <section class="metric-grid">
            <div><span>知识点错题率</span><strong :style="{ color: presentation.color }">{{ formatRiskRatePercent((detail || item).incorrectRate) }}%</strong><small>{{ presentation.label }}</small></div>
            <div><span>出错学生</span><strong>{{ (detail || item).incorrectStudentCount }}</strong><small>/ {{ (detail || item).attemptedStudentCount }} 名已作答</small></div>
            <div><span>错误记录</span><strong>{{ (detail || item).incorrectCount }}</strong><small>/ {{ (detail || item).attemptedCount }} 次作答</small></div>
          </section>

          <section class="detail-section">
            <div class="section-title"><h3>大家普遍存在的错误</h3><span>{{ detail?.commonMistakes.length || 0 }} 类</span></div>
            <div v-if="detail?.commonMistakes.length" class="mistake-list">
              <article v-for="mistake in detail.commonMistakes" :key="`${mistake.answer}-${mistake.count}`">
                <p>{{ mistake.answer || '未填写答案' }}</p><span>{{ mistake.studentCount }} 人 · {{ mistake.count }} 次</span>
              </article>
            </div>
            <p v-else class="empty-evidence">当前暂无可归纳的共同错误答案。</p>
          </section>

          <section class="detail-section">
            <div class="section-title"><h3>代表性错误与标准答案</h3><span>{{ detail?.representativeAttempts.length || 0 }} 条</span></div>
            <article v-for="attempt in detail?.representativeAttempts || []" :key="`${attempt.generatedQuestionId}-${attempt.studentId}`" class="attempt-card">
              <header><strong>{{ attempt.title }}</strong><span>{{ attempt.studentName }}</span></header>
              <div class="answer wrong"><span>学生原始作答</span><p>{{ attempt.answer || '未填写' }}</p></div>
              <div class="answer standard"><span>参考答案</span><p>{{ attempt.standardAnswer || '暂无参考答案' }}</p></div>
            </article>
            <p v-if="!detail?.representativeAttempts.length" class="empty-evidence">暂无代表性作答证据。</p>
          </section>

          <section class="detail-section">
            <div class="section-title"><h3>出错学生</h3><span>{{ detail?.pagination.total ?? (detail || item).incorrectStudentCount }} 人</span></div>
            <input v-model="studentSearch" class="student-filter" type="search" placeholder="搜索学生姓名或 ID" />
            <div class="affected-list"><span v-for="student in filteredStudents" :key="student.studentId">{{ student.studentName || `学生 ${student.studentId}` }}</span></div>
            <p v-if="detail && !filteredStudents.length" class="empty-evidence">没有匹配的学生。</p>
            <div v-if="detail && detail.pagination.total > detail.pagination.size" class="pagination">
              <div class="join">
                <button type="button" class="btn join-item btn-xs" :disabled="detail.pagination.page <= 1 || loading" @click="loadDetail(detail.pagination.page - 1)">上一页</button>
                <button type="button" class="btn btn-active join-item btn-xs">第 {{ detail.pagination.page }} 页</button>
                <button type="button" class="btn join-item btn-xs" :disabled="detail.pagination.page * detail.pagination.size >= detail.pagination.total || loading" @click="loadDetail(detail.pagination.page + 1)">下一页</button>
              </div>
            </div>
          </section>

          <KnowledgeAiAnalysisPanel
            :class-id="classId"
            :course-id="courseId"
            :knowledge-point-id="item.knowledgePointId"
            :knowledge-point-name="item.knowledgePointName"
            :affected-students="item.affectedStudents"
            :all-students="allStudents"
            @issued="emit('issued')"
          />
        </div>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.drawer-layer{position:fixed;inset:0;z-index:1200}.drawer-backdrop{position:absolute;inset:0;width:100%;border:0;background:rgba(17,31,49,.36);cursor:pointer}.detail-drawer{position:absolute;inset:0 0 0 auto;width:min(720px,94vw);overflow:auto;background:oklch(var(--b2));box-shadow:-12px 0 38px rgba(27,48,75,.22)}.drawer-head{position:sticky;top:0;z-index:2;display:flex;justify-content:space-between;gap:16px;padding:22px 25px;border-bottom:1px solid oklch(var(--bc) / .12);background:oklch(var(--b1))}.drawer-head span{color:oklch(var(--p));font-size:11px;font-weight:700}.drawer-head h2{margin:5px 0 4px;color:oklch(var(--bc));font-size:20px}.drawer-head p{margin:0;color:oklch(var(--bc) / .6);font-size:11px}.drawer-close{width:34px;height:34px;border:1px solid oklch(var(--bc) / .12);border-radius:50%;background:oklch(var(--b1));color:oklch(var(--bc));font-size:23px;line-height:1;cursor:pointer}.drawer-close:focus-visible{outline:2px solid oklch(var(--p));outline-offset:2px}.drawer-content{display:grid;gap:15px;padding:20px}.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);overflow:hidden;border:1px solid oklch(var(--bc) / .12);border-radius:9px;background:oklch(var(--b1))}.metric-grid div{display:grid;gap:4px;padding:15px;border-right:1px solid oklch(var(--bc) / .12)}.metric-grid div:last-child{border-right:0}.metric-grid span,.metric-grid small{color:oklch(var(--bc) / .6);font-size:10px}.metric-grid strong{color:oklch(var(--bc));font-size:22px}.detail-section{padding:17px;border:1px solid oklch(var(--bc) / .12);border-radius:9px;background:oklch(var(--b1))}.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px}.section-title h3{margin:0;color:oklch(var(--bc));font-size:14px}.section-title span{color:oklch(var(--bc) / .6);font-size:10px}.mistake-list{display:grid;gap:8px}.mistake-list article{display:flex;align-items:flex-start;justify-content:space-between;gap:15px;padding:10px 11px;border-left:3px solid oklch(var(--wa));background:oklch(var(--b2))}.mistake-list p{margin:0;color:oklch(var(--bc));font-size:12px;line-height:1.6}.mistake-list span{color:oklch(var(--wa));font-size:10px;white-space:nowrap}.attempt-card{margin-top:10px;overflow:hidden;border:1px solid oklch(var(--bc) / .12);border-radius:7px}.attempt-card header{display:flex;justify-content:space-between;gap:12px;padding:10px 12px;background:oklch(var(--b2))}.attempt-card header strong{color:oklch(var(--bc));font-size:12px}.attempt-card header span{color:oklch(var(--bc) / .6);font-size:10px}.answer{display:grid;grid-template-columns:90px 1fr;gap:8px;padding:10px 12px;border-top:1px solid oklch(var(--bc) / .12)}.answer span{font-size:10px;font-weight:700}.answer p{margin:0;color:oklch(var(--bc));font-size:11px;line-height:1.6}.answer.wrong span{color:oklch(var(--er))}.answer.standard span{color:oklch(var(--su))}.student-filter{width:100%;height:36px;padding:0 10px;border:1px solid oklch(var(--bc) / .12);border-radius:6px;outline:none}.student-filter:focus{border-color:oklch(var(--p))}.affected-list{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}.affected-list span{padding:6px 9px;border-radius:999px;background:oklch(var(--b2));color:oklch(var(--p));font-size:10px}.pagination{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:13px;color:oklch(var(--bc) / .6);font-size:10px}.pagination button,.inline-error button,.pagination button:disabled{opacity:.45;cursor:not-allowed}.primary-action{position:sticky;bottom:10px;width:100%;padding:12px;border:0;border-radius:7px;background:oklch(var(--p));color:oklch(var(--pc));font-size:13px;font-weight:700;box-shadow:0 7px 18px rgba(37,99,173,.2);cursor:pointer}.empty-evidence{margin:0;color:oklch(var(--bc) / .6);font-size:11px}.drawer-state{display:grid;gap:10px;place-items:center;padding:60px 24px;color:oklch(var(--bc) / .6);font-size:12px}.inline-error{padding:10px;border-radius:6px;background:oklch(var(--b2));color:oklch(var(--er));font-size:11px}@media(max-width:600px){.drawer-head{padding:17px}.drawer-content{padding:12px}.metric-grid{grid-template-columns:1fr}.metric-grid div{border-right:0;border-bottom:1px solid oklch(var(--bc) / .12)}.metric-grid div:last-child{border-bottom:0}.answer{grid-template-columns:1fr}}
</style>
