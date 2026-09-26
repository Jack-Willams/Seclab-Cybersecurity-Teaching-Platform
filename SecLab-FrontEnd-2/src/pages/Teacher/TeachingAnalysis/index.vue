<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getAiAnalysisHealth,
  getApiErrorMessage,
  getGeneratedQuestionSummary,
  getTeachingClassAnalysis,
  getTeachingClassInterventions,
  getTeachingClasses,
  getTeachingClassExperimentRiskMap,
  getTeachingClassStudentAnalysis,
  getTeachingClassStudentCapabilityEvidence,
  getTeachingClassStudentCapabilityGrowth,
  getTeachingClassStudentLearningReplay,
  getTeachingClassStudentProfile,
  getTeachingClassStudents,
  getTeachingClassCourses,
  getTeacherClassCourseQuestions,
  getTeacherStudentCourseQuestions,
  getTeacherCourseAnalysis,
  rebuildTeachingClassProfiles,
  startTeachingClassAnalysis,
  startTeachingClassStudentAnalysis,
  startTeacherCourseAnalysis,
  type AiAnalysisHealthDto,
  type CapabilityGrowthResponseDto,
  type CapabilityEvidenceResponseDto,
  type KnowledgeRiskItemDto,
  type LearningReplayResponseDto,
  type TeacherGeneratedQuestionSummary,
  type TeacherInterventionDto,
  type TeacherStudentProfileResponseDto,
  type TeachingClassAnalysisDto,
  type TeachingClassDto,
  type TeachingClassStudentDto,
  type TeachingStudentAnalysisDto,
  type TeachingClassCourseDto,
  type TeacherCourseQuestionsDto,
  type TeacherCourseAnalysisDto,
} from '../../../api'
import CapabilityEvidencePanel from './components/CapabilityEvidencePanel.vue'
import CapabilityGrowthPanel from '../../../components/CapabilityGrowthPanel.vue'
import KnowledgeRiskPieChart from './components/KnowledgeRiskPieChart.vue'
import KnowledgeRiskDetailDrawer from './components/KnowledgeRiskDetailDrawer.vue'
import LearningReplayTimeline from './components/LearningReplayTimeline.vue'
import TeachingActionPanel from './components/TeachingActionPanel.vue'
import CourseQuestionRecords from './components/CourseQuestionRecords.vue'
import CourseAnalysisPanel from './components/CourseAnalysisPanel.vue'
import { findMatchingRiskItem, getAnalysisRefreshPresentation, getRiskPresentation } from './analysisPresentation'
import '../teacher-page.css'

const route = useRoute()
const router = useRouter()
const classes = ref<TeachingClassDto[]>([])
const selectedClassId = ref<number | null>(null)
const activeTab = ref<'class' | 'student'>('class')
const students = ref<TeachingClassStudentDto[]>([])
const selectedStudentId = ref<number | null>(null)
const courses = ref<TeachingClassCourseDto[]>([])
const selectedCourseId = ref<number | null>(null)
const studentSearch = ref('')
const questionSummary = ref<TeacherGeneratedQuestionSummary | null>(null)
const classAnalysis = ref<TeachingClassAnalysisDto | null>(null)
const studentProfile = ref<TeacherStudentProfileResponseDto | null>(null)
const studentAnalysis = ref<TeachingStudentAnalysisDto | null>(null)
const capabilityEvidence = ref<CapabilityEvidenceResponseDto | null>(null)
const capabilityGrowth = ref<CapabilityGrowthResponseDto | null>(null)
const capabilityGrowthError = ref('')
const learningReplay = ref<LearningReplayResponseDto | null>(null)
const riskItems = ref<KnowledgeRiskItemDto[]>([])
const selectedRisk = ref<KnowledgeRiskItemDto | null>(null)
const riskDrawerOpen = ref(false)
const interventions = ref<TeacherInterventionDto[]>([])
const aiHealth = ref<AiAnalysisHealthDto | null>(null)
const classCourseQuestions = ref<TeacherCourseQuestionsDto | null>(null)
const studentCourseQuestions = ref<TeacherCourseQuestionsDto | null>(null)
const classCourseAnalysis = ref<TeacherCourseAnalysisDto | null>(null)
const studentCourseAnalysis = ref<TeacherCourseAnalysisDto | null>(null)
const courseDataLoading = ref(false)
const classCourseAnalysing = ref(false)
const studentCourseAnalysing = ref(false)
const courseError = ref('')
const loading = ref(true)
const classDataLoading = ref(false)
const studentDataLoading = ref(false)
const classAnalysing = ref(false)
const studentAnalysing = ref(false)
const rebuildingProfiles = ref(false)
const rebuildMessage = ref('')
const pageError = ref('')
const classError = ref('')
const studentError = ref('')
const classAnalysisNotice = ref<{ tone: 'warning' | 'danger'; message: string } | null>(null)
const expandedProblemIndex = ref<number | null>(null)

const selectedClass = computed(() => classes.value.find((item) => item.teachingClassId === selectedClassId.value) || null)
const selectedStudent = computed(() => students.value.find((item) => item.studentId === selectedStudentId.value) || null)
const selectedCourse = computed(() => courses.value.find((item) => item.courseId === selectedCourseId.value) || null)
const filteredStudents = computed(() => {
  const keyword = studentSearch.value.trim().toLowerCase()
  if (!keyword) return students.value
  return students.value.filter((item) => [item.studentName, item.studentNumber, item.administrativeClass]
    .some((value) => String(value || '').toLowerCase().includes(keyword)))
})
const classProblems = computed(() => classAnalysis.value?.analysis?.commonProblems || [])

/**
 * 顶部仪表条的三个读数。
 * 错题率不是新接口，是拿已有的「最终错题 / 本实验题目」现算的 —— 有了这个比值，
 * 「29」才有参照系：29/143 和 29/40 是完全不同的两件事，只给绝对值教师读不出轻重。
 */
const consoleMetrics = computed(() => {
  const summary = classCourseQuestions.value?.summary
  const questionCount = summary?.questionCount ?? 0
  const incorrect = summary?.incorrectQuestionCount ?? 0
  const ratio = questionCount > 0 ? incorrect / questionCount : 0
  return {
    studentCount: summary?.studentCount ?? 0,
    questionCount,
    incorrect,
    ratio,
    percent: Math.round(ratio * 100),
    /** 错题率决定读数的色调：三档和知识点风险的语义保持一致 */
    tone: ratio >= 0.4 ? 'danger' : ratio >= 0.2 ? 'warning' : 'calm',
  }
})
const generatedQuestionCount = computed(() => questionSummary.value?.items.reduce((total, item) => total + item.generatedQuestionCount, 0) || 0)
const incorrectQuestionCount = computed(() => questionSummary.value?.items.reduce((total, item) => total + item.incorrectCount, 0) || 0)
const scoreCards = computed(() => [
  ['综合', studentProfile.value?.latestProfile?.overall_score],
  ['知识掌握', studentProfile.value?.latestProfile?.knowledge_mastery_score],
  ['排障能力', studentProfile.value?.latestProfile?.troubleshooting_score],
  ['自主学习', studentProfile.value?.latestProfile?.autonomy_score],
  ['AI 协同', studentProfile.value?.latestProfile?.ai_collaboration_score],
  ['学习投入', studentProfile.value?.latestProfile?.engagement_score],
] as const)

const formatDateTime = (value?: string | null) => value
  ? new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
  : '暂无记录'
const formatScore = (value?: number | null) => typeof value === 'number' ? value.toFixed(1) : '—'

async function loadClasses() {
  loading.value = true
  pageError.value = ''
  // AI 健康探测会向模型服务发一次真实请求（实测 1.9~2.0 秒），但它只决定顶部那条提示条
  // 显不显示。原先和班级列表一起 await，整页就白等这 2 秒；改成不阻塞，探完再补上提示条。
  void getAiAnalysisHealth()
    .then((result) => { aiHealth.value = result })
    .catch(() => { aiHealth.value = null })
  try {
    classes.value = (await getTeachingClasses()).filter((item) => item.status !== 'ARCHIVED')
    const queryId = Number(route.query.classId)
    const initialId = Number.isFinite(queryId) && classes.value.some((item) => item.teachingClassId === queryId)
      ? queryId : classes.value[0]?.teachingClassId
    selectedClassId.value = initialId || null
  } catch (error) {
    pageError.value = getApiErrorMessage(error, '教学班加载失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

async function loadInterventions() {
  if (!selectedClassId.value) return
  try {
    interventions.value = (await getTeachingClassInterventions(selectedClassId.value)).items
  } catch (error) {
    classError.value ||= getApiErrorMessage(error, '教学行动加载失败。')
  }
}

async function loadClassData() {
  if (!selectedClassId.value) return
  const classId = selectedClassId.value
  classDataLoading.value = true
  classError.value = ''
  classAnalysisNotice.value = null
  rebuildMessage.value = ''
  selectedStudentId.value = null
  studentProfile.value = null
  studentAnalysis.value = null
  capabilityEvidence.value = null
  learningReplay.value = null
  const [studentResult, courseResult, summaryResult, analysisResult, interventionResult] = await Promise.allSettled([
    getTeachingClassStudents(classId),
    getTeachingClassCourses(classId),
    getGeneratedQuestionSummary(classId),
    getTeachingClassAnalysis(classId),
    getTeachingClassInterventions(classId),
  ])
  if (classId !== selectedClassId.value) return
  students.value = studentResult.status === 'fulfilled' ? studentResult.value : []
  courses.value = courseResult.status === 'fulfilled' ? courseResult.value : []
  questionSummary.value = summaryResult.status === 'fulfilled' ? summaryResult.value : null
  classAnalysis.value = analysisResult.status === 'fulfilled' ? analysisResult.value : null
  interventions.value = interventionResult.status === 'fulfilled' ? interventionResult.value.items : []
  riskItems.value = []
  selectedRisk.value = null
  riskDrawerOpen.value = false
  if (studentResult.status === 'rejected') classError.value = getApiErrorMessage(studentResult.reason, '学生名单加载失败。')
  selectedStudentId.value = students.value[0]?.studentId || null
  const queryCourseId = Number(route.query.courseId)
  const nextCourseId = courses.value.some((item) => item.courseId === queryCourseId)
    ? queryCourseId
    : courses.value.find((item) => item.courseId === 1)?.courseId || courses.value[0]?.courseId || null
  const courseChanged = selectedCourseId.value !== nextCourseId
  selectedCourseId.value = nextCourseId
  classDataLoading.value = false
  if (!courseChanged && nextCourseId) void loadCourseData()
  if (!nextCourseId) {
    classCourseQuestions.value = null
    studentCourseQuestions.value = null
    classCourseAnalysis.value = null
    studentCourseAnalysis.value = null
  }
}

async function loadCourseData() {
  if (!selectedClassId.value || !selectedCourseId.value) return
  const classId = selectedClassId.value
  const courseId = selectedCourseId.value
  courseDataLoading.value = true
  courseError.value = ''
  const [questionsResult, analysisResult, riskResult] = await Promise.allSettled([
    getTeacherClassCourseQuestions(classId, courseId),
    getTeacherCourseAnalysis(classId, courseId),
    getTeachingClassExperimentRiskMap(classId, courseId),
  ])
  if (classId !== selectedClassId.value || courseId !== selectedCourseId.value) return
  classCourseQuestions.value = questionsResult.status === 'fulfilled' ? questionsResult.value : null
  classCourseAnalysis.value = analysisResult.status === 'fulfilled' ? analysisResult.value : null
  riskItems.value = riskResult.status === 'fulfilled' ? riskResult.value.items : []
  selectedRisk.value = riskItems.value[0] || null
  riskDrawerOpen.value = false
  if (questionsResult.status === 'rejected') courseError.value = getApiErrorMessage(questionsResult.reason, '实验做题记录加载失败。')
  else if (riskResult.status === 'rejected') courseError.value = getApiErrorMessage(riskResult.reason, '本实验知识点错误分布加载失败。')
  courseDataLoading.value = false
  await loadStudentCourseData()
}

async function loadStudentCourseData() {
  if (!selectedClassId.value || !selectedCourseId.value || !selectedStudentId.value) return
  const classId = selectedClassId.value
  const courseId = selectedCourseId.value
  const studentId = selectedStudentId.value
  const [questionsResult, analysisResult] = await Promise.allSettled([
    getTeacherStudentCourseQuestions(classId, courseId, studentId),
    getTeacherCourseAnalysis(classId, courseId, studentId),
  ])
  if (classId !== selectedClassId.value || courseId !== selectedCourseId.value || studentId !== selectedStudentId.value) return
  studentCourseQuestions.value = questionsResult.status === 'fulfilled' ? questionsResult.value : null
  studentCourseAnalysis.value = analysisResult.status === 'fulfilled' ? analysisResult.value : null
    if (questionsResult.status === 'rejected') studentError.value = getApiErrorMessage(questionsResult.reason, '该学生的实验做题记录加载失败。')
}

async function loadStudentData() {
  if (!selectedClassId.value || !selectedStudentId.value) return
  const classId = selectedClassId.value
  const studentId = selectedStudentId.value
  studentDataLoading.value = true
  studentError.value = ''
  capabilityGrowthError.value = ''
  const [profileResult, analysisResult, growthResult, evidenceResult, replayResult] = await Promise.allSettled([
    getTeachingClassStudentProfile(classId, studentId),
    getTeachingClassStudentAnalysis(classId, studentId),
    getTeachingClassStudentCapabilityGrowth(classId, studentId),
    getTeachingClassStudentCapabilityEvidence(classId, studentId),
    getTeachingClassStudentLearningReplay(classId, studentId),
  ])
  if (classId !== selectedClassId.value || studentId !== selectedStudentId.value) return
  studentProfile.value = profileResult.status === 'fulfilled' ? profileResult.value : null
  studentAnalysis.value = analysisResult.status === 'fulfilled' ? analysisResult.value : null
  capabilityGrowth.value = growthResult.status === 'fulfilled' ? growthResult.value : null
  capabilityEvidence.value = evidenceResult.status === 'fulfilled' ? evidenceResult.value : null
  learningReplay.value = replayResult.status === 'fulfilled' ? replayResult.value : null
  if (profileResult.status === 'rejected') studentError.value = getApiErrorMessage(profileResult.reason, '学生学习数据加载失败。')
  if (growthResult.status === 'rejected') capabilityGrowthError.value = getApiErrorMessage(growthResult.reason, '能力成长数据加载失败。')
  studentDataLoading.value = false
  await loadStudentCourseData()
}

async function runClassCourseAnalysis() {
  if (!selectedClassId.value || !selectedCourseId.value) return
  classCourseAnalysing.value = true
  courseError.value = ''
  try { classCourseAnalysis.value = await startTeacherCourseAnalysis(selectedClassId.value, selectedCourseId.value) }
  catch (error) { courseError.value = getApiErrorMessage(error, '本实验分析失败，请稍后重试。') }
  finally { classCourseAnalysing.value = false }
}

async function runStudentCourseAnalysis() {
  if (!selectedClassId.value || !selectedCourseId.value || !selectedStudentId.value) return
  studentCourseAnalysing.value = true
  studentError.value = ''
  try { studentCourseAnalysis.value = await startTeacherCourseAnalysis(selectedClassId.value, selectedCourseId.value, selectedStudentId.value) }
  catch (error) { studentError.value = getApiErrorMessage(error, '该学生的实验分析失败，请稍后重试。') }
  finally { studentCourseAnalysing.value = false }
}

async function runClassAnalysis() {
  if (!selectedClassId.value) return
  classAnalysing.value = true
  classAnalysisNotice.value = null
  try { classAnalysis.value = await startTeachingClassAnalysis(selectedClassId.value) }
  catch (error) {
    const notice = getAnalysisRefreshPresentation(error, Boolean(classAnalysis.value?.analysis))
    classAnalysisNotice.value = { tone: notice.tone === 'warning' ? 'warning' : 'danger', message: notice.message }
  }
  finally { classAnalysing.value = false }
}

async function runStudentAnalysis() {
  if (!selectedClassId.value || !selectedStudentId.value) return
  studentAnalysing.value = true
  studentError.value = ''
  try { studentAnalysis.value = await startTeachingClassStudentAnalysis(selectedClassId.value, selectedStudentId.value) }
  catch (error) { studentError.value = getApiErrorMessage(error, '学生分析失败，请稍后重试。') }
  finally { studentAnalysing.value = false }
}

async function rebuildProfiles() {
  if (!selectedClassId.value) return
  rebuildingProfiles.value = true
  classError.value = ''
  try {
    const result = await rebuildTeachingClassProfiles(selectedClassId.value)
    rebuildMessage.value = `已更新 ${result.rebuiltCount}/${result.studentCount} 名学生画像${result.failedCount ? `，${result.failedCount} 名待重试` : ''}。`
    await loadStudentData()
  } catch (error) { classError.value = getApiErrorMessage(error, '学生画像更新失败。') }
  finally { rebuildingProfiles.value = false }
}

function selectRisk(item: KnowledgeRiskItemDto) {
  selectedRisk.value = item
  riskDrawerOpen.value = true
}

function toggleProblem(index: number) {
  expandedProblemIndex.value = expandedProblemIndex.value === index ? null : index
}

function problemRisk(item: { title: string; evidence: string; questionIds: string[] }) {
  return findMatchingRiskItem(item, riskItems.value)
}

watch(selectedClassId, (classId) => {
  if (!classId) return
  void router.replace({ query: { ...route.query, classId: String(classId) } })
  void loadClassData()
})
watch(selectedStudentId, () => void loadStudentData())
watch(selectedCourseId, (courseId) => {
  if (!courseId) return
  void router.replace({ query: { ...route.query, classId: String(selectedClassId.value), courseId: String(courseId) } })
  void loadCourseData()
})
onMounted(() => void loadClasses())
</script>

<template>
  <div class="teacher-page analysis-page">
    <header class="page-head">
      <h1>教学分析</h1>
      <select v-model="selectedClassId" class="class-select" aria-label="选择教学班">
        <option v-for="item in classes" :key="item.teachingClassId" :value="item.teachingClassId">{{ item.academicYear }}学年 · 第{{ item.semester }}学期 · {{ item.className }}</option>
      </select>
    </header>

    <div v-if="loading" class="panel loading-state">正在加载教学班…</div>
    <div v-else-if="pageError" class="panel error-state">{{ pageError }} <button class="secondary-button" @click="loadClasses">重新加载</button></div>
    <div v-else-if="!selectedClass" class="panel empty-state"><strong>暂无可分析的教学班</strong></div>

    <template v-else>
      <div v-if="aiHealth && (!aiHealth.configured || !aiHealth.providerReachable)" class="notice warning analysis-notice">AI 分析暂不可用，请稍后重试。</div>
      <!-- 顶部仪表台：原来是「统计条」+「实验切换」两个并列的圆角盒子，读起来是两件事；
           合成一块之后是一条完整的上下文——"哪个班 / 这个实验的规模 / 正在看哪个实验"。 -->
      <section class="analysis-console">
        <div class="console-top">
          <div class="console-identity">
            <span class="console-eyebrow">当前教学班</span>
            <strong class="gradient-text">{{ selectedClass.className }}</strong>
            <small>{{ selectedClass.academicYear }}学年 · 第{{ selectedClass.semester }}学期</small>
          </div>

          <div class="console-metrics">
            <!-- 前两个是中性的规模指标，走渐变；「最终错题」是要行动的信号，
                 保留风险配色（--su/--wa/--er），不能被渐变吃掉语义 -->
            <div class="metric">
              <span>本实验做题学生</span>
              <strong class="gradient-text">{{ consoleMetrics.studentCount }}</strong>
              <em>人</em>
            </div>
            <div class="metric">
              <span>本实验题目</span>
              <strong class="gradient-text">{{ consoleMetrics.questionCount }}</strong>
              <em>道</em>
            </div>
            <div class="metric metric-alert" :class="`tone-${consoleMetrics.tone}`">
              <span>最终错题</span>
              <strong>{{ consoleMetrics.incorrect }}</strong>
              <em>占全部题目 {{ consoleMetrics.percent }}%</em>
              <div
                class="metric-bar"
                role="img"
                :aria-label="`错题占比 ${consoleMetrics.percent}%`"
                :style="{ '--fill': `${Math.min(100, consoleMetrics.percent)}%` }"
              ><i></i></div>
            </div>
          </div>
        </div>

        <div class="console-rail">
          <div class="rail-label">
            <span>分析实验</span>
            <strong>{{ selectedCourse?.courseName || '请选择实验' }}</strong>
          </div>
          <div class="rail-tabs" role="listbox" aria-label="选择分析实验">
            <button
              v-for="course in courses"
              :key="course.courseId"
              type="button"
              role="option"
              :aria-selected="selectedCourseId === course.courseId"
              :class="{ active: selectedCourseId === course.courseId }"
              @click="selectedCourseId = course.courseId"
            >
              <span class="rail-no">{{ course.teachingOrder }}</span>
              <span class="rail-name">{{ course.courseName }}</span>
            </button>
          </div>
        </div>
      </section>
      <div v-if="courseError" class="notice error analysis-notice">{{ courseError }}</div>

      <div class="analysis-tabs" role="tablist"><button :class="{ active: activeTab === 'class' }" @click="activeTab = 'class'">班级实验分析</button><button :class="{ active: activeTab === 'student' }" @click="activeTab = 'student'">学生实验分析</button></div>
      <div v-if="classDataLoading" class="panel loading-state">正在读取最新学习数据…</div>

      <template v-else-if="activeTab === 'class'">
        <div v-if="classError" class="notice error analysis-notice">{{ classError }}</div>
        <div v-if="rebuildMessage" class="notice success analysis-notice">{{ rebuildMessage }}</div>
        <section class="panel result-panel"><CourseAnalysisPanel :data="classCourseAnalysis" :analysing="classCourseAnalysing" subject-label="班级" @analyse="runClassCourseAnalysis" /></section>
        <section class="panel result-panel"><CourseQuestionRecords :data="classCourseQuestions" :loading="courseDataLoading" scope-label="班级" /></section>
        <div class="supplement-title"><strong>跨实验辅助统计</strong></div>
        <section class="panel result-panel">
          <div class="panel-head"><div><h2>班级学习情况</h2><p v-if="classAnalysis?.analysis">最近分析：{{ formatDateTime(classAnalysis.generatedAt) }}</p></div><div class="head-actions"><button class="secondary-button" :disabled="rebuildingProfiles" @click="rebuildProfiles">{{ rebuildingProfiles ? '正在更新画像…' : '更新32人画像' }}</button><button class="primary-button" :disabled="classAnalysing" @click="runClassAnalysis">{{ classAnalysing ? '正在分析…' : classAnalysis?.analysis ? '重新分析' : '开始分析' }}</button></div></div>
          <div v-if="classAnalysisNotice" class="notice analysis-notice scoped-analysis-notice" :class="classAnalysisNotice.tone">{{ classAnalysisNotice.message }}</div>
          <div v-if="classAnalysis?.analysis" class="result-body"><p class="overall-comment">{{ classAnalysis.analysis.overallComment }}</p><div v-if="classProblems.length" class="problem-list"><article v-for="(item,index) in classProblems" :key="`${item.title}-${index}`" class="problem-card" :class="{ expanded: expandedProblemIndex === index }" role="button" :tabindex="0" :aria-expanded="expandedProblemIndex === index" @click="toggleProblem(index)" @keydown.enter.prevent="toggleProblem(index)"><div class="problem-index">{{ index+1 }}</div><div class="problem-main"><div class="problem-title"><strong>{{ item.title }}</strong><div class="problem-title-actions"><span>涉及 {{ item.studentCount }} 人</span><button type="button" class="problem-detail-button" @click.stop="toggleProblem(index)">{{ expandedProblemIndex === index ? '收起详情' : '查看详情' }}</button></div></div><p>{{ item.evidence }}</p><div class="teacher-action"><span>教学建议</span>{{ item.teacherAction }}</div><div v-if="expandedProblemIndex === index" class="problem-detail" @click.stop><template v-if="problemRisk(item)"><div class="problem-detail-summary"><div><span>对应知识点</span><strong>{{ problemRisk(item)?.knowledgePointName }}</strong></div><div><span>风险等级</span><strong :class="`risk-${getRiskPresentation(problemRisk(item)?.riskLevel).tone}`">{{ getRiskPresentation(problemRisk(item)?.riskLevel).label }}</strong></div><div><span>错题率</span><strong>{{ Math.round(Number(problemRisk(item)?.incorrectRate || 0) * 100) }}%</strong></div><div><span>错误记录</span><strong>{{ problemRisk(item)?.incorrectCount || 0 }} 条</strong></div></div><div class="problem-detail-section"><h4>涉及学生</h4><div class="student-chips"><span v-for="student in problemRisk(item)?.affectedStudents || []" :key="student.studentId">{{ student.studentName || `学生 ${student.studentId}` }}</span></div></div><div class="problem-detail-section"><h4>代表性错题</h4><div v-for="question in problemRisk(item)?.representativeQuestions || []" :key="question.generatedQuestionId" class="question-row">{{ question.title }}<small>{{ question.generatedQuestionId }}</small></div></div><button type="button" class="problem-action-link" @click="selectRisk(problemRisk(item)!)">打开知识点详情与 AI 分析</button></template><template v-else><div class="problem-detail-section"><h4>证据题目</h4><div class="student-chips"><span v-for="questionId in item.questionIds" :key="questionId">{{ questionId }}</span></div><p>当前问题已有班级分析证据，但还没有匹配到本实验的知识点错误记录。</p></div></template></div></div></article></div></div>
          <div v-else class="empty-state compact-empty"><strong>暂无班级 AI 分析</strong></div>
        </section>
        <section class="panel feature-panel"><KnowledgeRiskPieChart :items="riskItems" :selected-course-id="selectedCourseId!" @select="selectRisk" /></section>
        <KnowledgeRiskDetailDrawer
          :open="riskDrawerOpen"
          :class-id="selectedClassId!"
          :course-id="selectedCourseId!"
          :item="selectedRisk"
          :all-students="students"
          @close="riskDrawerOpen = false"
          @issued="loadInterventions"
        />
        <section class="panel feature-panel"><TeachingActionPanel :class-id="selectedClassId!" :students="students" :selected-risk="selectedRisk" :interventions="interventions" @changed="loadInterventions" /></section>
      </template>

      <template v-else>
        <div class="student-analysis-grid">
          <aside class="panel student-list-panel"><div class="student-search"><input v-model="studentSearch" placeholder="搜索姓名或学号" /></div><button v-for="student in filteredStudents" :key="student.studentId" class="student-row" :class="{ active: selectedStudentId === student.studentId }" @click="selectedStudentId = student.studentId"><span class="student-avatar">{{ (student.studentName || '学').slice(0,1) }}</span><span><strong>{{ student.studentName || '未填写姓名' }}</strong><small>{{ student.studentNumber }} · {{ student.administrativeClass || '未填写行政班' }}</small></span></button><div v-if="!filteredStudents.length" class="empty-state compact-empty">没有匹配的学生。</div></aside>
          <main class="student-content">
            <section class="panel student-result-panel"><CourseAnalysisPanel :data="studentCourseAnalysis" :analysing="studentCourseAnalysing" :subject-label="selectedStudent ? `${selectedStudent.studentName || selectedStudent.studentNumber}的` : '学生'" @analyse="runStudentCourseAnalysis" /></section>
            <section class="panel student-result-panel"><CourseQuestionRecords :data="studentCourseQuestions" :loading="studentDataLoading || courseDataLoading" :scope-label="selectedStudent ? `${selectedStudent.studentName || selectedStudent.studentNumber}的` : '学生'" /></section>
            <div class="supplement-title"><strong>跨实验五维画像</strong></div>
            <section class="panel student-result-panel">
              <div v-if="!selectedStudent" class="empty-state"><strong>请选择学生</strong>从左侧名单选择一名学生查看学习情况。</div>
              <div v-else-if="studentDataLoading" class="loading-state">正在读取 {{ selectedStudent.studentName || selectedStudent.studentNumber }} 的学习数据…</div>
              <template v-else><div class="panel-head"><div><h2>{{ selectedStudent.studentName || '未填写姓名' }} · 综合画像</h2><p>{{ selectedStudent.studentNumber }} · 最近活跃 {{ formatDateTime(selectedStudent.recentActivityAt) }}</p></div><button class="secondary-button" :disabled="studentAnalysing" @click="runStudentAnalysis">{{ studentAnalysing ? '正在更新…' : '更新综合画像分析' }}</button></div><div v-if="studentError" class="notice error analysis-notice">{{ studentError }}</div><div class="student-result-body"><div class="profile-score-grid"><div v-for="card in scoreCards" :key="card[0]"><span>{{ card[0] }}</span><strong>{{ formatScore(card[1]) }}</strong></div></div><div v-if="studentAnalysis?.analysis" class="student-analysis-content"><div class="analysis-time">跨实验分析更新于：{{ formatDateTime(studentAnalysis.generatedAt) }}</div><p class="overall-comment">{{ studentAnalysis.analysis.overallComment }}</p><article v-for="item in studentAnalysis.analysis.focusAreas" :key="item.dimension" class="focus-card"><div><strong>{{ item.label }}</strong><span :class="`priority-${item.priority || 'medium'}`">{{ item.priority === 'high' ? '优先关注' : '持续观察' }}</span></div><p>{{ item.evidence }}</p><div class="teacher-action"><span>建议做法</span>{{ item.teacherAction }}</div></article></div></div></template>
            </section>
            <CapabilityGrowthPanel
              class="student-result-panel"
              :data="capabilityGrowth"
              :loading="studentDataLoading"
              :error="capabilityGrowthError"
              teacher-mode
              @retry="loadStudentData"
            />
            <section class="panel feature-panel"><CapabilityEvidencePanel :data="capabilityEvidence" /></section>
            <section class="panel feature-panel"><LearningReplayTimeline :items="learningReplay?.items || []" /></section>
          </main>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* 全部颜色走 daisyUI 语义 token，不写死十六进制 —— 写死的话这一页在 night 主题下
   纹丝不动：深藏青正文（如 #182843）落在深色卡面上就是"看不见"，纯白药丸背景（#fff）
   在暗色里则刺眼。这是教师端和学生端观感割裂的老问题，2026-07-29 清过一次，
   后来被重新引入，2026-08-08 再次清零并把压成一行的样式展开。

   映射规则（按绝对色度差 (max-min)/255 判定，不能用 HLS 饱和度）：
     色度 < .24 且亮度高  -> 面/线：--b1 / --b2 / --bc 低透明度
     色度 < .24 且亮度低  -> 正文：--bc（如 #25364e、#182843 都属于这一类，别刷成蓝色）
     色度 高 且偏蓝       -> --p 主色
     色度 高 且偏橙棕     -> --wa 警告
     色度 高 且偏红       -> --er
     色度 高 且偏绿       -> --su                                                */

.class-select {
  min-width: 330px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid oklch(var(--bc) / 0.2);
  border-radius: 7px;
  background: oklch(var(--b1));
  color: oklch(var(--bc));
  font-size: 13px;
}

/* ============================================================
   顶部仪表台
   ------------------------------------------------------------
   原来这里是两个并排的圆角盒子（统计条 + 实验切换），和下面五个 .panel 长得一模一样，
   于是整页读起来就是"八个白盒子"，没有主次。合成一块仪表台之后，顶部承担
   "上下文"这个单一职责：哪个班 / 这个实验多大规模 / 正在看哪个实验。

   视觉语言刻意和学生端的星空层呼应：顶边一道主色能量条、右上一团柔光、
   底纹是极淡的网格 —— 和 AmbientBackdrop 的 .ambient-grid 同一套语汇。
   读数用等宽表格数字（tabular-nums），换实验时数字不会左右抖动。
   ============================================================ */
/* 面本身保持干净：不加网格底纹、柔光、能量条这类质感效果 —— 层次全部交给
   排版和那条主色渐变去表达。渐变文字沿用学生端首页
   「开启你的安全实验之旅」的 from-primary via-secondary to-accent，两端同一套语言。 */
.analysis-console {
  position: relative;
  margin-bottom: 18px;
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: var(--rounded-box, 1rem);
  background: oklch(var(--b1));
  box-shadow: 0 1px 3px oklch(var(--bc) / 0.06);
  overflow: hidden;
}

/* 渐变文字的公共写法。注意 background-clip:text 之后 color 必须透明，
   而一旦透明就没有可测的前景色了 —— 所以只用在大字上（班级名 27px / 读数 30px），
   小字一律保持实色，避免出现读不清又量不出来的文本。 */
.gradient-text {
  background: linear-gradient(
    100deg,
    oklch(var(--p)) 0%,
    oklch(var(--s)) 48%,
    oklch(var(--a)) 100%
  );
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  /* 渐变铺在字形上，字重够粗才不会显得发虚 */
  -webkit-text-fill-color: transparent;
}

.console-top {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto;
  gap: 26px;
  align-items: center;
  padding: 22px 24px 20px;
}

/* ---------- 班级身份 ---------- */
.console-identity {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.console-eyebrow {
  display: block;
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.14em;
}

.console-identity strong {
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.18;
  /* 渐变裁到字形上时，行高留不够下缘会被切掉（"班"字的竖钩最明显） */
  padding-bottom: 2px;
}

.console-identity small {
  color: oklch(var(--bc) / 0.6);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 11px;
}

/* ---------- 三个读数 ---------- */
.console-metrics {
  display: flex;
  align-items: stretch;
  gap: 0;
}

.metric {
  display: grid;
  align-content: center;
  gap: 2px;
  min-width: 132px;
  padding: 2px 22px;
  border-left: 1px solid oklch(var(--bc) / 0.12);
}

.metric:first-child {
  border-left: 0;
}

.metric span {
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
  letter-spacing: 0.04em;
}

/* tabular-nums：换实验时 31 -> 143 不会把标签挤得左右跳。
   color 写成 :not(.gradient-text)：`.metric strong` 特异度 (0,1,1) 高于
   `.gradient-text` (0,1,0)，直接写会把渐变的 transparent 盖回实色。 */
.metric strong {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 32px;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
  padding-bottom: 2px;
}

.metric strong:not(.gradient-text) {
  color: oklch(var(--bc));
}

.metric em {
  color: oklch(var(--bc) / 0.6);
  font-size: 10px;
  font-style: normal;
}

/* 错题读数按错题率变色，三档和知识点风险的语义对齐：
   给出「29」的同时给出「占全部题目 20%」，教师才读得出轻重 */
.metric-alert.tone-calm strong { color: oklch(var(--su)); }
.metric-alert.tone-warning strong { color: oklch(var(--wa)); }
.metric-alert.tone-danger strong { color: oklch(var(--er)); }

.metric-bar {
  position: relative;
  height: 3px;
  margin-top: 6px;
  border-radius: 999px;
  background: oklch(var(--bc) / 0.12);
  overflow: hidden;
}

.metric-bar > i {
  position: absolute;
  inset: 0 auto 0 0;
  width: var(--fill, 0%);
  border-radius: inherit;
  transition: width 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.metric-alert.tone-calm .metric-bar > i { background: oklch(var(--su)); }
.metric-alert.tone-warning .metric-bar > i { background: oklch(var(--wa)); }
.metric-alert.tone-danger .metric-bar > i { background: oklch(var(--er)); }

/* ---------- 实验切换轨道 ---------- */
.console-rail {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
  padding: 14px 24px 16px;
  border-top: 1px solid oklch(var(--bc) / 0.1);
  background: oklch(var(--b2) / 0.5);
}

.rail-label {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.rail-label span {
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
  letter-spacing: 0.04em;
}

.rail-label strong {
  color: oklch(var(--bc));
  font-size: 15px;
  font-weight: 700;
}

.rail-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 3px 2px;
  scrollbar-width: thin;
}

.rail-tabs button {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
  padding: 8px 13px 8px 9px;
  border: 1px solid oklch(var(--bc) / 0.16);
  border-radius: 999px;
  background: oklch(var(--b1));
  color: oklch(var(--bc) / 0.7);
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease,
    box-shadow 0.16s ease, transform 0.16s ease;
}

.rail-tabs button:hover {
  border-color: oklch(var(--p) / 0.5);
  color: oklch(var(--bc));
  transform: translateY(-1px);
}

.rail-no {
  display: grid;
  width: 21px;
  height: 21px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: oklch(var(--bc) / 0.1);
  color: oklch(var(--bc) / 0.65);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
  transition: background 0.16s ease, color 0.16s ease;
}

/* 选中态：实心主色 + 一圈辉光，和顶边能量条、学生端的柔光是同一套语言。
   这里刻意不用「主色淡底 + 主色文字」——实测 light 主题下 --p 压在 --p/.14 底上
   只有 4.24:1，12px 小字达不到 WCAG 的 4.5。实心底是 night 9.16 / light 4.75，
   而且选中的实验决定整页数据，本来就该是最重的那个状态。 */
.rail-tabs button.active {
  border-color: oklch(var(--p));
  background: oklch(var(--p));
  color: oklch(var(--pc));
  font-weight: 650;
  box-shadow: 0 0 0 3px oklch(var(--p) / 0.15), 0 6px 18px oklch(var(--p) / 0.3);
}

.rail-tabs button.active:hover {
  border-color: oklch(var(--p));
  color: oklch(var(--pc));
}

.rail-tabs button.active .rail-no {
  background: oklch(var(--pc) / 0.25);
  color: oklch(var(--pc));
}

.rail-tabs button:focus-visible {
  outline: 2px solid oklch(var(--p));
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .live-dot { animation: none; }
  .metric-bar > i { transition: none; }
  .rail-tabs button:hover { transform: none; }
}

/* ============================================================
   板块标题
   ------------------------------------------------------------
   五个 .panel 的标题原来和正文一个重量，扫一眼分不出段落。
   加一道主色竖条 + 收紧字距，让"这是一个新板块"在余光里就成立。
   只作用于本页（.analysis-page），不动其他教师页。
   ============================================================ */
/* 五个板块的标题分散在各自组件里，用的 class 各不相同：
     .panel-head    本页模板（班级学习情况）
     .analysis-head CourseAnalysisPanel（班级实验分析）
     .records-head  CourseQuestionRecords（全部做题情况）
     .section-heading KnowledgeRiskPieChart / TeachingActionPanel（知识点分布、教学行动）
   全列出来，否则只有一个标题带竖条、反而更乱。
   h3（建议下一步、行动追踪）刻意不加 —— 那是下一层，加了层级就压平了。 */
.analysis-page :deep(.panel-head h2),
.analysis-page :deep(.analysis-head h2),
.analysis-page :deep(.records-head h2),
.analysis-page :deep(.section-heading h2),
.analysis-page .supplement-title strong {
  position: relative;
  padding-left: 12px;
  letter-spacing: -0.01em;
}

.analysis-page :deep(.panel-head h2)::before,
.analysis-page :deep(.analysis-head h2)::before,
.analysis-page :deep(.records-head h2)::before,
.analysis-page :deep(.section-heading h2)::before,
.analysis-page .supplement-title strong::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  width: 3px;
  height: 1em;
  transform: translateY(-50%);
  border-radius: 999px;
  background: oklch(var(--p));
}

/* ---------- 班级/学生 分析切换 ---------- */
.analysis-tabs {
  display: flex;
  gap: 24px;
  margin: 0 0 14px;
  border-bottom: 1px solid oklch(var(--bc) / 0.14);
}

.analysis-tabs button {
  padding: 11px 2px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: oklch(var(--bc) / 0.6);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: color 0.16s ease, border-color 0.16s ease;
}

.analysis-tabs button:hover {
  color: oklch(var(--bc) / 0.85);
}

.analysis-tabs button.active {
  border-color: oklch(var(--p));
  color: oklch(var(--p));
}

.result-panel,
.feature-panel {
  margin-bottom: 18px;
}

.feature-panel {
  padding: 20px;
}

.result-body,
.student-result-body {
  padding: 22px;
}

.head-actions {
  display: flex;
  gap: 9px;
}

/* ---------- 班级总评 ---------- */
.overall-comment {
  margin: 0 0 20px;
  padding: 14px 16px;
  border-left: 3px solid oklch(var(--p));
  background: oklch(var(--p) / 0.08);
  color: oklch(var(--bc) / 0.85);
  font-size: 13px;
  line-height: 1.75;
}

/* ---------- 问题卡片 ---------- */
.problem-list {
  display: grid;
  gap: 12px;
}

.problem-card {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: 12px;
  padding: 16px;
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.problem-card:hover,
.problem-card:focus-visible,
.problem-card.expanded {
  border-color: oklch(var(--p) / 0.5);
  box-shadow: 0 5px 16px oklch(var(--bc) / 0.1);
  outline: none;
}

.problem-index {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 6px;
  background: oklch(var(--p) / 0.14);
  color: oklch(var(--p));
  font-size: 12px;
  font-weight: 750;
}

.problem-main {
  min-width: 0;
}

.problem-title {
  display: flex;
  justify-content: space-between;
  gap: 15px;
}

.problem-title strong {
  font-size: 14px;
}

/* 正确率标注是琥珀色告警语义，不是红色 */
.problem-title span {
  color: oklch(var(--wa));
  font-size: 12px;
}

.problem-title-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  white-space: nowrap;
}

.problem-title-actions > span {
  color: oklch(var(--wa));
  font-size: 12px;
}

.problem-card p,
.focus-card p {
  margin: 8px 0;
  color: oklch(var(--bc) / 0.65);
  font-size: 12px;
  line-height: 1.65;
}

.problem-detail-button {
  padding: 5px 9px;
  border: 1px solid oklch(var(--p) / 0.35);
  border-radius: 5px;
  background: oklch(var(--b1));
  color: oklch(var(--p));
  font-size: 11px;
  cursor: pointer;
}

.problem-detail {
  margin-top: 14px;
  padding: 15px;
  border-top: 1px solid oklch(var(--bc) / 0.12);
  background: oklch(var(--b2));
  cursor: default;
}

.problem-detail-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.problem-detail-summary > div {
  display: grid;
  gap: 4px;
  padding: 10px;
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: 6px;
  background: oklch(var(--b1));
}

.problem-detail-summary span,
.problem-detail-section h4 {
  margin: 0;
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
}

/* #25364e 色度 0.16 —— 深藏青正文，不是主色，别刷成蓝的 */
.problem-detail-summary strong {
  color: oklch(var(--bc));
  font-size: 13px;
}

.problem-detail-section {
  margin-top: 13px;
}

.student-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 7px;
}

.student-chips span {
  padding: 5px 9px;
  border-radius: 999px;
  background: oklch(var(--p) / 0.14);
  color: oklch(var(--p));
  font-size: 11px;
}

.question-row {
  display: flex;
  width: 100%;
  justify-content: space-between;
  gap: 12px;
  margin-top: 7px;
  padding: 9px 10px;
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: 6px;
  background: oklch(var(--b1));
  color: oklch(var(--bc) / 0.85);
  text-align: left;
}

.question-row small {
  color: oklch(var(--bc) / 0.6);
}

.problem-action-link {
  margin-top: 13px;
  padding: 8px 11px;
  border: 0;
  border-radius: 6px;
  background: oklch(var(--p));
  color: oklch(var(--pc));
  font-size: 12px;
  cursor: pointer;
}

/* ---------- 教师动作 ---------- */
.teacher-action {
  padding: 10px 12px;
  border-radius: 6px;
  background: oklch(var(--b2));
  color: oklch(var(--bc) / 0.85);
  font-size: 12px;
  line-height: 1.6;
}

.teacher-action span {
  margin-right: 8px;
  color: oklch(var(--p));
  font-weight: 700;
}

.analysis-notice {
  margin: 0 0 12px;
}

.scoped-analysis-notice {
  margin: 14px 22px 0;
}

.compact-empty {
  padding: 34px 20px;
}

/* ---------- 学生分析 ---------- */
.student-analysis-grid {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.student-list-panel {
  position: sticky;
  top: 16px;
  max-height: calc(100vh - 50px);
  overflow: auto;
}

.student-search {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 13px;
  border-bottom: 1px solid oklch(var(--bc) / 0.12);
  background: oklch(var(--b1));
}

.student-search input {
  width: 100%;
  height: 38px;
  padding: 0 11px;
  border: 1px solid oklch(var(--bc) / 0.2);
  border-radius: 7px;
  outline: none;
  background: oklch(var(--b1));
  color: oklch(var(--bc));
}

.student-search input:focus {
  border-color: oklch(var(--p));
  box-shadow: 0 0 0 3px oklch(var(--p) / 0.15);
}

.student-row {
  display: flex;
  width: 100%;
  gap: 10px;
  padding: 12px 14px;
  border: 0;
  border-bottom: 1px solid oklch(var(--bc) / 0.12);
  background: oklch(var(--b1));
  color: oklch(var(--bc) / 0.85);
  text-align: left;
  cursor: pointer;
  transition: background 0.14s ease;
}

.student-row:hover,
.student-row.active {
  background: oklch(var(--p) / 0.1);
}

.student-row.active {
  box-shadow: inset 3px 0 oklch(var(--p));
}

.student-avatar {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: oklch(var(--p) / 0.15);
  color: oklch(var(--p));
  font-weight: 700;
}

.student-row strong,
.student-row small {
  display: block;
}

.student-row strong {
  font-size: 13px;
}

.student-row small {
  margin-top: 4px;
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
}

.student-content {
  min-width: 0;
}

.student-result-panel {
  margin-bottom: 18px;
}

.profile-score-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  margin-bottom: 20px;
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: 8px;
  overflow: hidden;
}

.profile-score-grid div {
  display: grid;
  gap: 5px;
  padding: 14px;
  border-right: 1px solid oklch(var(--bc) / 0.12);
}

.profile-score-grid div:last-child {
  border-right: 0;
}

.profile-score-grid span {
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
}

.profile-score-grid strong {
  color: oklch(var(--p));
  font-size: 20px;
}

.analysis-time {
  margin-bottom: 9px;
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
}

.focus-card {
  margin-top: 11px;
  padding: 15px;
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: 8px;
}

.focus-card > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.focus-card strong {
  font-size: 14px;
}

.focus-card > div:first-child span {
  padding: 3px 7px;
  border-radius: 999px;
  font-size: 10px;
}

.priority-high {
  background: oklch(var(--wa) / 0.16);
  color: oklch(var(--wa));
}

.priority-medium,
.priority-low {
  background: oklch(var(--p) / 0.13);
  color: oklch(var(--p));
}

.supplement-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 25px 2px 12px;
}

.supplement-title strong {
  color: oklch(var(--bc));
  font-size: 15px;
}

.supplement-title span {
  color: oklch(var(--bc) / 0.6);
  font-size: 11px;
}

/* ---------- 风险等级文字 ---------- */
.risk-danger {
  color: oklch(var(--er)) !important;
}

.risk-warning {
  color: oklch(var(--wa)) !important;
}

.risk-success {
  color: oklch(var(--su)) !important;
}

/* ---------- 响应式 ---------- */
@media (max-width: 1080px) {
  /* 读数换行到班级身份下面，并把左侧竖线改成上方横线 */
  .console-top {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .console-metrics {
    border-top: 1px solid oklch(var(--bc) / 0.12);
    padding-top: 16px;
  }

  .metric {
    flex: 1;
    min-width: 0;
    padding: 0 16px;
  }

  .console-rail {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .student-analysis-grid {
    grid-template-columns: 250px minmax(0, 1fr);
  }

  .profile-score-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 820px) {
  .class-select {
    width: 100%;
    min-width: 0;
  }

  .student-analysis-grid {
    grid-template-columns: 1fr;
  }

  /* 窄屏下三个读数纵向排，各自留一条上边线 */
  .console-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px 0;
  }

  .metric {
    border-left: 0;
    padding: 0 12px;
  }

  .metric-alert {
    grid-column: 1 / -1;
  }

  .console-identity strong {
    font-size: 23px;
  }

  .metric strong {
    font-size: 26px;
  }

  .student-list-panel {
    position: static;
    max-height: 320px;
  }

  .profile-score-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .panel-head {
    flex-direction: column;
  }

  .head-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .head-actions button,
  .panel-head > .primary-button {
    flex: 1;
  }
}
</style>
