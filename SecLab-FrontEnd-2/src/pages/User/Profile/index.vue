<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { User } from '../../../types/user'
import {
  avatarUrl,
  diagnoseTraining,
  generateTrainingQuestionSet,
  generateTrainingQuestions,
  getApiErrorMessage,
  isImageServiceUnreachable,
  uploadImageFile,
  getProfileDashboard,
  getProfileLatest,
  getStudentCapabilityGrowth,
  getTrainingSessionSummary,
  getTrainingQuestions,
  getUserInfo,
  getUserTrainingSessions,
  type ProfileRecommendationItem,
  submitGeneratedQuestionAnswer,
  submitTrainingAnswer,
  updateUserInfoByToken,
  type GeneratedQuestionAnswerSubmitResponse,
  type GeneratedTrainingQuestion,
  type CapabilityGrowthResponseDto,
  type ProfileDashboardResponse,
  type ProfileLatestResponse,
  type TrainingDiagnoseResponse,
  type TrainingQuestionSetItem,
  type TrainingSessionSummaryResponse,
  type TrainingSingleQuestion,
  type TrainingSessionData,
  type WeakKnowledgePoint
} from '../../../api'
import { showToast, useCookie } from '../../../common'
import CapabilityGrowthPanel from '../../../components/CapabilityGrowthPanel.vue'
import SolveHistoryPanel from './SolveHistoryPanel.vue'
import TeacherAssignments from './TeacherAssignments.vue'
import { trainingGenerationErrorMessage, trainingWaitMessage } from './trainingReadiness'

type SolveRecord = ProfileDashboardResponse['solveRecords'][number]
type LoginStorageUser = Partial<User> & {
  studentNumber?: string
  studentNo?: string
  account?: string
  username?: string
  phone?: string
  major?: string
  data?: unknown
  loginData?: unknown
}

type AnalysisDimensionCard = {
  icon: string
  label: string
  desc: string
  borderClass: string
  iconClass: string
}

type ProfileRecommendationCard = {
  id: string
  title: string
  dimension: string
  dimensionName: string
  score: number
  scoreText: string
  resourceType: string
  resourceTypeLabel: string
  difficulty: number | null
  difficultyText: string
  priorityLabel: string
  priorityClass: string
  reason: string
  action: string
  actionText: string
  actionDisabled: boolean
  actionHint: string
  courseId: number | null
  moduleId: number | null
  labId: number | null
  knowledgeTags: string[]
  tags: string[]
}

type RecommendationQuestionState = {
  generatedQuestionId?: string
  question?: TrainingSingleQuestion | null
  answerVisible?: boolean
  teachingAnalysisVisible?: boolean
  studentAnswer?: string
  submittingAnswer?: boolean
  feedback?: GeneratedQuestionAnswerSubmitResponse | null
  loading: boolean
  trainingSessionId: string
  questions: RecommendationPracticeQuestion[]
  currentIndex: number
  answers: Record<string, string>
  attempts: Record<string, GeneratedQuestionAnswerSubmitResponse>
  submittedQuestionIds: string[]
  completed: boolean
  summaryLoading: boolean
  summary: TrainingSessionSummaryResponse | null
  error: string
  submitError: string
  doneNotice: string
}

type RecommendationPracticeQuestion = TrainingQuestionSetItem & {
  submitted: boolean
  submitting: boolean
  score: number | null
  level: string
  briefFeedback: string
  expanded: boolean
}

type TrainingRecommendationCard = {
  id: string
  title: string
  difficulty: string
  difficultyClass: string
  type: string
  tags: string[]
  reason: string
  moduleId?: number | null
  taskId?: number | null
  source: WeakKnowledgePoint
}

type TrainingQuestionViewModel = GeneratedTrainingQuestion & {
  currentAnswer: string
  submitting: boolean
  submitted: boolean
  isCorrect: boolean | null
  score: number | null
  submitError: string
  startedAt: number
  costTime: number | null
  explanationVisible: boolean
}

/** 画像速览只留「优势 / 短板」两张卡：阶段和更新时间已经在左侧身份栏里了，
    原来四张平铺会和身份栏、和下面的技能条三处重复讲同一件事 */
type ProfileFocusCard = {
  kind: 'strength' | 'gap'
  title: string
  skill: string
  score: number
  scoreText: string
  desc: string
  badge: string
}

type RailStat = {
  label: string
  value: string
  accent?: boolean
}

const cookie = useCookie()
const router = useRouter()
const STORAGE_USER_KEYS = ['userInfo', 'currentUser', 'user', 'loginUser', 'loginData', 'tokenUser', 'studentInfo', 'auth_student_number']
const EMPTY_PROFILE_MESSAGE = '暂无画像数据，完成实验、提交 Flag 或使用 AI 助手后将生成画像。'
const PROFILE_LOAD_ERROR_MESSAGE = '画像数据加载失败，请稍后重试。'
const EMPTY_RECOMMENDATIONS_MESSAGE = '暂无推荐任务'
const RECOMMENDATION_PRACTICE_COUNT = 7
const EMPTY_SKILLS = [
  { name: 'Web安全', score: 0, color: 'text-primary' },
  { name: '系统安全', score: 0, color: 'text-secondary' },
  { name: '密码学', score: 0, color: 'text-accent' },
  { name: '逆向工程', score: 0, color: 'text-info' },
  { name: '渗透测试', score: 0, color: 'text-success' }
]
const user = ref<User>({
  userId: 0,
  userStudentNumber: '',
  userName: '',
  userEmail: '',
  userTel: '',
  userAcademy: '',
  userClass: '',
  userGender: 1,
  userImage: '',
  classId: 0
})

const editedUser = ref<User>({ ...user.value })
const profileMajor = ref('')
const completedExperiments = ref(0)
const learningHours = ref(0)

const isLoadingUserData = ref(false)
const isEditing = ref(false)
const showProfileModal = ref(false)
const isLoading = ref(false)
const isLoaded = ref(false)

const userStats = ref({
  completedCourses: 0,
  totalScore: 0,
  ranking: 0,
  activeStreak: 0
})

const learningProfile = ref({
  skills: EMPTY_SKILLS.map((skill) => ({ ...skill })),
  tags: [] as ProfileDashboardResponse['learningProfile']['tags'],
  recentFocus: '',
  comprehensiveScore: 0,
  evaluation: '暂无学习记录'
})

const solveRecords = ref<SolveRecord[]>([])

const latestProfile = ref<ProfileLatestResponse | null>(null)
const pageRootRef = ref<HTMLElement | null>(null)
const capabilityGrowth = ref<CapabilityGrowthResponseDto | null>(null)
const capabilityGrowthLoading = ref(false)
const capabilityGrowthError = ref('')
const trainingDiagnoseResult = ref<TrainingDiagnoseResponse | null>(null)
const userTrainingSessions = ref<TrainingSessionData[]>([])
const activeTrainingSessionId = ref('')
const trainingQuestions = ref<TrainingQuestionViewModel[]>([])
const showTrainingView = ref(false)

const isLoadingDashboard = ref(false)
const dashboardLoaded = ref(true)
const dashboardError = ref('')
const pageNotice = ref('')

const diagnosing = ref(false)
const diagnoseError = ref('')
const generatingQuestions = ref(false)
const generateError = ref('')
const generatingRecommendationId = ref('')
const generationElapsedSeconds = ref(0)
let generationElapsedTimer: ReturnType<typeof setInterval> | null = null
const recommendationQuestionStates = ref<Record<string, RecommendationQuestionState>>({})
const refreshingProfileAfterSubmit = ref(false)
const profileRefreshError = ref('')
const displayProfile = computed(() => ({
  userName: user.value.userName || '未填写',
  studentNo: user.value.userStudentNumber || '未填写',
  className: user.value.userClass || '未填写',
  college: user.value.userAcademy || '未填写',
  major: profileMajor.value || '未填写',
  email: user.value.userEmail || '未填写',
  phone: user.value.userTel || '未填写'
}))

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : null
}

function parseStorageValue(raw: string) {
  const text = raw.trim()
  if (!text) return null
  if ((text.startsWith('{') && text.endsWith('}')) || (text.startsWith('[') && text.endsWith(']'))) {
    try {
      return JSON.parse(text)
    } catch {
      return raw
    }
  }
  return raw
}

function candidateRecords(value: unknown): Record<string, unknown>[] {
  const queue = [value]
  const records: Record<string, unknown>[] = []

  while (queue.length) {
    const current = queue.shift()
    const record = asRecord(current)
    if (!record) continue
    records.push(record)
    if (record.data) queue.push(record.data)
    if (record.loginData) queue.push(record.loginData)
  }

  return records
}

function readFirstString(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key]
    if (value === null || value === undefined) continue
    const normalized = String(value).trim()
    if (normalized) return normalized
  }
  return ''
}

function getCurrentLoginUser(): LoginStorageUser | null {
  if (typeof window === 'undefined') return null

  const merged: LoginStorageUser = {}
  const storages = [window.localStorage, window.sessionStorage]

  const assignIfEmpty = (key: keyof LoginStorageUser, value: unknown) => {
    const normalized = value === null || value === undefined ? '' : String(value).trim()
    if (!normalized) return
    if (!merged[key]) {
      merged[key] = normalized as never
    }
  }

  for (const storage of storages) {
    for (const key of STORAGE_USER_KEYS) {
      const raw = storage.getItem(key)
      if (!raw) continue

      if (key === 'auth_student_number') {
        assignIfEmpty('userStudentNumber', raw)
        assignIfEmpty('studentNumber', raw)
        assignIfEmpty('studentNo', raw)
        assignIfEmpty('account', raw)
        continue
      }

      const parsed = parseStorageValue(raw)
      for (const record of candidateRecords(parsed)) {
        assignIfEmpty('userName', readFirstString(record, ['userName', 'username', 'accountName', 'name']))
        assignIfEmpty('username', readFirstString(record, ['username', 'userName', 'accountName', 'name']))
        assignIfEmpty('userStudentNumber', readFirstString(record, ['userStudentNumber', 'studentNumber', 'studentNo', 'account']))
        assignIfEmpty('studentNumber', readFirstString(record, ['studentNumber', 'userStudentNumber', 'studentNo', 'account']))
        assignIfEmpty('studentNo', readFirstString(record, ['studentNo', 'studentNumber', 'userStudentNumber', 'account']))
        assignIfEmpty('account', readFirstString(record, ['account', 'studentNumber', 'userStudentNumber']))
        assignIfEmpty('userEmail', readFirstString(record, ['userEmail', 'email']))
        assignIfEmpty('userTel', readFirstString(record, ['userTel', 'phone', 'mobile']))
        assignIfEmpty('phone', readFirstString(record, ['phone', 'mobile', 'userTel']))
        assignIfEmpty('userAcademy', readFirstString(record, ['userAcademy', 'college', 'academy']))
        assignIfEmpty('userClass', readFirstString(record, ['userClass', 'className', 'class']))
        assignIfEmpty('major', readFirstString(record, ['major', 'specialty']))
      }
    }
  }

  return Object.keys(merged).length ? merged : null
}

function createEmptyTrainingDiagnose(userId: number, classId = 0, courseId = 0): TrainingDiagnoseResponse {
  return {
    profile_snapshot_id: null,
    user_id: userId,
    class_id: classId || null,
    course_id: courseId || null,
    dimension_scores: {
      knowledge_mastery_score: 0,
      troubleshooting_score: 0,
      autonomy_score: 0,
      ai_collaboration_score: 0,
      engagement_score: 0,
      overall_score: 0
    },
    weak_dimensions: [],
    tags: [],
    recent_focus: '',
    weak_knowledge_points: [],
    generation_constraints: {
      difficulty: 'medium',
      question_types: ['single_choice', 'fill_blank', 'short_answer'],
      question_count: 5
    },
    recent_evidence: {
      recent_errors: [],
      recent_failed_tasks: [],
      recent_ai_topics: []
    }
  }
}

function applyEmptyProfileBundle(loginUser?: LoginStorageUser | null) {
  const userName = loginUser?.userName || loginUser?.username || ''
  const studentNumber = loginUser?.userStudentNumber || loginUser?.studentNumber || loginUser?.studentNo || loginUser?.account || ''
  const email = loginUser?.userEmail || ''
  const phone = loginUser?.userTel || loginUser?.phone || ''
  const academy = loginUser?.userAcademy || ''
  const className = loginUser?.userClass || ''

  user.value = {
    userId: user.value.userId || 0,
    userStudentNumber: studentNumber,
    userName,
    userEmail: email,
    userTel: phone,
    userAcademy: academy,
    userClass: className,
    userGender: typeof user.value.userGender === 'number' ? user.value.userGender : 1,
    userImage: loginUser?.userImage || '',
    classId: user.value.classId || 0
  }
  editedUser.value = { ...user.value }
  profileMajor.value = loginUser?.major || ''
  completedExperiments.value = 0
  learningHours.value = 0
  userStats.value = {
    completedCourses: 0,
    totalScore: 0,
    ranking: 0,
    activeStreak: 0
  }
  learningProfile.value = {
    skills: EMPTY_SKILLS.map((skill) => ({ ...skill })),
    tags: [],
    recentFocus: '',
    comprehensiveScore: 0,
    evaluation: '暂无学习记录'
  }
  solveRecords.value = []
  latestProfile.value = null
  capabilityGrowth.value = null
  capabilityGrowthError.value = ''
  trainingDiagnoseResult.value = createEmptyTrainingDiagnose(user.value.userId || 0, user.value.classId || 0, 0)
  userTrainingSessions.value = []
}

function hasMeaningfulDashboardData(profileDashboard: ProfileDashboardResponse | null) {
  if (!profileDashboard) return false

  const hasStats = Object.values(profileDashboard.userStats || {}).some((value) => Number(value || 0) > 0)
  const hasSkills = (profileDashboard.learningProfile?.skills || []).some((skill) => Number(skill.score || 0) > 0)
  const hasTags = Boolean(profileDashboard.learningProfile?.tags?.length)
  const hasRecords = Boolean(profileDashboard.solveRecords?.length)

  return hasStats || hasSkills || hasTags || hasRecords
}

function hasMeaningfulLatestProfile(profile: ProfileLatestResponse | null) {
  return Boolean(profile?.snapshot_id || profile?.overall_score || profile?.knowledge_mastery_score)
}

const displayUserImage = computed(() => avatarUrl(user.value.userImage))

// ---- 头像上传 ----
const avatarFile = ref<File | null>(null)
const avatarPreview = ref('')
const avatarError = ref('')
const isUploadingAvatar = ref(false)

/** 编辑中优先显示本地预览，其次显示已保存的头像 */
const editingAvatarImage = computed(() => avatarPreview.value || avatarUrl(editedUser.value.userImage))

const resetAvatarPicker = () => {
  if (avatarPreview.value) {
    URL.revokeObjectURL(avatarPreview.value)
  }
  avatarFile.value = null
  avatarPreview.value = ''
  avatarError.value = ''
}

const handleAvatarChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] || null
  avatarError.value = ''

  if (!file) {
    resetAvatarPicker()
    return
  }
  if (!file.type.startsWith('image/')) {
    avatarError.value = '请选择图片文件。'
    input.value = ''
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    avatarError.value = '头像图片不能超过 2MB。'
    input.value = ''
    return
  }

  if (avatarPreview.value) {
    URL.revokeObjectURL(avatarPreview.value)
  }
  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

/** 移除头像：清掉待上传的文件，并把已保存的头像也置空（保存后生效） */
const removeAvatar = () => {
  resetAvatarPicker()
  editedUser.value = { ...editedUser.value, userImage: '' }
}

const currentUserId = computed(() => user.value.userId || 0)

const currentClassId = computed(() => {
  return user.value.classId ?? latestProfile.value?.class_id ?? trainingDiagnoseResult.value?.class_id ?? userTrainingSessions.value[0]?.class_id ?? 1
})

const currentCourseId = computed(() => {
  return latestProfile.value?.course_id ?? trainingDiagnoseResult.value?.course_id ?? userTrainingSessions.value[0]?.course_id ?? 1
})

const currentProfileSnapshotId = computed(() => {
  return trainingDiagnoseResult.value?.profile_snapshot_id ?? latestProfile.value?.snapshot_id ?? null
})

const latestProfileComputedAt = computed(() => {
  const raw = latestProfile.value?.computed_at || latestProfile.value?.created_at || ''
  return raw ? raw.replace('T', ' ').slice(0, 16) : '未同步'
})

const classRankText = computed(() => {
  const ranking = Number(userStats.value.ranking || 0)
  return ranking > 0 ? `#${ranking}` : '--'
})

const strongestSkill = computed(() => {
  const [first] = [...learningProfile.value.skills].sort((a, b) => b.score - a.score)
  return first || { name: '学习投入', score: 0, color: 'text-success' }
})

const weakestSkill = computed(() => {
  const [first] = [...learningProfile.value.skills].sort((a, b) => a.score - b.score)
  return first || { name: '渗透测试', score: 0, color: 'text-secondary' }
})

const profileStageSummary = computed(() => {
  const score = Number(learningProfile.value.comprehensiveScore || 0)
  if (score <= 0) return { label: '待生成', desc: EMPTY_PROFILE_MESSAGE, badgeClass: 'badge-ghost' }
  if (score >= 85) return { label: '稳定拔高期', desc: '已具备较强自主学习与复盘能力，可重点展示综合攻防与带队协作。', badgeClass: 'badge-success' }
  if (score >= 70) return { label: '能力成型期', desc: '基础能力稳定，正在通过专项训练补齐薄弱项，成长轨迹清晰可追踪。', badgeClass: 'badge-primary' }
  return { label: '重点提升期', desc: '画像已明确主要短板，系统正在围绕弱项持续生成针对性训练。', badgeClass: 'badge-warning' }
})

const displayTags = computed(() => {
  if (learningProfile.value.tags.length) {
    return learningProfile.value.tags
  }
  return [{ text: '暂无学习徽章', type: 'badge-ghost' }]
})

const hasProfileSignal = computed(() => Number(learningProfile.value.comprehensiveScore || 0) > 0)

/** 0 一律显示成破折号：加粗的 0 看着像 bug，破折号才读得出「还没有数据」 */
function statText(value: number | null | undefined) {
  const numeric = Number(value || 0)
  return numeric > 0 ? String(numeric) : '—'
}

const profileFocusCards = computed<ProfileFocusCard[]>(() => {
  const hasScore = hasProfileSignal.value

  return [
    {
      kind: 'strength',
      title: '当前优势',
      skill: hasScore ? strongestSkill.value.name : '暂无',
      score: hasScore ? strongestSkill.value.score : 0,
      scoreText: hasScore ? String(strongestSkill.value.score) : '—',
      desc: hasScore ? '基础概念掌握较稳定，适合继续挑战综合题。' : '当前账号暂无可展示的优势项目。',
      badge: hasScore ? '持续稳定' : '待生成'
    },
    {
      kind: 'gap',
      title: '下一步提升',
      skill: hasScore ? weakestSkill.value.name : '暂无',
      score: hasScore ? weakestSkill.value.score : 0,
      scoreText: hasScore ? String(weakestSkill.value.score) : '—',
      desc: hasScore ? '后续练习会优先安排相关题目，帮助你逐步提升解题思路。' : '当前账号暂无学习反馈，完成练习后将生成提升建议。',
      badge: hasScore ? '继续提升' : '待生成'
    }
  ]
})

/** 只给累计得分上色，其余保持中性 —— 四个数字四种颜色等于没有重点。
    注意这里的「累计得分」是 userStats.totalScore，和上方那个 0~100 的综合能力评分
    （learningProfile.comprehensiveScore）不是一个数；原来两处都叫「综合得分」，
    数值又不一样，看的人只会以为是 bug */
const railStats = computed<RailStat[]>(() => [
  { label: '累计得分', value: statText(userStats.value.totalScore), accent: true },
  { label: '完成课程', value: statText(userStats.value.completedCourses) },
  { label: '完成实验', value: statText(completedExperiments.value) },
  { label: '班级排名', value: classRankText.value }
])

const identityFields = computed(() => [
  { label: '学号', value: displayProfile.value.studentNo },
  { label: '学院', value: displayProfile.value.college },
  { label: '班级', value: displayProfile.value.className },
  { label: '专业', value: displayProfile.value.major }
])

const contactFields = computed(() => [
  { label: '邮箱', value: displayProfile.value.email },
  { label: '电话', value: displayProfile.value.phone }
])

/** 技能条按分数降序，最后一名标成短板：同一个色相靠长度区分强弱，
    比原来五条各用一个语义色（彩虹）更容易读出差距 */
const rankedSkills = computed(() => {
  const sorted = [...learningProfile.value.skills].sort((a, b) => b.score - a.score)
  return sorted.map((skill, index) => ({
    name: skill.name,
    score: skill.score,
    isWeakest: hasProfileSignal.value && index === sorted.length - 1
  }))
})

const recentTrainingCards = computed(() => {
  if (userTrainingSessions.value.length) {
    return userTrainingSessions.value.slice(0, 3).map((session, index) => ({
      id: session.training_session_id,
      title: index === 0 ? '最近一次专项训练' : `历史训练 ${index + 1}`,
      time: session.created_at ? session.created_at.replace('T', ' ').slice(0, 16) : '近期生成',
      desc: `共生成 ${session.question_count || 0} 题，已完成 ${session.attempt_count || 0} 次作答，训练结果会直接回流到画像评估。`
    }))
  }

  return [
    {
      id: 'prep-1',
      title: currentProfileSnapshotId.value ? '首轮画像训练待开始' : '暂无学习记录',
      time: currentProfileSnapshotId.value ? '随时可发起' : '--',
      desc: currentProfileSnapshotId.value
        ? '系统已根据当前画像准备好训练路径，点击“开始练习”即可生成第一轮个性化题目。'
        : EMPTY_PROFILE_MESSAGE
    }
  ]
})

const recentTrainingSummary = computed(() => {
  if (!userTrainingSessions.value.length) {
    return currentProfileSnapshotId.value
      ? '还没有个性化训练记录，系统会根据最新画像直接生成第一轮针对性训练。'
      : EMPTY_PROFILE_MESSAGE
  }
  const latest = userTrainingSessions.value[0]
  const createdAt = latest.created_at ? new Date(latest.created_at).toLocaleString() : '刚刚'
  return `最近一次训练生成于 ${createdAt}，累计训练 ${userTrainingSessions.value.length} 次。`
})

function getProfileSummaryValue(key: string) {
  const summary = latestProfile.value?.profile_summary_json
  if (!summary || typeof summary !== 'object') return undefined
  return (summary as Record<string, unknown>)[key]
}

function recommendationTypeLabel(type: ProfileRecommendationItem['type']) {
  switch (type) {
    case 'COURSE':
      return '课程'
    case 'MODULE':
      return '模块'
    case 'LAB':
      return '实验'
    case 'QUESTION':
      return '题目'
    default:
      return '通用建议'
  }
}

function recommendationActionHint(item: ProfileRecommendationItem) {
  if (item.moduleId || item.courseId) {
    return ''
  }
  return '暂无可跳转资源'
}

const profileRecommendations = computed<ProfileRecommendationCard[]>(() => {
  const rawRecommendations = getProfileSummaryValue('recommendations')
  if (!Array.isArray(rawRecommendations)) return []

  return rawRecommendations
    .filter((item): item is ProfileRecommendationItem => Boolean(item && typeof item === 'object'))
    .map((item) => {
      const score = Number(item.score || 0)
      const priorityLabel = item.priority === 'high' ? '高优先级' : '建议跟进'
      const difficulty = typeof item.difficulty === 'number' ? item.difficulty : null
      return {
        id: item.id,
        title: item.title,
        dimension: item.dimension,
        dimensionName: item.dimension_name || item.dimension,
        score,
        scoreText: Number.isFinite(score) ? score.toFixed(2) : '--',
        resourceType: item.type,
        resourceTypeLabel: recommendationTypeLabel(item.type),
        difficulty,
        difficultyText: difficulty ? `难度 ${difficulty}` : '难度未知',
        priorityLabel,
        priorityClass: item.priority === 'high' ? 'badge-error' : 'badge-warning',
        reason: item.reason,
        action: item.action || item.actionText,
        actionText: item.actionText || '开始训练',
        actionDisabled: !(item.moduleId || item.courseId),
        actionHint: recommendationActionHint(item),
        courseId: item.courseId,
        moduleId: item.moduleId,
        labId: item.labId,
        knowledgeTags: Array.isArray(item.knowledgeTags) ? item.knowledgeTags.filter((tag): tag is string => Boolean(tag)) : [],
        tags: Array.isArray(item.tags) ? item.tags.filter((tag): tag is string => Boolean(tag)) : []
      }
    })
})

const profileAnalysisDimensions = computed<AnalysisDimensionCard[]>(() => {
  const tones = [
    { borderClass: 'border-primary', iconClass: 'text-primary' },
    { borderClass: 'border-error', iconClass: 'text-error' },
    { borderClass: 'border-info', iconClass: 'text-info' },
    { borderClass: 'border-secondary', iconClass: 'text-secondary' }
  ]

  return profileRecommendations.value.map((item, index) => {
    const tone = tones[index % tones.length]
    return {
      icon: getDimensionIcon(item.dimensionName),
      label: item.dimensionName,
      desc: item.reason,
      borderClass: tone.borderClass,
      iconClass: tone.iconClass
    }
  })
})

const aiRecommendedTasks = computed(() => {
  const diagnose = trainingDiagnoseResult.value
  const tones = [
    { borderClass: 'border-primary', iconClass: 'text-primary' },
    { borderClass: 'border-error', iconClass: 'text-error' },
    { borderClass: 'border-info', iconClass: 'text-info' },
    { borderClass: 'border-secondary', iconClass: 'text-secondary' }
  ]

  const analysisDimensions: AnalysisDimensionCard[] = (diagnose?.weak_dimensions || []).map((dimension, index) => {
    const tone = tones[index % tones.length]
    return {
      icon: getDimensionIcon(dimension),
      label: dimension,
      desc: getDimensionDescription(dimension, index),
      borderClass: tone.borderClass,
      iconClass: tone.iconClass
    }
  })

  const difficulty = diagnose?.generation_constraints?.difficulty || 'medium'
  const generatedQuestions: TrainingRecommendationCard[] = (diagnose?.weak_knowledge_points || []).map((point) => ({
    id: `${point.knowledge_point_id ?? 'approx'}-${point.module_id ?? 'm'}-${point.task_id ?? 't'}-${point.name}`,
    title: point.name,
    difficulty: difficultyLabel(difficulty),
    difficultyClass: difficultyBadgeClass(difficulty),
    type: point.evidence_level === 'approximate' ? '近似诊断' : '精准诊断',
    tags: [
      point.category || '知识点',
      point.evidence_level === 'approximate' ? 'module/task 近似推断' : '画像证据',
      point.difficulty_level || '训练推荐'
    ].filter(Boolean),
    reason: point.reason,
    moduleId: point.module_id,
    taskId: point.task_id,
    source: point
  }))

  return {
    analysisDimensions,
    generatedQuestions
  }
})

function getDimensionIcon(dimension: string) {
  const iconMap: Record<string, string> = {
    知识掌握: 'fa-brain',
    知识掌握度: 'fa-brain',
    排障能力: 'fa-bug',
    自主探索: 'fa-compass',
    自主探索能力: 'fa-compass',
    AI协同: 'fa-robot',
    'AI 协作能力': 'fa-robot',
    学习投入: 'fa-fire',
    学习投入度: 'fa-fire'
  }
  return iconMap[dimension] || 'fa-chart-line'
}

function openRecommendationResource(item: ProfileRecommendationCard) {
  if (item.moduleId) {
    router.push(`/user/module/${item.moduleId}`)
    return
  }
  if (item.courseId) {
    router.push(`/user/course/${item.courseId}`)
    return
  }
}

function getRecommendationQuestionState(item: ProfileRecommendationCard) {
  return recommendationQuestionStates.value[item.id]
}

function canGenerateRecommendationQuestion(item: ProfileRecommendationCard) {
  return Boolean(item.moduleId || item.knowledgeTags.length)
}

function isGeneratingRecommendationQuestion(item: ProfileRecommendationCard) {
  return generatingRecommendationId.value === item.id
}

function createEmptyRecommendationPracticeState(patch: Partial<RecommendationQuestionState> = {}): RecommendationQuestionState {
  return {
    generatedQuestionId: '',
    question: null,
    answerVisible: false,
    teachingAnalysisVisible: false,
    studentAnswer: '',
    submittingAnswer: false,
    feedback: null,
    loading: false,
    trainingSessionId: '',
    questions: [],
    currentIndex: 0,
    answers: {},
    attempts: {},
    submittedQuestionIds: [],
    completed: false,
    summaryLoading: false,
    summary: null,
    error: '',
    submitError: '',
    doneNotice: '',
    ...patch
  }
}

function updateRecommendationQuestionState(item: ProfileRecommendationCard, patch: Partial<RecommendationQuestionState>) {
  const current = recommendationQuestionStates.value[item.id] || createEmptyRecommendationPracticeState()
  recommendationQuestionStates.value = {
    ...recommendationQuestionStates.value,
    [item.id]: {
      ...current,
      ...patch
    }
  }
}

function recommendationPracticeButtonLabel(item: ProfileRecommendationCard) {
  const state = getRecommendationQuestionState(item)
  if (isGeneratingRecommendationQuestion(item) || state?.loading) return `准备中 ${generationElapsedSeconds.value}s`
  if (state?.completed) return '查看训练报告'
  if (state?.trainingSessionId) return '继续训练'
  // 原来也叫「开始训练」，和旁边那颗跳转按钮、和上面那行「建议动作：开始训练」
  // 一模一样 —— 同一个小面板里三处同名，谁也分不清点哪个
  return '生成训练题'
}

/** 主按钮是跳去真实资源，标签按资源类型说清楚跳去哪 */
function resourceJumpLabel(item: ProfileRecommendationCard) {
  if (item.moduleId) return '去做实验'
  if (item.courseId) return '去看课程'
  return item.actionHint || '暂无可跳转资源'
}

/** 后端的 action 多数就是「开始训练」，跟按钮重复；只有写了别的内容才值得单独占一行 */
function hasDistinctAction(item: ProfileRecommendationCard) {
  const action = (item.action || '').trim()
  if (!action) return false
  return action !== item.actionText && action !== '开始训练'
}

function currentRecommendationQuestion(state: RecommendationQuestionState | undefined) {
  if (!state?.questions.length) return null
  return state.questions[state.currentIndex] || state.questions[0]
}

function isLastRecommendationQuestion(state: RecommendationQuestionState | undefined) {
  if (!state?.questions.length) return false
  return state.currentIndex >= state.questions.length - 1
}

function currentRecommendationAnswer(state: RecommendationQuestionState | undefined) {
  const question = currentRecommendationQuestion(state)
  return question ? state?.answers[question.generatedQuestionId] || '' : ''
}

function updateRecommendationStudentAnswer(item: ProfileRecommendationCard, value: string) {
  const state = getRecommendationQuestionState(item)
  const question = currentRecommendationQuestion(state)
  if (!state || !question || question.submitted) return
  updateRecommendationQuestionState(item, {
    answers: {
      ...state.answers,
      [question.generatedQuestionId]: value
    },
    submitError: ''
  })
}

function goToNextRecommendationQuestion(item: ProfileRecommendationCard) {
  const state = getRecommendationQuestionState(item)
  if (!state) return
  const nextIndex = Math.min(state.currentIndex + 1, Math.max(state.questions.length - 1, 0))
  updateRecommendationQuestionState(item, {
    currentIndex: nextIndex,
    submitError: ''
  })
}

function toggleSummaryQuestion(item: ProfileRecommendationCard, generatedQuestionId: string) {
  const state = getRecommendationQuestionState(item)
  if (!state) return
  updateRecommendationQuestionState(item, {
    questions: state.questions.map((question) =>
      question.generatedQuestionId === generatedQuestionId
        ? { ...question, expanded: !question.expanded }
        : question
    )
  })
}

function backendErrorCode(error: unknown) {
  const response = asRecord(asRecord(error)?.response)
  const data = asRecord(response?.data)
  const detail = asRecord(data?.detail)
  const code = detail?.code
  return typeof code === 'string' ? code : ''
}

function isRequestTimeout(error: unknown) {
  const record = asRecord(error)
  const code = record?.code
  const message = record?.message
  return code === 'ECONNABORTED' || (typeof message === 'string' && message.toLowerCase().includes('timeout'))
}

function stopGenerationElapsedTimer() {
  if (generationElapsedTimer !== null) {
    clearInterval(generationElapsedTimer)
    generationElapsedTimer = null
  }
}

function startGenerationElapsedTimer() {
  stopGenerationElapsedTimer()
  generationElapsedSeconds.value = 0
  generationElapsedTimer = setInterval(() => {
    generationElapsedSeconds.value += 1
  }, 1000)
}

function toggleRecommendationAnswer(item: ProfileRecommendationCard) {
  const current = getRecommendationQuestionState(item)
  if (!current) return
  updateRecommendationQuestionState(item, {
    answerVisible: !current.answerVisible
  })
}

function toggleRecommendationTeachingAnalysis(item: ProfileRecommendationCard) {
  const current = getRecommendationQuestionState(item)
  if (!current) return
  updateRecommendationQuestionState(item, {
    teachingAnalysisVisible: !current.teachingAnalysisVisible
  })
}

function hasRecommendationTeachingAnalysis(question: TrainingSingleQuestion | null | undefined) {
  if (!question) return false
  return Boolean(
    question.teachingObjective ||
    question.expectedSkill ||
    question.difficultyReason ||
    question.commonMistakes?.length ||
    question.gradingRubric?.length ||
    typeof question.qualityScore === 'number' ||
    question.qualitySummary ||
    question.qualityFlags?.length
  )
}

function trainingQuestionErrorMessage(error: unknown) {
  return trainingGenerationErrorMessage(backendErrorCode(error), isRequestTimeout(error))
}

async function generateQuestionForRecommendation(item: ProfileRecommendationCard) {
  if (generatingRecommendationId.value) return

  const userId = currentUserId.value
  if (!userId) {
    showToast('请先登录')
    return
  }

  if (!canGenerateRecommendationQuestion(item)) {
    const message = '当前推荐缺少足够知识库上下文，暂不能生成训练题。'
    updateRecommendationQuestionState(item, createEmptyRecommendationPracticeState({ error: message }))
    showToast(message)
    return
  }

  generatingRecommendationId.value = item.id
  startGenerationElapsedTimer()
  updateRecommendationQuestionState(item, createEmptyRecommendationPracticeState({ loading: true }))

  try {
    const response = await generateTrainingQuestionSet({
      userId,
      dimension: item.dimension,
      recommendationId: item.id,
      moduleId: item.moduleId,
      courseId: item.courseId,
      knowledgeTags: item.knowledgeTags,
      difficulty: item.difficulty || 2,
      questionType: 'SHORT_ANSWER',
      count: RECOMMENDATION_PRACTICE_COUNT,
      source: 'student_profile_snapshot'
    })

    updateRecommendationQuestionState(item, {
      loading: false,
      trainingSessionId: response.trainingSessionId,
      questions: response.questions.map((question) => ({
        ...question,
        submitted: false,
        submitting: false,
        score: null,
        level: '',
        briefFeedback: '',
        expanded: false
      })),
      currentIndex: 0,
      answers: {},
      attempts: {},
      submittedQuestionIds: [],
      completed: false,
      summaryLoading: false,
      summary: null,
      error: '',
      submitError: '',
      doneNotice: ''
    })
    showToast('训练题已准备好')
  } catch (error) {
    const message = trainingQuestionErrorMessage(error)
    updateRecommendationQuestionState(item, createEmptyRecommendationPracticeState({ error: message }))
    showToast(message)
  } finally {
    stopGenerationElapsedTimer()
    if (generatingRecommendationId.value === item.id) {
      generatingRecommendationId.value = ''
    }
  }
}

function generatedAnswerErrorMessage(error: unknown) {
  switch (backendErrorCode(error)) {
    case 'EMPTY_ANSWER':
      return '请输入你的答案。'
    case 'ANSWER_TOO_SHORT':
      return '答案太短，请至少写出一个完整判断或理由。'
    case 'GENERATED_QUESTION_NOT_FOUND':
      return '训练题不存在，请重新生成。'
    case 'UNSUPPORTED_QUESTION_TYPE':
      return '当前题型暂不支持自动评分。'
    default:
      return '答案提交失败，请稍后重试。'
  }
}

function feedbackLevelLabel(level?: string) {
  switch (level) {
    case 'EXCELLENT':
      return '优秀'
    case 'GOOD':
      return '良好'
    case 'PARTIAL':
      return '部分掌握'
    case 'NEEDS_REVIEW':
      return '需要复习'
    default:
      return level || '待评估'
  }
}

function feedbackLevelClass(level?: string) {
  switch (level) {
    case 'EXCELLENT':
      return 'badge-success'
    case 'GOOD':
      return 'badge-info'
    case 'PARTIAL':
      return 'badge-warning'
    default:
      return 'badge-error'
  }
}

async function submitRecommendationAnswer(item: ProfileRecommendationCard) {
  const state = getRecommendationQuestionState(item)
  const question = currentRecommendationQuestion(state)
  const userId = currentUserId.value
  if (!state || !question || question.submitting || question.submitted) return
  if (!userId) {
    showToast('请先登录')
    return
  }
  const answer = (state.answers[question.generatedQuestionId] || '').trim()
  if (!answer) {
    updateRecommendationQuestionState(item, { submitError: '请输入你的答案。' })
    return
  }

  updateRecommendationQuestionState(item, {
    questions: state.questions.map((itemQuestion) =>
      itemQuestion.generatedQuestionId === question.generatedQuestionId
        ? { ...itemQuestion, submitting: true }
        : itemQuestion
    ),
    submitError: ''
  })

  try {
    const response = await submitGeneratedQuestionAnswer(question.generatedQuestionId, {
      userId,
      answer,
      source: 'user_profile_recommendation'
    })
    const latest = getRecommendationQuestionState(item) || state
    const submittedIds = latest.submittedQuestionIds.includes(question.generatedQuestionId)
      ? latest.submittedQuestionIds
      : [...latest.submittedQuestionIds, question.generatedQuestionId]
    const completed = submittedIds.length >= latest.questions.length
    updateRecommendationQuestionState(item, {
      questions: latest.questions.map((itemQuestion) =>
        itemQuestion.generatedQuestionId === question.generatedQuestionId
          ? {
              ...itemQuestion,
              submitting: false,
              submitted: true,
              score: response.correctnessScore,
              level: response.level,
              briefFeedback: response.feedback
            }
          : itemQuestion
      ),
      attempts: {
        ...latest.attempts,
        [question.generatedQuestionId]: response
      },
      submittedQuestionIds: submittedIds,
      completed,
      submitError: '',
      doneNotice: completed ? '全部题目已提交，可以查看训练报告。' : ''
    })
    showToast(completed ? '本轮训练已完成' : '本题已提交')
  } catch (error) {
    const message = generatedAnswerErrorMessage(error)
    const latest = getRecommendationQuestionState(item) || state
    updateRecommendationQuestionState(item, {
      questions: latest.questions.map((itemQuestion) =>
        itemQuestion.generatedQuestionId === question.generatedQuestionId
          ? { ...itemQuestion, submitting: false }
          : itemQuestion
      ),
      submitError: message
    })
    showToast(message)
  }
}

async function loadRecommendationTrainingSummary(item: ProfileRecommendationCard) {
  const state = getRecommendationQuestionState(item)
  const userId = currentUserId.value
  if (!state?.trainingSessionId || !userId || state.summaryLoading) return
  updateRecommendationQuestionState(item, {
    summaryLoading: true,
    submitError: ''
  })
  try {
    const summary = await getTrainingSessionSummary(state.trainingSessionId, userId)
    updateRecommendationQuestionState(item, {
      summary,
      summaryLoading: false,
      completed: summary.completed,
      doneNotice: summary.completed ? '训练完成，画像已更新。' : ''
    })
    if (summary.completed) {
      await refreshProfileAfterTrainingSubmit(userId)
      showToast('训练完成，画像已更新')
    }
  } catch (error) {
    const message = extractErrorMessage(error, '训练报告加载失败，请稍后重试。')
    updateRecommendationQuestionState(item, {
      summaryLoading: false,
      submitError: message
    })
    showToast(message)
  }
}

async function handleRecommendationPracticeAction(item: ProfileRecommendationCard) {
  const state = getRecommendationQuestionState(item)
  if (!state?.trainingSessionId) {
    await generateQuestionForRecommendation(item)
    return
  }
  if (state.completed) {
    await loadRecommendationTrainingSummary(item)
    return
  }
  const nextIndex = state.questions.findIndex((question) => !question.submitted)
  updateRecommendationQuestionState(item, {
    currentIndex: nextIndex >= 0 ? nextIndex : state.currentIndex
  })
}

function getDimensionDescription(dimension: string, index: number) {
  const diagnose = trainingDiagnoseResult.value
  const point = diagnose?.weak_knowledge_points?.[index]
  const evidence = diagnose?.recent_evidence
  const aiTopics = evidence?.recent_ai_topics?.slice(0, 2).join('、')
  const errors = evidence?.recent_errors?.slice(0, 2).join('、')
  const failedTaskCount = evidence?.recent_failed_tasks?.length || 0

  if (dimension === '知识掌握' && point) {
    return `当前重点薄弱知识点为「${point.name}」，${point.reason}`
  }
  if (dimension === '自主探索' && aiTopics) {
    return `近期 AI 求助主题集中在 ${aiTopics}，建议通过针对性练习逐步摆脱卡点。`
  }
  if (dimension === '学习投入') {
    return failedTaskCount > 0 ? `近期存在 ${failedTaskCount} 个失败任务记录，训练结果会直接回流到投入度画像。` : '近期训练数据偏少，可通过专项练习补足画像证据。'
  }
  if (dimension === 'AI协同' && aiTopics) {
    return `当前协同热点集中在 ${aiTopics}，系统会继续围绕这些主题出题。`
  }
  if (dimension === '排障能力' && errors) {
    return `近期错误摘要包括 ${errors}，训练题会优先覆盖相近错误模式。`
  }
  return point?.reason || '系统根据画像、做题与实验行为综合诊断出了这一薄弱维度。'
}

function difficultyLabel(level?: string | null) {
  switch (level) {
    case 'hard':
      return '困难'
    case 'easy':
      return '简单'
    default:
      return '中等'
  }
}

function difficultyBadgeClass(level?: string | null) {
  switch (level) {
    case 'hard':
      return 'badge-error'
    case 'easy':
      return 'badge-success'
    default:
      return 'badge-warning'
  }
}

function questionTypeLabel(type: string) {
  switch (type) {
    case 'single_choice':
      return '单选题'
    case 'fill_blank':
      return '填空题'
    case 'short_answer':
      return '简答题'
    default:
      return type
  }
}

function extractErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

async function fetchDashboardData(userId: number) {
  if (!userId) return
  isLoadingDashboard.value = true
  dashboardError.value = ''
  try {
    const dashboard = await getProfileDashboard(userId)
    if (hasMeaningfulDashboardData(dashboard)) {
      userStats.value = dashboard.userStats || userStats.value
      learningProfile.value = dashboard.learningProfile || learningProfile.value
      solveRecords.value = dashboard.solveRecords || []
    } else {
      userStats.value = {
        completedCourses: 0,
        totalScore: 0,
        ranking: 0,
        activeStreak: 0
      }
      learningProfile.value = {
        skills: EMPTY_SKILLS.map((skill) => ({ ...skill })),
        tags: [],
        recentFocus: '',
        comprehensiveScore: 0,
        evaluation: '暂无学习记录'
      }
      solveRecords.value = []
      dashboardError.value = EMPTY_PROFILE_MESSAGE
    }
    dashboardLoaded.value = true
  } catch (error) {
    console.error('获取画像面板数据失败:', error)
    userStats.value = {
      completedCourses: 0,
      totalScore: 0,
      ranking: 0,
      activeStreak: 0
    }
    learningProfile.value = {
      skills: EMPTY_SKILLS.map((skill) => ({ ...skill })),
      tags: [],
      recentFocus: '',
      comprehensiveScore: 0,
      evaluation: '暂无学习记录'
      }
    solveRecords.value = []
    dashboardError.value = PROFILE_LOAD_ERROR_MESSAGE
    dashboardLoaded.value = true
  } finally {
    isLoadingDashboard.value = false
  }
}

async function fetchLatestProfileData(userId: number) {
  if (!userId) return null
  try {
    const latest = await getProfileLatest(userId)
    if (hasMeaningfulLatestProfile(latest)) {
      pageNotice.value = ''
      latestProfile.value = latest
      return latest
    }
    latestProfile.value = null
    return null
  } catch (error) {
    console.error('获取最新画像失败:', error)
    pageNotice.value = PROFILE_LOAD_ERROR_MESSAGE
    latestProfile.value = null
    return null
  }
}

async function fetchCapabilityGrowth(userId: number) {
  if (!userId) return null
  capabilityGrowthLoading.value = true
  capabilityGrowthError.value = ''
  try {
    capabilityGrowth.value = await getStudentCapabilityGrowth(userId)
    return capabilityGrowth.value
  } catch (error) {
    console.error('获取能力成长数据失败:', error)
    capabilityGrowth.value = null
    capabilityGrowthError.value = extractErrorMessage(error, '能力成长数据加载失败，请稍后重试。')
    return null
  } finally {
    capabilityGrowthLoading.value = false
  }
}

async function fetchUserTrainingSessionsData(userId: number) {
  if (!userId) return []
  try {
    const response = await getUserTrainingSessions(userId)
    userTrainingSessions.value = response.sessions?.length ? response.sessions : []
    return userTrainingSessions.value
  } catch (error) {
    console.error('获取训练会话失败:', error)
    userTrainingSessions.value = []
    return userTrainingSessions.value
  }
}

async function fetchTrainingDiagnosis(userId: number) {
  if (!userId) return null
  diagnosing.value = true
  diagnoseError.value = ''
  try {
    const response = await diagnoseTraining({
      user_id: userId,
      class_id: currentClassId.value,
      course_id: currentCourseId.value,
      top_k: 3,
      question_count: 5
    })
    trainingDiagnoseResult.value = response
    return response
  } catch (error) {
    console.error('训练诊断失败:', error)
    diagnoseError.value = '当前账号暂无训练诊断数据。'
    trainingDiagnoseResult.value = createEmptyTrainingDiagnose(userId, currentClassId.value || 0, currentCourseId.value || 0)
    return trainingDiagnoseResult.value
  } finally {
    diagnosing.value = false
  }
}

async function refreshTrainingPanelData(userId: number) {
  await Promise.allSettled([
    fetchLatestProfileData(userId),
    fetchUserTrainingSessionsData(userId)
  ])
  await fetchTrainingDiagnosis(userId)
}

async function refreshProfileAfterTrainingSubmit(userId: number) {
  refreshingProfileAfterSubmit.value = true
  profileRefreshError.value = ''
  try {
    await Promise.allSettled([
      fetchDashboardData(userId),
      fetchLatestProfileData(userId),
      fetchCapabilityGrowth(userId)
    ])
    await fetchTrainingDiagnosis(userId)
  } catch (error) {
    console.error('训练后刷新画像失败:', error)
    profileRefreshError.value = extractErrorMessage(error, '训练已提交，但画像刷新暂时失败。')
  } finally {
    refreshingProfileAfterSubmit.value = false
  }
}

function buildCourseContext(points: WeakKnowledgePoint[]) {
  const grouped = new Map<number | string, { module_id?: number | null; module_name?: string | null; knowledge_snippets: string[] }>()

  for (const point of points) {
    const key = point.module_id ?? point.knowledge_point_id ?? point.name
    const item = grouped.get(key) || {
      module_id: point.module_id ?? null,
      module_name: point.module_id ? `模块 ${point.module_id}` : learningProfile.value.recentFocus || '画像推荐模块',
      knowledge_snippets: []
    }

    item.knowledge_snippets.push(point.name)
    if (point.description) item.knowledge_snippets.push(point.description)
    item.knowledge_snippets.push(point.reason)
    if (learningProfile.value.recentFocus) item.knowledge_snippets.push(`近期关注：${learningProfile.value.recentFocus}`)

    grouped.set(key, item)
  }

  return Array.from(grouped.values()).map((item) => ({
    ...item,
    knowledge_snippets: Array.from(new Set(item.knowledge_snippets)).slice(0, 5)
  }))
}

function buildTrainingQuestionState(question: GeneratedTrainingQuestion): TrainingQuestionViewModel {
  return {
    ...question,
    options: question.options || [],
    scoring_rubric: question.scoring_rubric || [],
    currentAnswer: '',
    submitting: false,
    submitted: false,
    isCorrect: null,
    score: null,
    submitError: '',
    startedAt: Date.now(),
    costTime: null,
    explanationVisible: false
  }
}

async function hydrateTrainingQuestions(trainingSessionId: string) {
  const response = await getTrainingQuestions(trainingSessionId)
  trainingQuestions.value = (response.questions || []).map(buildTrainingQuestionState)
}

async function openTeacherAssignmentSession(trainingSessionId: string) {
  if (!trainingSessionId) return
  try {
    activeTrainingSessionId.value = trainingSessionId
    await hydrateTrainingQuestions(trainingSessionId)
    showTrainingView.value = true
    await nextTick()
    // 页面真正的滚动容器是 User 布局里的 overflow-y-auto div（不是 window），
    // 所以这里用 scrollIntoView 让浏览器自动定位最近的可滚动祖先并回滚到顶部
    pageRootRef.value?.scrollIntoView({ block: 'start', behavior: 'auto' })
  } catch (error) {
    showToast(extractErrorMessage(error, '教师布置的训练加载失败，请稍后重试。'))
  }
}

function generateRequestId() {
  return `training-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function getSingleChoiceValue(option: string, index: number) {
  const match = option.match(/^\s*([A-Z])[\.\u3001:：)]/)
  if (match?.[1]) {
    return match[1]
  }
  return String.fromCharCode(65 + index)
}

function normalizeAnswer(question: TrainingQuestionViewModel) {
  const answer = question.currentAnswer.trim()
  if (question.question_type === 'single_choice') {
    return answer.toUpperCase()
  }
  return answer
}

function validateAnswer(question: TrainingQuestionViewModel) {
  const answer = normalizeAnswer(question)
  if (question.question_type === 'single_choice' && !answer) {
    return '请选择一个选项后再提交。'
  }
  if (question.question_type === 'fill_blank' && !answer) {
    return '填空题答案不能为空。'
  }
  if (question.question_type === 'short_answer' && answer.length < 10) {
    return '简答题至少输入 10 个字符。'
  }
  return ''
}

function hasExplanationContent(question: TrainingQuestionViewModel) {
  return Boolean(
    question.explanation ||
    question.reference_answer ||
    question.standard_answer ||
    (question.scoring_rubric && question.scoring_rubric.length)
  )
}

function toggleExplanation(question: TrainingQuestionViewModel) {
  question.explanationVisible = !question.explanationVisible
}

async function startTraining(target?: WeakKnowledgePoint) {
  const userId = currentUserId.value
  if (!userId) {
    showToast('请先登录后再开始训练')
    return
  }

  generateError.value = ''
  generatingQuestions.value = true

  try {
    let diagnose = trainingDiagnoseResult.value
    if (!diagnose) {
      diagnose = await fetchTrainingDiagnosis(userId)
    }
    if (!diagnose) {
      throw new Error('当前还没有可用的训练诊断结果。')
    }

    const weakPoints = target ? [target] : diagnose.weak_knowledge_points
    if (!weakPoints.length) {
      throw new Error('当前没有可训练的薄弱知识点，请先完成课程学习后再试。')
    }

    const response = await generateTrainingQuestions({
      user_id: userId,
      class_id: currentClassId.value,
      course_id: currentCourseId.value,
      profile_snapshot_id: currentProfileSnapshotId.value,
      dimension_scores: diagnose.dimension_scores,
      weak_dimensions: diagnose.weak_dimensions,
      weak_knowledge_points: weakPoints,
      recent_focus: diagnose.recent_focus,
      tags: diagnose.tags,
      recent_evidence: diagnose.recent_evidence,
      question_types: ['single_choice', 'fill_blank', 'short_answer'],
      difficulty: diagnose.generation_constraints?.difficulty || 'medium',
      question_count: diagnose.generation_constraints?.question_count || 5,
      course_context: buildCourseContext(weakPoints)
    })

    activeTrainingSessionId.value = response.training_session_id
    trainingQuestions.value = (response.questions || []).map(buildTrainingQuestionState)

    if (response.training_session_id) {
      try {
        await hydrateTrainingQuestions(response.training_session_id)
      } catch (error) {
        console.warn('训练题列表回查失败，使用生成响应中的题目:', error)
      }
    }

    showTrainingView.value = true
    await nextTick()
    // 页面真正的滚动容器是 User 布局里的 overflow-y-auto div（不是 window），
    // 所以这里用 scrollIntoView 让浏览器自动定位最近的可滚动祖先并回滚到顶部
    pageRootRef.value?.scrollIntoView({ block: 'start', behavior: 'auto' })
  } catch (error) {
    console.error('生成训练题失败:', error)
    generateError.value = extractErrorMessage(error, '出题失败，请稍后再试。')
    showToast(generateError.value)
  } finally {
    generatingQuestions.value = false
  }
}

function exitTraining() {
  showTrainingView.value = false
}

async function submitQuestion(question: TrainingQuestionViewModel) {
  if (question.submitting || question.submitted) {
    return
  }

  question.submitError = ''
  const validationMessage = validateAnswer(question)
  if (validationMessage) {
    question.submitError = validationMessage
    return
  }

  question.submitting = true

  try {
    const costTime = Math.max(1, Math.round((Date.now() - question.startedAt) / 1000))
    const response = await submitTrainingAnswer({
      user_id: currentUserId.value,
      class_id: currentClassId.value,
      course_id: currentCourseId.value,
      module_id: question.module_id ?? null,
      task_id: question.task_id ?? null,
      training_session_id: activeTrainingSessionId.value,
      question_id: question.question_id,
      question_uid: question.question_id,
      question_type: question.question_type,
      answer: normalizeAnswer(question),
      knowledge_point_id: question.knowledge_point_id ?? null,
      question_score: 10,
      cost_time: costTime,
      request_id: generateRequestId(),
      auto_rebuild: true
    })

    question.submitted = true
    question.isCorrect = response.is_correct
    question.score = response.score
    question.costTime = costTime
    question.explanationVisible = true

    if (response.profile_rebuild_triggered) {
      await refreshProfileAfterTrainingSubmit(currentUserId.value)
    }

    showToast(response.message || '训练题提交成功')
  } catch (error) {
    console.error('提交训练题失败:', error)
    question.submitError = extractErrorMessage(error, '提交失败，请稍后再试。')
  } finally {
    question.submitting = false
  }
}

// ---- 区块锚点导航 ----
// 这一页有六个区块、纵向大概六屏，没有导航只能靠滚轮找
const SECTIONS = [
  { id: 'profile-portrait', label: '学习画像' },
  { id: 'profile-growth', label: '能力成长' },
  { id: 'profile-assignments', label: '老师布置' },
  { id: 'profile-training', label: '强化练习' },
  { id: 'profile-review', label: '知识点复习' },
  { id: 'profile-history', label: '解题记录' }
] as const

const activeSection = ref<string>(SECTIONS[0].id)
let sectionObserver: IntersectionObserver | null = null
let scrollHost: HTMLElement | null = null

function scrollToSection(id: string) {
  // 真正滚动的是 User 布局里的 overflow-y-auto 容器而不是 window，
  // scrollIntoView 会自己找到最近的可滚动祖先
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function findScrollHost(from: HTMLElement | null): HTMLElement | null {
  let node = from?.parentElement ?? null
  while (node) {
    const overflowY = getComputedStyle(node).overflowY
    if (overflowY === 'auto' || overflowY === 'scroll') return node
    node = node.parentElement
  }
  return null
}

/** 最后一段贴着页面底部，永远滚不到判定线上方，靠「是否到底」单独点亮 */
function handleHostScroll() {
  if (!scrollHost) return
  const atBottom = scrollHost.scrollTop + scrollHost.clientHeight >= scrollHost.scrollHeight - 4
  if (atBottom) activeSection.value = SECTIONS[SECTIONS.length - 1].id
}

function disconnectSectionObserver() {
  sectionObserver?.disconnect()
  sectionObserver = null
  scrollHost?.removeEventListener('scroll', handleHostScroll)
  scrollHost = null
}

function observeSections() {
  disconnectSectionObserver()
  if (typeof IntersectionObserver === 'undefined') return

  // root 用默认视口就行：不管哪一层在滚动，区块相对视口的位置都是准的。
  // 上边界收 148px —— 吸顶条实测停在 96~145px（见样式里的说明），
  // 判定线正好压在它下沿；下边界收 55%，滚到哪一段就亮哪一段
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
      const id = visible[0]?.target?.id
      if (id) activeSection.value = id
    },
    { rootMargin: '-148px 0px -55% 0px', threshold: 0 }
  )

  for (const section of SECTIONS) {
    const element = document.getElementById(section.id)
    if (element) sectionObserver.observe(element)
  }

  scrollHost = findScrollHost(pageRootRef.value)
  scrollHost?.addEventListener('scroll', handleHostScroll, { passive: true })
}

const openProfileModal = () => {
  editedUser.value = { ...user.value }
  resetAvatarPicker()
  showProfileModal.value = true
}

const closeProfileModal = () => {
  showProfileModal.value = false
  isEditing.value = false
  resetAvatarPicker()
}

const startEdit = () => {
  isEditing.value = true
}

const cancelEdit = () => {
  isEditing.value = false
  editedUser.value = { ...user.value }
  resetAvatarPicker()
}

async function saveEdit() {
  isLoading.value = true
  try {
    const token = cookie.get('token')
    if (!token) {
      showToast('请先登录')
      return
    }

    const payload = { ...editedUser.value }

    // 选了新头像就先传图片服务，拿到文件名再随资料一起提交
    if (avatarFile.value) {
      avatarError.value = ''
      isUploadingAvatar.value = true
      try {
        const uploadResult = await uploadImageFile(avatarFile.value)
        const uploadedName = uploadResult.filename || uploadResult.url || ''
        if (!uploadedName) {
          avatarError.value = '头像上传失败，请稍后重试。'
          return
        }
        payload.userImage = uploadedName
      } catch (error) {
        console.error('头像上传失败:', error)
        avatarError.value = isImageServiceUnreachable(error)
          ? '图片服务（8086）没有启动，头像暂时传不了，其他资料可以照常保存。'
          : getApiErrorMessage(error, '头像上传失败，请稍后重试。')
        return
      } finally {
        isUploadingAvatar.value = false
      }
    }

    const response = await updateUserInfoByToken(payload, token)
    if (response?.data) {
      const image = response.data.userImage?.trim() || ''
      user.value = { ...response.data, userImage: image }
      editedUser.value = { ...user.value }
      syncStoredAvatar(image)
    }

    resetAvatarPicker()
    isEditing.value = false
    showProfileModal.value = false
    showToast('保存成功')
  } catch (error) {
    console.error('保存用户信息失败:', error)
    showToast('保存失败，请稍后重试')
  } finally {
    isLoading.value = false
  }
}

/** 头像变了要同步登录态缓存，否则别的页面还在用旧值 */
function syncStoredAvatar(image: string) {
  try {
    const raw = localStorage.getItem('auth_current_user')
    if (!raw) return
    const stored = JSON.parse(raw)
    stored.userImage = image
    localStorage.setItem('auth_current_user', JSON.stringify(stored))
  } catch (error) {
    console.warn('同步头像到登录态缓存失败:', error)
  }
}

async function fetchUserData() {
  isLoadingUserData.value = true
  try {
    const loginUser = getCurrentLoginUser()
    const token = cookie.get('token')
    if (!token) {
      applyEmptyProfileBundle(loginUser)
      pageNotice.value = ''
      return
    }

    const response = await getUserInfo(token)
    if (!response?.data) {
      throw new Error('未获取到用户数据')
    }

    user.value = {
      ...response.data,
      userName: response.data.userName || loginUser?.userName || loginUser?.username || '',
      userStudentNumber: response.data.userStudentNumber || loginUser?.userStudentNumber || loginUser?.studentNumber || loginUser?.studentNo || loginUser?.account || '',
      userEmail: response.data.userEmail || loginUser?.userEmail || '',
      userTel: response.data.userTel || loginUser?.userTel || loginUser?.phone || '',
      userAcademy: response.data.userAcademy || loginUser?.userAcademy || '',
      userClass: response.data.userClass || loginUser?.userClass || '',
      userImage: response.data.userImage?.trim() || ''
    }
    editedUser.value = { ...user.value }
    profileMajor.value = loginUser?.major || ''
    completedExperiments.value = 0
    learningHours.value = 0
      pageNotice.value = ''

    await Promise.allSettled([
      fetchDashboardData(user.value.userId),
      refreshTrainingPanelData(user.value.userId),
      fetchCapabilityGrowth(user.value.userId)
    ])

    if (!currentProfileSnapshotId.value && !dashboardError.value) {
      dashboardError.value = EMPTY_PROFILE_MESSAGE
    }
  } catch (error) {
    console.error('获取用户数据失败:', error)
    applyEmptyProfileBundle(getCurrentLoginUser())
    pageNotice.value = PROFILE_LOAD_ERROR_MESSAGE
  } finally {
    isLoadingUserData.value = false
  }
}

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)

  setTimeout(() => {
    fetchUserData()
  }, 300)

  void nextTick(observeSections)
})

// 训练视图会把六个区块整体换掉，回来时要重新挂观察器
watch(showTrainingView, (training) => {
  if (training) {
    disconnectSectionObserver()
    return
  }
  activeSection.value = SECTIONS[0].id
  void nextTick(observeSections)
})

onBeforeUnmount(() => {
  stopGenerationElapsedTimer()
  disconnectSectionObserver()
})
</script>

<template>
  <div ref="pageRootRef" class="profile-page pb-10">
    <!-- ===== 区块锚点条：贴在顶栏下方吸顶 =====
         -mx-8 正好抵掉布局容器的 px-8，让这条的底色横贯整个宽度 -->
    <nav v-if="!showTrainingView" class="section-nav" aria-label="页面区块导航">
      <div class="section-nav-inner">
        <div class="section-nav-who">
          <span class="section-nav-name">{{ displayProfile.userName }}</span>
          <span class="section-nav-score">
            综合能力
            <strong class="num">{{ statText(learningProfile.comprehensiveScore) }}</strong>
          </span>
        </div>
        <div class="section-nav-tabs">
          <button
            v-for="section in SECTIONS"
            :key="section.id"
            type="button"
            class="section-nav-tab"
            :class="{ 'is-active': activeSection === section.id }"
            @click="scrollToSection(section.id)"
          >
            {{ section.label }}
          </button>
        </div>
      </div>
    </nav>

    <div v-if="!showTrainingView" class="space-y-6">
      <div v-if="pageNotice" class="alert alert-warning py-3">
        <i class="fas fa-triangle-exclamation"></i>
        <span>{{ pageNotice }}</span>
      </div>

      <div class="grid gap-6 xl:grid-cols-[19.5rem_minmax(0,1fr)]">
        <!-- ============================================================
             左：身份栏。xl 以上吸顶跟随 —— 长页面滚到第五屏时，
             「我是谁、我几分」不该滚出视野
             ============================================================ -->
        <!-- top 是相对滚动容器 padding box 算的，吸顶条底边在其下方 49px，再留 1rem -->
        <aside class="min-w-0 xl:sticky xl:top-[4.0625rem] xl:self-start">
          <div class="panel reveal" :class="{ 'is-in': isLoaded }">
            <!-- 原来是 h-32 的三色渐变 + 一个 20% 不透明度的白色巨盾，
                 是整页最吵的东西。这里收成两色低饱和色带 + 极淡点阵 -->
            <div class="identity-banner">
              <span class="identity-role">学生</span>
            </div>

            <div class="px-5 pb-5">
              <div class="-mt-11 mb-4">
                <button
                  type="button"
                  class="avatar-shell"
                  aria-label="查看或编辑个人资料"
                  @click="openProfileModal"
                >
                  <img v-if="displayUserImage" :src="displayUserImage" alt="用户头像" />
                  <i v-else class="fas fa-user"></i>
                </button>
              </div>

              <h1 class="identity-name">{{ displayProfile.userName }}</h1>
              <div class="mt-2 flex flex-wrap items-center gap-2">
                <span class="badge badge-sm" :class="profileStageSummary.badgeClass">
                  {{ profileStageSummary.label }}
                </span>
                <span class="text-xs text-base-content/60">
                  更新于 {{ latestProfileComputedAt }}
                </span>
              </div>

              <!-- 主分数：窄栏里一个大号数字比一个环形进度更好读，
                   而且没数据时是「—」而不是一个看着像坏了的空环 -->
              <div class="score-block">
                <div class="score-label">综合能力评分</div>
                <div class="score-value num">
                  {{ statText(learningProfile.comprehensiveScore) }}<em>/100</em>
                </div>
                <div class="score-track">
                  <span
                    class="score-fill"
                    :style="{ width: `${Math.min(Math.max(Number(learningProfile.comprehensiveScore) || 0, 0), 100)}%` }"
                  ></span>
                </div>
                <p class="score-desc">{{ profileStageSummary.desc }}</p>
              </div>

              <div class="rail-stats">
                <div v-for="stat in railStats" :key="stat.label" class="rail-stat">
                  <div class="rail-stat-value num" :class="{ 'is-accent': stat.accent }">{{ stat.value }}</div>
                  <div class="rail-stat-label">{{ stat.label }}</div>
                </div>
              </div>
              <p class="rail-hours">累计学习 <strong class="num">{{ learningHours }}</strong> 小时</p>

              <!-- 原来七个信息都套着同样的 bg-base-200 药丸 + 图标，
                   学号和电话一样重。改成键值表，字段名压到 /55 -->
              <dl class="rail-facts">
                <div v-for="field in identityFields" :key="field.label">
                  <dt>{{ field.label }}</dt>
                  <dd>{{ field.value }}</dd>
                </div>
              </dl>
              <dl class="rail-facts rail-facts-muted">
                <div v-for="field in contactFields" :key="field.label">
                  <dt>{{ field.label }}</dt>
                  <dd>{{ field.value }}</dd>
                </div>
              </dl>

              <button type="button" class="btn btn-outline btn-sm mt-4 w-full" @click="openProfileModal">
                编辑资料
              </button>

              <div v-if="isLoadingUserData" class="rail-note">正在同步用户资料…</div>
            </div>
          </div>
        </aside>

        <!-- ===== 右：主内容 ===== -->
        <div class="min-w-0 space-y-6">
          <!-- ============================================================
               §1 学习画像
               ============================================================ -->
          <section id="profile-portrait" class="panel reveal" :class="{ 'is-in': isLoaded }" style="--d: 60ms">
            <div class="panel-head">
              <div>
                <span class="eyebrow">画像分析</span>
                <h2 class="panel-title">学习画像</h2>
              </div>
              <span v-if="currentProfileSnapshotId" class="panel-head-note">
                <span class="live-dot"></span>
                快照 已生成
              </span>
              <span v-else class="panel-head-note">快照 待生成</span>
            </div>

            <div class="panel-body">
              <div v-if="isLoadingDashboard" class="hint-line">正在同步数据库画像…</div>
              <div v-else-if="dashboardError" class="hint-line hint-line-warn">{{ dashboardError }}</div>
              <div v-else-if="!dashboardLoaded" class="hint-line">
                当前画像快照正在生成中，系统会根据最近学习与训练表现自动更新分析结果。
              </div>

              <!-- 优势 / 短板：这两张才是学生真正要看的结论 -->
              <div class="grid gap-4 sm:grid-cols-2">
                <div
                  v-for="card in profileFocusCards"
                  :key="card.title"
                  class="focus-card"
                  :class="`focus-card-${card.kind}`"
                >
                  <div class="focus-card-head">
                    <span class="focus-card-title">{{ card.title }}</span>
                    <span class="focus-card-badge">{{ card.badge }}</span>
                  </div>
                  <div class="focus-card-value">
                    <span class="focus-card-skill">{{ card.skill }}</span>
                    <span class="focus-card-score num">{{ card.scoreText }}</span>
                  </div>
                  <p class="focus-card-desc">{{ card.desc }}</p>
                </div>
              </div>

              <!-- 技能条：统一主色，靠长度和排序表达强弱；末位标短板 -->
              <div class="subsection">
                <div class="subsection-head">
                  <h3>技能掌握度</h3>
                  <span class="subsection-note">按当前得分排序 · 满分 100</span>
                </div>
                <div class="skill-list">
                  <div v-for="skill in rankedSkills" :key="skill.name" class="skill-row">
                    <span class="skill-name">
                      {{ skill.name }}
                      <span v-if="skill.isWeakest" class="skill-flag">短板</span>
                    </span>
                    <div class="skill-track">
                      <span class="skill-tick" style="left: 60%"></span>
                      <span class="skill-tick" style="left: 80%"></span>
                      <span
                        class="skill-fill"
                        :class="{ 'is-weak': skill.isWeakest }"
                        :style="{ width: `${Math.min(Math.max(Number(skill.score) || 0, 0), 100)}%` }"
                      ></span>
                    </div>
                    <span class="skill-score num" :class="{ 'is-weak': skill.isWeakest }">
                      {{ skill.score }}<em>/100</em>
                    </span>
                  </div>
                </div>
              </div>

              <div class="subsection">
                <div class="subsection-head">
                  <h3>学习标签</h3>
                </div>
                <!-- 这些标签几乎全是「XX待提升」，四个不同的语义色（warning/error/…）
                     并不携带额外信息，只是让这一行看起来像四条报警。统一成中性 chip -->
                <div class="flex flex-wrap gap-2">
                  <span v-for="(tag, index) in displayTags" :key="index" class="learn-tag">
                    {{ tag.text }}
                  </span>
                </div>
              </div>

              <div class="advice-block">
                <div class="advice-head">AI 学习建议</div>
                <p class="advice-body">{{ learningProfile.evaluation }}</p>
                <div class="advice-foot">
                  <span>近期学习重点</span>
                  <span class="badge badge-primary badge-sm">{{ learningProfile.recentFocus || '待生成' }}</span>
                </div>
              </div>
            </div>
          </section>

          <!-- ============================================================
               §2 能力成长（组件自带表头，直接挂锚点）
               ============================================================ -->
          <section id="profile-growth" class="reveal" :class="{ 'is-in': isLoaded }" style="--d: 120ms">
      <CapabilityGrowthPanel
              :data="capabilityGrowth"
              :loading="capabilityGrowthLoading"
              :error="capabilityGrowthError"
              @retry="fetchCapabilityGrowth(currentUserId)"
            />
          </section>

          <!-- ============================================================
               §3 老师布置的练习
               ============================================================ -->
          <section id="profile-assignments" class="reveal" :class="{ 'is-in': isLoaded }" style="--d: 180ms">
            <TeacherAssignments :user-id="currentUserId" @open-session="openTeacherAssignmentSession" />
          </section>

          <!-- ============================================================
               §4 强化练习
               ============================================================ -->
          <section id="profile-training" class="panel reveal" :class="{ 'is-in': isLoaded }" style="--d: 240ms">
            <div class="panel-head">
              <div>
                <span class="eyebrow">个性化训练</span>
                <h2 class="panel-title">AI 专属强化练习</h2>
              </div>
              <button
                class="btn btn-primary btn-sm"
                :disabled="generatingQuestions || diagnosing"
                @click="startTraining()"
                title="完成个性化训练后，画像分数、标签和推荐内容会自动刷新。"
              >
                <i v-if="generatingQuestions" class="fas fa-spinner fa-spin"></i>
                {{ generatingQuestions ? '正在生成题目…' : '开始练习' }}
              </button>
            </div>

            <div class="panel-body">
              <p class="panel-lede">
                系统会根据你的答题记录、实验完成情况和常见错误，生成适合当前阶段的强化练习。完成练习后，个人画像会同步更新，帮助你看到自己的进步。
              </p>
              <p class="hint-line">{{ recentTrainingSummary }}</p>

              <div class="grid gap-4 md:grid-cols-3">
                <div v-for="item in recentTrainingCards" :key="item.id" class="mini-card">
                  <div class="mini-card-title">{{ item.title }}</div>
                  <div class="mini-card-time num">{{ item.time }}</div>
                  <p class="mini-card-desc">{{ item.desc }}</p>
                </div>
              </div>

              <div v-if="diagnosing" class="alert alert-info py-3">
                <i class="fas fa-spinner fa-spin"></i>
                <span>正在分析最新画像、近期做题与实验行为…</span>
              </div>
              <div v-if="diagnoseError" class="alert alert-warning py-3">
                <i class="fas fa-triangle-exclamation"></i>
                <span>{{ diagnoseError }}</span>
              </div>
              <div v-if="generateError" class="alert alert-error py-3">
                <i class="fas fa-circle-exclamation"></i>
                <span>{{ generateError }}</span>
              </div>

              <div class="subsection">
                <div class="subsection-head">
                  <h3>学习薄弱点分析</h3>
                  <span class="subsection-note">来自画像证据与近期作答</span>
                </div>
                <!-- 维度数量是后端给的（这里 5 个），写死 4 列会剩一个孤零零的尾巴。
                     auto-fit 让列数跟着数量走，任何个数都是齐的 -->
                <div v-if="profileAnalysisDimensions.length" class="auto-grid">
                  <div
                    v-for="dimension in profileAnalysisDimensions"
                    :key="dimension.label"
                    class="dim-card"
                    :class="dimension.borderClass"
                  >
                    <i :class="['fas', dimension.icon, dimension.iconClass]"></i>
                    <div class="min-w-0">
                      <div class="dim-card-label">{{ dimension.label }}</div>
                      <p class="dim-card-desc">{{ dimension.desc }}</p>
                    </div>
                  </div>
                </div>
                <div v-else class="empty-state">
                  <i class="fas fa-chart-line"></i>
                  <div class="empty-state-title">还没拉开明显的弱项差距</div>
                  <p>系统会继续结合实验记录、作答结果和 AI 协同主题更新推荐方向。</p>
                </div>
              </div>

              <div class="subsection">
                <div class="subsection-head">
                  <h3>推荐强化任务</h3>
                  <span v-if="profileRecommendations.length" class="subsection-note num">
                    {{ profileRecommendations.length }} 项
                  </span>
                </div>
          <div v-if="profileRecommendations.length" class="space-y-4">
            <article
              v-for="recommendation in profileRecommendations"
              :key="recommendation.id"
              class="rec-card"
              :class="recommendation.priorityLabel === '高优先级' ? 'rec-card-high' : 'rec-card-normal'"
            >
              <div class="rec-main">
                <div class="rec-title-row">
                  <h4 class="rec-title">{{ recommendation.title }}</h4>
                  <span class="badge badge-sm" :class="recommendation.priorityClass">{{ recommendation.priorityLabel }}</span>
                </div>

                <!-- 维度 / 得分 / 类型 / 难度原来是四个 badge，和优先级 badge 混在一行分不出主次。
                     它们是同一层的元信息，压成一行点号分隔的小字 -->
                <div class="rec-meta">
                  <span>{{ recommendation.dimensionName }}</span>
                  <span>当前得分 <strong class="num">{{ recommendation.scoreText }}</strong></span>
                  <span>{{ recommendation.resourceTypeLabel }}</span>
                  <span>{{ recommendation.difficultyText }}</span>
                </div>

                <p class="rec-reason">
                  <strong>推荐原因</strong>{{ recommendation.reason }}
                </p>

                <div v-if="recommendation.tags.length" class="rec-tags">
                  <span v-for="tag in recommendation.tags" :key="tag">#{{ tag }}</span>
                </div>
              </div>

              <div class="rec-action">
                <div class="rec-action-label">下一步</div>
                <p v-if="hasDistinctAction(recommendation)" class="rec-action-text">{{ recommendation.action }}</p>
                <button
                  class="btn btn-primary btn-sm w-full"
                  :disabled="recommendation.actionDisabled"
                  :title="recommendation.actionHint"
                  @click="openRecommendationResource(recommendation)"
                >
                  {{ recommendation.actionDisabled ? recommendation.actionHint : resourceJumpLabel(recommendation) }}
                </button>
                <button
                  class="btn btn-outline btn-sm w-full"
                  :disabled="Boolean(generatingRecommendationId && !isGeneratingRecommendationQuestion(recommendation)) || !canGenerateRecommendationQuestion(recommendation)"
                  @click="handleRecommendationPracticeAction(recommendation)"
                >
                  <i v-if="isGeneratingRecommendationQuestion(recommendation)" class="fas fa-spinner fa-spin"></i>
                  {{ recommendationPracticeButtonLabel(recommendation) }}
                </button>
                <div
                  v-if="isGeneratingRecommendationQuestion(recommendation) || getRecommendationQuestionState(recommendation)?.loading"
                  class="rec-action-wait"
                >
                  {{ trainingWaitMessage(generationElapsedSeconds, RECOMMENDATION_PRACTICE_COUNT) }}
                </div>
              </div>

              <div v-if="getRecommendationQuestionState(recommendation)?.error" class="w-full rounded-box border border-error/20 bg-error/10 p-4 text-sm text-error">
                {{ getRecommendationQuestionState(recommendation)?.error }}
              </div>

              <div
                v-if="getRecommendationQuestionState(recommendation)?.trainingSessionId"
                class="w-full rounded-box border border-accent/20 bg-base-100/90 p-4 space-y-4"
              >
                <div class="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <div class="text-xs font-bold uppercase tracking-wider text-accent mb-1">推荐训练板块</div>
                    <h4 class="text-base font-bold text-base-content/90">{{ recommendation.title }}</h4>
                    <div class="mt-2 flex flex-wrap gap-2 text-xs">
                      <span class="badge badge-accent badge-outline">本轮训练共 {{ getRecommendationQuestionState(recommendation)?.questions.length || RECOMMENDATION_PRACTICE_COUNT }} 题</span>
                      <span class="badge badge-outline">
                        已完成 {{ getRecommendationQuestionState(recommendation)?.submittedQuestionIds.length || 0 }} / {{ getRecommendationQuestionState(recommendation)?.questions.length || RECOMMENDATION_PRACTICE_COUNT }}
                      </span>
                    </div>
                  </div>
                  <button
                    v-if="getRecommendationQuestionState(recommendation)?.completed"
                    class="btn btn-outline btn-sm"
                    :disabled="getRecommendationQuestionState(recommendation)?.summaryLoading"
                    @click="loadRecommendationTrainingSummary(recommendation)"
                  >
                    <i class="fas" :class="getRecommendationQuestionState(recommendation)?.summaryLoading ? 'fa-spinner fa-spin' : 'fa-chart-column'"></i>
                    {{ getRecommendationQuestionState(recommendation)?.summaryLoading ? '报告生成中...' : '查看训练报告' }}
                  </button>
                </div>

                <div v-if="getRecommendationQuestionState(recommendation)?.doneNotice" class="alert alert-success py-3">
                  <i class="fas fa-circle-check"></i>
                  <span>{{ getRecommendationQuestionState(recommendation)?.doneNotice }}</span>
                </div>

                <template v-if="!getRecommendationQuestionState(recommendation)?.summary">
                  <div v-if="currentRecommendationQuestion(getRecommendationQuestionState(recommendation))" class="rounded-box border border-base-300 bg-base-200/30 p-4 space-y-4">
                    <div class="flex items-start justify-between gap-3 flex-wrap">
                      <div>
                        <div class="text-sm font-semibold text-base-content/70">
                          第 {{ (getRecommendationQuestionState(recommendation)?.currentIndex || 0) + 1 }} /
                          {{ getRecommendationQuestionState(recommendation)?.questions.length || RECOMMENDATION_PRACTICE_COUNT }} 题
                        </div>
                        <h5 class="text-base font-bold mt-1">
                          {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.title }}
                        </h5>
                      </div>
                      <div class="flex flex-wrap gap-2">
                        <span class="badge badge-accent badge-outline">
                          {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.questionType }}
                        </span>
                        <span class="badge badge-outline">
                          难度 {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.difficulty }}
                        </span>
                      </div>
                    </div>

                    <p class="text-sm text-base-content/80 leading-7 whitespace-pre-wrap">
                      {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.stem }}
                    </p>

                    <div class="flex flex-wrap gap-2">
                      <span
                        v-for="tag in currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.knowledgeTags || []"
                        :key="`${recommendation.id}-set-tag-${tag}`"
                        class="text-[0.65rem] font-bold tracking-wider bg-accent/10 text-accent px-2 py-1 rounded"
                      >
                        #{{ tag }}
                      </span>
                    </div>

                    <label class="form-control">
                      <div class="label">
                        <span class="label-text font-semibold">输入你的答案</span>
                      </div>
                      <textarea
                        :value="currentRecommendationAnswer(getRecommendationQuestionState(recommendation))"
                        class="textarea textarea-bordered min-h-28 text-sm"
                        placeholder="请输入你的答案"
                        :disabled="Boolean(currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitted || currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitting)"
                        @input="updateRecommendationStudentAnswer(recommendation, ($event.target as HTMLTextAreaElement).value)"
                      ></textarea>
                    </label>

                    <div v-if="getRecommendationQuestionState(recommendation)?.submitError" class="text-sm text-error">
                      {{ getRecommendationQuestionState(recommendation)?.submitError }}
                    </div>

                    <div
                      v-if="currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitted"
                      class="rounded-box border border-success/20 bg-success/5 p-4 space-y-2"
                    >
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="font-semibold">本题已提交</span>
                        <span class="badge badge-outline">
                          得分 {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.score ?? 0 }}/100
                        </span>
                        <span class="badge" :class="feedbackLevelClass(currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.level)">
                          {{ feedbackLevelLabel(currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.level) }}
                        </span>
                      </div>
                      <div class="text-sm text-base-content/80 whitespace-pre-wrap">
                        {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.briefFeedback }}
                      </div>
                    </div>

                    <div class="flex flex-wrap gap-2">
                      <button
                        v-if="!currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitted"
                        class="btn btn-primary btn-sm"
                        :disabled="Boolean(currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitting)"
                        @click="submitRecommendationAnswer(recommendation)"
                      >
                        <i
                          class="fas"
                          :class="currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitting ? 'fa-spinner fa-spin' : 'fa-paper-plane'"
                        ></i>
                        {{ currentRecommendationQuestion(getRecommendationQuestionState(recommendation))?.submitting ? '提交中...' : '提交答案' }}
                      </button>
                      <button
                        v-else-if="!isLastRecommendationQuestion(getRecommendationQuestionState(recommendation))"
                        class="btn btn-accent btn-sm"
                        @click="goToNextRecommendationQuestion(recommendation)"
                      >
                        继续下一题
                      </button>
                      <button
                        v-else
                        class="btn btn-accent btn-sm"
                        :disabled="getRecommendationQuestionState(recommendation)?.summaryLoading"
                        @click="loadRecommendationTrainingSummary(recommendation)"
                      >
                        <i class="fas" :class="getRecommendationQuestionState(recommendation)?.summaryLoading ? 'fa-spinner fa-spin' : 'fa-chart-column'"></i>
                        {{ getRecommendationQuestionState(recommendation)?.summaryLoading ? '报告生成中...' : '查看训练报告' }}
                      </button>
                    </div>
                  </div>
                </template>

                <div v-if="getRecommendationQuestionState(recommendation)?.summary" class="rounded-box border border-primary/20 bg-primary/5 p-4 space-y-4">
                  <div class="flex items-center justify-between gap-3 flex-wrap">
                    <div>
                      <div class="text-sm font-semibold text-base-content/70">训练报告</div>
                      <div class="text-xl font-bold mt-1">
                        平均分 {{ getRecommendationQuestionState(recommendation)?.summary?.averageScore }}/100
                      </div>
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <span class="badge badge-outline">总题数 {{ getRecommendationQuestionState(recommendation)?.summary?.totalQuestions }}</span>
                      <span class="badge badge-outline">已完成 {{ getRecommendationQuestionState(recommendation)?.summary?.submittedCount }}</span>
                      <span class="badge" :class="feedbackLevelClass(getRecommendationQuestionState(recommendation)?.summary?.level)">
                        {{ feedbackLevelLabel(getRecommendationQuestionState(recommendation)?.summary?.level) }}
                      </span>
                    </div>
                  </div>

                  <div v-if="getRecommendationQuestionState(recommendation)?.summary?.summaryFeedback" class="text-sm text-base-content/80 whitespace-pre-wrap">
                    {{ getRecommendationQuestionState(recommendation)?.summary?.summaryFeedback }}
                  </div>
                  <ul v-if="getRecommendationQuestionState(recommendation)?.summary?.nextActions?.length" class="list-disc pl-5 text-sm text-base-content/75 space-y-1">
                    <li v-for="action in getRecommendationQuestionState(recommendation)?.summary?.nextActions || []" :key="`${recommendation.id}-next-${action}`">
                      {{ action }}
                    </li>
                  </ul>

                  <div class="space-y-3">
                    <div
                      v-for="(item, index) in getRecommendationQuestionState(recommendation)?.summary?.questions || []"
                      :key="item.generatedQuestionId"
                      class="rounded-box border border-base-300 bg-base-100/80"
                    >
                      <button
                        class="w-full text-left p-4 flex items-center justify-between gap-3"
                        @click="toggleSummaryQuestion(recommendation, item.generatedQuestionId)"
                      >
                        <span class="font-semibold">第 {{ index + 1 }} 题：{{ item.title }}</span>
                        <span class="flex items-center gap-2">
                          <span class="badge badge-outline">{{ item.correctnessScore ?? 0 }}/100</span>
                          <i class="fas fa-chevron-down"></i>
                        </span>
                      </button>
                      <div
                        v-if="getRecommendationQuestionState(recommendation)?.questions.find((question) => question.generatedQuestionId === item.generatedQuestionId)?.expanded"
                        class="px-4 pb-4 space-y-3 text-sm"
                      >
                        <div class="whitespace-pre-wrap text-base-content/80">{{ item.stem }}</div>
                        <div>
                          <div class="font-semibold mb-1">学生答案</div>
                          <div class="whitespace-pre-wrap text-base-content/75">{{ item.studentAnswer || '未提交' }}</div>
                        </div>
                        <div v-if="item.feedback">
                          <div class="font-semibold mb-1">反馈</div>
                          <div class="whitespace-pre-wrap text-base-content/75">{{ item.feedback }}</div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <div class="font-semibold text-success mb-1">命中项</div>
                            <ul class="list-disc pl-5 space-y-1">
                              <li v-for="hit in item.hitRubricItems" :key="`${item.generatedQuestionId}-hit-${hit.point}`">{{ hit.point }}（{{ hit.score }} 分）</li>
                              <li v-if="!item.hitRubricItems.length">暂无</li>
                            </ul>
                          </div>
                          <div>
                            <div class="font-semibold text-warning mb-1">遗漏项</div>
                            <ul class="list-disc pl-5 space-y-1">
                              <li v-for="miss in item.missedRubricItems" :key="`${item.generatedQuestionId}-miss-${miss.point}`">{{ miss.point }}（{{ miss.score }} 分）</li>
                              <li v-if="!item.missedRubricItems.length">暂无</li>
                            </ul>
                          </div>
                        </div>
                        <div>
                          <div class="font-semibold mb-1">标准答案</div>
                          <div class="whitespace-pre-wrap text-base-content/75">{{ item.standardAnswer }}</div>
                        </div>
                        <div>
                          <div class="font-semibold mb-1">题目解析</div>
                          <div class="whitespace-pre-wrap text-base-content/75">{{ item.explanation }}</div>
                        </div>
                        <div class="rounded border border-info/20 bg-info/5 p-3 space-y-2">
                          <div class="font-semibold">教学分析</div>
                          <div v-if="item.teachingObjective" class="whitespace-pre-wrap">教学目标：{{ item.teachingObjective }}</div>
                          <div v-if="item.expectedSkill" class="whitespace-pre-wrap">能力点：{{ item.expectedSkill }}</div>
                          <div v-if="item.difficultyReason" class="whitespace-pre-wrap">难度依据：{{ item.difficultyReason }}</div>
                          <div v-if="item.commonMistakes?.length">常见错误：{{ item.commonMistakes.join('；') }}</div>
                          <div v-if="item.gradingRubric?.length">
                            <div class="font-semibold mt-2">评分规则</div>
                            <ul class="list-disc pl-5 space-y-1">
                              <li v-for="rubric in item.gradingRubric" :key="`${item.generatedQuestionId}-rubric-${rubric.point}`">
                                {{ rubric.point }}（{{ rubric.score }} 分）
                              </li>
                            </ul>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div
                v-if="getRecommendationQuestionState(recommendation)?.question"
                class="w-full rounded-box border border-accent/20 bg-base-100/90 p-4 space-y-4"
              >
                <div class="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <div class="text-xs font-bold uppercase tracking-wider text-accent mb-1">AI 生成训练题</div>
                    <h4 class="text-base font-bold text-base-content/90">
                      {{ getRecommendationQuestionState(recommendation)?.question?.title }}
                    </h4>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <span class="badge badge-accent badge-outline">
                      {{ getRecommendationQuestionState(recommendation)?.question?.questionType }}
                    </span>
                    <span class="badge badge-outline">
                      难度 {{ getRecommendationQuestionState(recommendation)?.question?.difficulty }}
                    </span>
                    <span class="badge badge-ghost">
                      {{ getRecommendationQuestionState(recommendation)?.generatedQuestionId }}
                    </span>
                  </div>
                </div>

                <p class="text-sm text-base-content/80 leading-7 whitespace-pre-wrap">
                  {{ getRecommendationQuestionState(recommendation)?.question?.stem }}
                </p>

                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="tag in getRecommendationQuestionState(recommendation)?.question?.knowledgeTags || []"
                    :key="`${recommendation.id}-generated-${tag}`"
                    class="text-[0.65rem] font-bold tracking-wider bg-accent/10 text-accent px-2 py-1 rounded"
                  >
                    #{{ tag }}
                  </span>
                </div>

                <div class="rounded-box border border-base-300 bg-base-200/30 p-4 space-y-3">
                  <label class="form-control">
                    <div class="label">
                      <span class="label-text font-semibold">输入你的答案</span>
                    </div>
                    <textarea
                      :value="getRecommendationQuestionState(recommendation)?.studentAnswer || ''"
                      class="textarea textarea-bordered min-h-28 text-sm"
                      placeholder="请输入你的答案"
                      :disabled="Boolean(getRecommendationQuestionState(recommendation)?.submittingAnswer || getRecommendationQuestionState(recommendation)?.feedback)"
                      @input="updateRecommendationStudentAnswer(recommendation, ($event.target as HTMLTextAreaElement).value)"
                    ></textarea>
                  </label>

                  <div v-if="getRecommendationQuestionState(recommendation)?.submitError" class="text-sm text-error">
                    {{ getRecommendationQuestionState(recommendation)?.submitError }}
                  </div>

                  <button
                    class="btn btn-primary btn-sm"
                    :disabled="Boolean(getRecommendationQuestionState(recommendation)?.submittingAnswer || getRecommendationQuestionState(recommendation)?.feedback)"
                    @click="submitRecommendationAnswer(recommendation)"
                  >
                    <i
                      class="fas"
                      :class="getRecommendationQuestionState(recommendation)?.submittingAnswer ? 'fa-spinner fa-spin' : 'fa-paper-plane'"
                    ></i>
                    {{ getRecommendationQuestionState(recommendation)?.submittingAnswer ? '提交中...' : '提交答案' }}
                  </button>

                  <div
                    v-if="getRecommendationQuestionState(recommendation)?.feedback"
                    class="rounded-box border border-success/20 bg-success/5 p-4 space-y-3"
                  >
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="text-sm font-semibold">评分反馈</span>
                      <span class="badge badge-outline">
                        {{ getRecommendationQuestionState(recommendation)?.feedback?.correctnessScore }}/100
                      </span>
                      <span class="badge" :class="feedbackLevelClass(getRecommendationQuestionState(recommendation)?.feedback?.level)">
                        {{ feedbackLevelLabel(getRecommendationQuestionState(recommendation)?.feedback?.level) }}
                      </span>
                    </div>
                    <div class="text-sm text-base-content/80 whitespace-pre-wrap">
                      {{ getRecommendationQuestionState(recommendation)?.feedback?.feedback }}
                    </div>

                    <div v-if="getRecommendationQuestionState(recommendation)?.feedback?.hitRubricItems?.length">
                      <div class="text-sm font-semibold text-success mb-1">已命中评分点</div>
                      <ul class="list-disc pl-5 text-sm text-base-content/75 space-y-1">
                        <li
                          v-for="item in getRecommendationQuestionState(recommendation)?.feedback?.hitRubricItems || []"
                          :key="`${recommendation.id}-hit-${item.point}`"
                        >
                          {{ item.point }}（{{ item.score }} 分）
                        </li>
                      </ul>
                    </div>

                    <div v-if="getRecommendationQuestionState(recommendation)?.feedback?.missedRubricItems?.length">
                      <div class="text-sm font-semibold text-warning mb-1">待补充评分点</div>
                      <ul class="list-disc pl-5 text-sm text-base-content/75 space-y-1">
                        <li
                          v-for="item in getRecommendationQuestionState(recommendation)?.feedback?.missedRubricItems || []"
                          :key="`${recommendation.id}-miss-${item.point}`"
                        >
                          {{ item.point }}（{{ item.score }} 分）
                        </li>
                      </ul>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <div class="font-semibold text-base-content/80 mb-1">命中关键词</div>
                        <div class="text-base-content/70">
                          {{ getRecommendationQuestionState(recommendation)?.feedback?.keywordHits?.join('、') || '暂无' }}
                        </div>
                      </div>
                      <div>
                        <div class="font-semibold text-base-content/80 mb-1">遗漏关键词</div>
                        <div class="text-base-content/70">
                          {{ getRecommendationQuestionState(recommendation)?.feedback?.keywordMisses?.join('、') || '暂无' }}
                        </div>
                      </div>
                    </div>

                    <div v-if="getRecommendationQuestionState(recommendation)?.feedback?.suggestion" class="text-sm text-base-content/80 whitespace-pre-wrap">
                      <span class="font-semibold">建议：</span>{{ getRecommendationQuestionState(recommendation)?.feedback?.suggestion }}
                    </div>
                  </div>
                </div>

                <div class="flex flex-wrap gap-2">
                  <button class="btn btn-ghost btn-sm" @click="toggleRecommendationTeachingAnalysis(recommendation)">
                    <i class="fas fa-chalkboard-user"></i>
                    {{ getRecommendationQuestionState(recommendation)?.teachingAnalysisVisible ? '收起教学分析' : '查看教学分析' }}
                  </button>
                  <button class="btn btn-ghost btn-sm" @click="toggleRecommendationAnswer(recommendation)">
                    <i class="fas fa-book-open"></i>
                    {{ getRecommendationQuestionState(recommendation)?.answerVisible ? '收起答案与解析' : '查看答案与解析' }}
                  </button>
                </div>

                <div
                  v-if="getRecommendationQuestionState(recommendation)?.teachingAnalysisVisible"
                  class="rounded-box border border-info/20 bg-info/5 p-4 space-y-3 training-teaching-analysis"
                >
                  <template v-if="hasRecommendationTeachingAnalysis(getRecommendationQuestionState(recommendation)?.question)">
                    <div v-if="getRecommendationQuestionState(recommendation)?.question?.teachingObjective">
                      <div class="text-sm font-semibold text-base-content/80 mb-1">教学目标</div>
                      <div class="text-sm text-base-content/75 whitespace-pre-wrap">
                        {{ getRecommendationQuestionState(recommendation)?.question?.teachingObjective }}
                      </div>
                    </div>
                    <div v-if="getRecommendationQuestionState(recommendation)?.question?.expectedSkill">
                      <div class="text-sm font-semibold text-base-content/80 mb-1">能力点</div>
                      <div class="text-sm text-base-content/75 whitespace-pre-wrap">
                        {{ getRecommendationQuestionState(recommendation)?.question?.expectedSkill }}
                      </div>
                    </div>
                    <div v-if="getRecommendationQuestionState(recommendation)?.question?.difficultyReason">
                      <div class="text-sm font-semibold text-base-content/80 mb-1">难度依据</div>
                      <div class="text-sm text-base-content/75 whitespace-pre-wrap">
                        {{ getRecommendationQuestionState(recommendation)?.question?.difficultyReason }}
                      </div>
                    </div>
                    <div v-if="getRecommendationQuestionState(recommendation)?.question?.commonMistakes?.length">
                      <div class="text-sm font-semibold text-base-content/80 mb-1">常见错误</div>
                      <ul class="list-disc pl-5 text-sm text-base-content/75 space-y-1">
                        <li
                          v-for="mistake in getRecommendationQuestionState(recommendation)?.question?.commonMistakes || []"
                          :key="`${recommendation.id}-mistake-${mistake}`"
                        >
                          {{ mistake }}
                        </li>
                      </ul>
                    </div>
                    <div v-if="getRecommendationQuestionState(recommendation)?.question?.gradingRubric?.length">
                      <div class="text-sm font-semibold text-base-content/80 mb-1">评分规则</div>
                      <div class="space-y-2">
                        <div
                          v-for="rubric in getRecommendationQuestionState(recommendation)?.question?.gradingRubric || []"
                          :key="`${recommendation.id}-rubric-${rubric.point}`"
                          class="flex items-start justify-between gap-3 rounded border border-base-300 bg-base-100/80 px-3 py-2 text-sm"
                        >
                          <span class="text-base-content/75">{{ rubric.point }}</span>
                          <span class="font-semibold text-info whitespace-nowrap">{{ rubric.score }} 分</span>
                        </div>
                      </div>
                    </div>
                    <div
                      v-if="typeof getRecommendationQuestionState(recommendation)?.question?.qualityScore === 'number' || getRecommendationQuestionState(recommendation)?.question?.qualitySummary"
                      class="rounded border border-base-300 bg-base-100/80 px-3 py-2"
                    >
                      <div class="text-sm font-semibold text-base-content/80 mb-1">
                        质量评分
                        <span v-if="typeof getRecommendationQuestionState(recommendation)?.question?.qualityScore === 'number'" class="text-info">
                          {{ getRecommendationQuestionState(recommendation)?.question?.qualityScore }}/100
                        </span>
                      </div>
                      <div v-if="getRecommendationQuestionState(recommendation)?.question?.qualitySummary" class="text-sm text-base-content/75 whitespace-pre-wrap">
                        {{ getRecommendationQuestionState(recommendation)?.question?.qualitySummary }}
                      </div>
                    </div>
                    <div v-if="getRecommendationQuestionState(recommendation)?.question?.qualityFlags?.length" class="flex flex-wrap gap-2">
                      <span
                        v-for="flag in getRecommendationQuestionState(recommendation)?.question?.qualityFlags || []"
                        :key="`${recommendation.id}-quality-flag-${flag}`"
                        class="badge badge-warning badge-outline"
                      >
                        {{ flag }}
                      </span>
                    </div>
                  </template>
                  <div v-else class="text-sm text-base-content/60">暂无教学分析</div>
                </div>

                <div
                  v-if="getRecommendationQuestionState(recommendation)?.answerVisible"
                  class="rounded-box border border-base-300 bg-base-200/40 p-4 space-y-3 training-answer"
                >
                  <div>
                    <div class="text-sm font-semibold text-base-content/80 mb-1">标准答案</div>
                    <div class="text-sm text-base-content/75 whitespace-pre-wrap">
                      {{ getRecommendationQuestionState(recommendation)?.question?.standardAnswer }}
                    </div>
                  </div>
                  <div>
                    <div class="text-sm font-semibold text-base-content/80 mb-1">题目解析</div>
                    <div class="text-sm text-base-content/75 whitespace-pre-wrap">
                      {{ getRecommendationQuestionState(recommendation)?.question?.explanation }}
                    </div>
                  </div>
                </div>
              </div>
            </article>
          </div>
                <div v-else class="empty-state">
                  <i class="fas fa-inbox"></i>
                  <div class="empty-state-title">{{ pageNotice || EMPTY_RECOMMENDATIONS_MESSAGE }}</div>
                  <p>完成实验、提交 Flag 或和 AI 助手对话后，这里会出现针对性的强化任务。</p>
                </div>
              </div>
            </div>
          </section>

          <!-- ============================================================
               §5 知识点复习卡
               ============================================================ -->
          <section id="profile-review" class="panel reveal" :class="{ 'is-in': isLoaded }" style="--d: 300ms">
            <div class="panel-head">
              <div>
                <span class="eyebrow">知识点粒度</span>
                <h2 class="panel-title">知识点复习卡</h2>
              </div>
              <span v-if="aiRecommendedTasks.generatedQuestions.length" class="panel-head-note num">
                {{ aiRecommendedTasks.generatedQuestions.length }} 个复习点
              </span>
            </div>

            <div class="panel-body">
              <p class="panel-lede">
                这里按知识点粒度列出训练诊断给出的复习点，点「去复习」会围绕该知识点单独出题，比上方按维度推荐的强化任务更聚焦。
              </p>

              <!-- 同理，复习卡可能只有 1 张：auto-fit + 上限宽度，1 张时也不会被拉成一条 -->
              <div v-if="aiRecommendedTasks.generatedQuestions.length" class="auto-grid-cap">
                <article
                  v-for="task in aiRecommendedTasks.generatedQuestions.slice(0, 4)"
                  :key="task.id"
                  class="review-card"
                >
                  <div class="review-card-top">
                    <span class="review-card-icon"><i class="fas fa-crosshairs"></i></span>
                    <span class="review-card-type">{{ task.type }}</span>
                  </div>
                  <h3 class="review-card-title">{{ task.title }}</h3>
                  <p class="review-card-desc">{{ task.reason }}</p>
                  <div class="review-card-tags">
                    <span v-for="tag in task.tags.slice(0, 2)" :key="`${task.id}-${tag}`">{{ tag }}</span>
                  </div>
                  <button
                    class="btn btn-outline btn-sm mt-auto w-full"
                    :disabled="generatingQuestions"
                    @click="startTraining(task.source)"
                  >
                    去复习
                  </button>
                </article>
              </div>
              <div v-else class="empty-state">
                <i class="fas fa-book-open"></i>
                <div class="empty-state-title">暂无知识点级复习卡</div>
                <p>训练诊断还没定位到具体知识点，主推荐请先看上方的强化任务。</p>
              </div>
            </div>
          </section>

          <!-- ============================================================
               §6 解题记录
               ============================================================ -->
          <section id="profile-history" class="panel reveal" :class="{ 'is-in': isLoaded }" style="--d: 360ms">
            <div class="panel-head">
              <div>
                <span class="eyebrow">作答留痕</span>
                <h2 class="panel-title">解题记录</h2>
              </div>
            </div>
            <div class="panel-body">
              <p class="panel-lede">
                点击任意记录可查看真实题目、你的答案、正确答案和解析；错题可单独筛选复盘。
              </p>
              <SolveHistoryPanel :records="solveRecords" />
            </div>
          </section>
        </div>
      </div>
    </div>

    <div v-else class="space-y-6 pt-2 animate-[fadeIn_0.5s_ease-out]">
      <div class="panel">
        <div class="panel-head">
          <div class="min-w-0">
            <span class="eyebrow">专注模式</span>
            <h2 class="panel-title">强化专项训练</h2>
            <p class="mt-2 text-sm leading-6 text-base-content/65">
              逐题提交后会复用训练提交主链，并在触发画像重建后同步刷新本页数据。
            </p>
            <div v-if="activeTrainingSessionId" class="mt-2 text-xs text-base-content/50">
              Session <span class="num">{{ activeTrainingSessionId }}</span>
            </div>
          </div>
          <button class="btn btn-outline btn-sm shrink-0" @click="exitTraining">返回画像页</button>
        </div>
      </div>

      <div v-if="refreshingProfileAfterSubmit" class="alert alert-info py-3">
        <i class="fas fa-spinner fa-spin"></i>
        <span>训练结果已提交，正在刷新画像与下一轮诊断...</span>
      </div>
      <div v-if="profileRefreshError" class="alert alert-warning py-3">
        <i class="fas fa-triangle-exclamation"></i>
        <span>{{ profileRefreshError }}</span>
      </div>

      <div v-if="trainingQuestions.length" class="space-y-6">
        <div v-for="(question, index) in trainingQuestions" :key="question.question_id" class="card bg-base-100 shadow-md">
          <div class="card-body">
            <div class="flex items-start justify-between gap-4 flex-wrap">
              <div class="space-y-2">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="badge badge-primary badge-outline">第 {{ index + 1 }} 题</span>
                  <span class="badge badge-ghost">{{ questionTypeLabel(question.question_type) }}</span>
                  <span v-if="question.difficulty" class="badge" :class="difficultyBadgeClass(question.difficulty)">
                    {{ difficultyLabel(question.difficulty) }}
                  </span>
                  <span v-if="question.knowledge_point_id" class="badge badge-outline">知识点 {{ question.knowledge_point_id }}</span>
                  <span v-if="question.module_id" class="badge badge-outline">模块 {{ question.module_id }}</span>
                  <span v-if="question.task_id" class="badge badge-outline">任务 {{ question.task_id }}</span>
                </div>
                <h3 class="text-lg font-semibold">{{ question.title }}</h3>
              </div>
              <div class="text-sm text-base-content/50">建议分值：10 分</div>
            </div>

            <p class="mt-4 text-base-content/85 leading-7 whitespace-pre-wrap">{{ question.stem }}</p>

            <div v-if="question.question_type === 'single_choice'" class="mt-4 space-y-2">
              <label
                v-for="(option, optionIndex) in question.options"
                :key="`${question.question_id}-${optionIndex}`"
                class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors"
                :class="question.currentAnswer === getSingleChoiceValue(option, optionIndex) ? 'border-primary bg-primary/5' : 'border-base-200 hover:bg-base-200/50'"
              >
                <input
                  v-model="question.currentAnswer"
                  type="radio"
                  class="radio radio-primary radio-sm"
                  :name="`question-${question.question_id}`"
                  :value="getSingleChoiceValue(option, optionIndex)"
                  :disabled="question.submitted"
                />
                <span class="text-base-content">{{ option }}</span>
              </label>
            </div>

            <div v-else-if="question.question_type === 'fill_blank'" class="mt-4">
              <input
                v-model="question.currentAnswer"
                type="text"
                class="input input-bordered w-full text-base"
                placeholder="请输入你的答案"
                :disabled="question.submitted"
              />
            </div>

            <div v-else class="mt-4">
              <textarea
                v-model="question.currentAnswer"
                class="textarea textarea-bordered w-full h-32 text-base"
                placeholder="请输入你的作答内容"
                :disabled="question.submitted"
              ></textarea>
            </div>

            <div class="mt-6 flex flex-col gap-3">
              <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                <div class="flex-1">
                  <div v-if="question.submitError" class="text-sm text-error">
                    {{ question.submitError }}
                  </div>
                  <div v-if="question.submitted" class="p-3 rounded-lg border" :class="{
                    'bg-success/10 text-success border-success/20': question.isCorrect === true,
                    'bg-error/10 text-error border-error/20': question.isCorrect === false,
                    'bg-info/10 text-info border-info/20': question.isCorrect === null
                  }">
                    <div class="font-bold mb-1 flex items-center gap-2">
                      <i
                        class="fas"
                        :class="question.isCorrect === true ? 'fa-check-circle' : question.isCorrect === false ? 'fa-times-circle' : 'fa-circle-info'"
                      ></i>
                      <span>
                        {{
                          question.isCorrect === true
                            ? '回答正确'
                            : question.isCorrect === false
                              ? '回答有误'
                              : '已提交，等待参考答案对照'
                        }}
                      </span>
                    </div>
                    <div class="text-sm">
                      本题得分：{{ question.score ?? 0 }} 分
                      <span v-if="question.costTime !== null" class="ml-2">耗时：{{ question.costTime }} 秒</span>
                    </div>
                  </div>
                </div>

                <div class="flex flex-wrap gap-2">
                  <button
                    v-if="hasExplanationContent(question)"
                    class="btn btn-ghost btn-sm"
                    :disabled="!question.submitted"
                    @click="toggleExplanation(question)"
                  >
                    <i class="fas fa-book-open"></i>
                    {{ question.explanationVisible ? '收起解析' : '查看解析' }}
                  </button>
                  <button
                    class="btn btn-primary min-w-[120px]"
                    :disabled="question.submitting || question.submitted"
                    @click="submitQuestion(question)"
                  >
                    <i class="fas" :class="question.submitting ? 'fa-spinner fa-spin' : 'fa-paper-plane'"></i>
                    {{ question.submitting ? '提交中...' : question.submitted ? '已提交' : '提交答案' }}
                  </button>
                </div>
              </div>

              <div v-if="question.submitted && question.explanationVisible && hasExplanationContent(question)" class="rounded-box border border-base-300 bg-base-200/40 p-4 space-y-3 training-answer">
                <div v-if="question.explanation">
                  <div class="text-sm font-semibold text-base-content/80 mb-1">题目解析</div>
                  <div class="text-sm text-base-content/75 whitespace-pre-wrap">{{ question.explanation }}</div>
                </div>
                <div v-if="question.standard_answer">
                  <div class="text-sm font-semibold text-base-content/80 mb-1">标准答案</div>
                  <div class="text-sm text-base-content/75 whitespace-pre-wrap">{{ question.standard_answer }}</div>
                </div>
                <div v-if="question.reference_answer">
                  <div class="text-sm font-semibold text-base-content/80 mb-1">参考答案</div>
                  <div class="text-sm text-base-content/75 whitespace-pre-wrap">{{ question.reference_answer }}</div>
                </div>
                <div v-if="question.scoring_rubric.length">
                  <div class="text-sm font-semibold text-base-content/80 mb-1">评分要点</div>
                  <ul class="list-disc pl-5 text-sm text-base-content/75 space-y-1">
                    <li v-for="(rubric, rubricIndex) in question.scoring_rubric" :key="`${question.question_id}-rubric-${rubricIndex}`">
                      {{ rubric }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="card bg-base-100 shadow-md">
        <div class="card-body">
          <div class="text-base-content/60">当前训练会话还没有题目，请返回画像页重新生成。</div>
        </div>
      </div>
    </div>

    <dialog class="modal" :class="{ 'modal-open': showProfileModal }">
      <div class="modal-box w-11/12 max-w-4xl bg-base-100/95 backdrop-blur-sm">
        <h3 class="font-bold text-2xl mb-6 flex items-center gap-3">
          <i class="fas fa-user-edit text-primary"></i>
          个人基本信息
        </h3>

        <div class="form-control mb-6">
          <label class="label">
            <span class="label-text flex items-center gap-2">
              <i class="fas fa-image text-primary"></i>
              头像
            </span>
            <span v-if="!isEditing" class="label-text-alt text-base-content/50">点「编辑资料」后可更换</span>
          </label>
          <div class="flex items-center gap-4">
            <div class="w-20 h-20 rounded-full border border-base-300 bg-base-200 flex items-center justify-center overflow-hidden shrink-0">
              <img
                v-if="editingAvatarImage"
                :src="editingAvatarImage"
                alt="头像预览"
                class="w-full h-full object-cover"
              />
              <i v-else class="fas fa-user text-3xl text-base-content/30"></i>
            </div>
            <div v-if="isEditing" class="flex-1 min-w-0">
              <input
                type="file"
                accept="image/*"
                class="file-input file-input-bordered file-input-sm w-full"
                :disabled="isUploadingAvatar"
                @change="handleAvatarChange"
              />
              <div class="mt-2 flex items-center gap-3">
                <button
                  v-if="editingAvatarImage"
                  type="button"
                  class="btn btn-xs btn-ghost"
                  @click="removeAvatar"
                >
                  移除头像
                </button>
                <span class="text-xs text-base-content/50">支持 jpg / png / gif / webp，不超过 2MB</span>
              </div>
            </div>
            <div v-else class="text-sm text-base-content/50">
              {{ editingAvatarImage ? '已设置头像' : '还没有上传头像' }}
            </div>
          </div>
          <label v-if="avatarError" class="label">
            <span class="label-text-alt text-error">{{ avatarError }}</span>
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
          <div
            v-for="field in [
              { key: 'userName' as keyof User, label: '姓名', icon: 'fa-user', type: 'text' },
              { key: 'userStudentNumber' as keyof User, label: '学号', icon: 'fa-id-card', type: 'text', readonly: true },
              { key: 'userTel' as keyof User, label: '电话', icon: 'fa-phone', type: 'tel' },
              { key: 'userEmail' as keyof User, label: '邮箱', icon: 'fa-envelope', type: 'email' },
              { key: 'userAcademy' as keyof User, label: '学院', icon: 'fa-university', type: 'text' },
              { key: 'userClass' as keyof User, label: '班级', icon: 'fa-users', type: 'text' }
            ]"
            :key="field.key"
            class="form-control"
          >
            <label class="label">
              <span class="label-text flex items-center gap-2">
                <i :class="['fas', field.icon, 'text-primary']"></i>
                {{ field.label }}
              </span>
            </label>
            <input
              v-model="editedUser[field.key]"
              :type="field.type"
              class="input input-bordered bg-base-200/50 focus:bg-base-100 transition-colors shadow-sm"
              :readonly="!isEditing || field.readonly"
              :class="{ 'input-disabled bg-base-200 opacity-60': !isEditing || field.readonly }"
            />
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text flex items-center gap-2">
                <i class="fas fa-venus-mars text-primary"></i>
                性别
              </span>
            </label>
            <select
              v-model="editedUser.userGender"
              class="select select-bordered h-12 bg-base-200/50 shadow-sm text-left py-0 leading-normal"
              :disabled="!isEditing"
              :class="{ 'select-disabled bg-base-200 opacity-60': !isEditing }"
            >
              <option :value="1">男</option>
              <option :value="0">女</option>
            </select>
          </div>
        </div>

        <div class="modal-action mt-8 flex justify-end gap-3">
          <button v-if="!isEditing" class="btn btn-primary gap-2" @click="startEdit">
            <i class="fas fa-edit"></i>
            编辑资料
          </button>
          <div v-else class="flex gap-2">
            <button class="btn btn-primary" :disabled="isLoading || isUploadingAvatar" @click="saveEdit">
              <i class="fas" :class="isLoading || isUploadingAvatar ? 'fa-spinner fa-spin' : 'fa-save'"></i>
              <span>{{ isUploadingAvatar ? '上传头像中...' : isLoading ? '保存中...' : '保存' }}</span>
            </button>
            <button class="btn btn-ghost" @click="cancelEdit">取消编辑</button>
          </div>
          <button class="btn btn-outline" @click="closeProfileModal">关闭</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="closeProfileModal">
        <button>close</button>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
/* ============================================================
   个人中心版式
   ------------------------------------------------------------
   几条贯穿全页的规则：
   1) 层级用亮度和 1px 描边表达，不靠彩色 —— 暗色底上黑色阴影是看不见的；
   2) 每个区块只允许一个强调色，其余一律走 base-content 的透明度阶梯；
   3) 所有数字都用 tabular-nums，纵向对齐后才读得出大小关系；
   4) 半径统一 18px，和 CapabilityGrowthPanel 自带的 18px 对齐。
   注意页面根节点不能加 overflow-x:hidden —— overflow-x 一旦不是 visible，
   这个元素自己就变成滚动容器，里面的 position:sticky 会贴到它身上而不是视口，
   顶部锚点条和左侧身份栏就都不吸顶了。宽度溢出改用 min-w-0 解决。
   ============================================================ */
.profile-page {
  width: 100%;
  max-width: 100%;
}

.num {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}

/* ---------- 入场：整块轻微上浮，用 --d 做错峰 ---------- */
.reveal {
  opacity: 0;
  transform: translateY(0.75rem);
  transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  transition-delay: var(--d, 0ms);
}

.reveal.is-in {
  opacity: 1;
  transform: none;
}

@media (prefers-reduced-motion: reduce) {
  .reveal {
    transition: none;
    opacity: 1;
    transform: none;
  }
}

/* ============================================================
   区块锚点条
   ============================================================ */
.section-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  margin: 0 -2rem 1.5rem;
  padding: 0 2rem;
  background: oklch(var(--b3) / 0.93);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid oklch(var(--bc) / 0.09);
}

/* 锚点跳转时区块顶端会正好停在吸顶条底下，把表头挡掉，要留落点余量。
   实测：滚动容器自带 padding-top:32px，而 sticky 是贴 padding box 的，
   所以 top:0 的吸顶条实际停在视口 96px（64 顶栏 + 32 内边距）、底边 145px；
   而 scroll-margin 是从 scrollport 边缘（64px）起算的 —— 两者基准不同，
   要 6.125rem（98px）才能让区块顶边落到吸顶条下方约 17px */
.profile-page section[id^='profile-'] {
  scroll-margin-top: 6.125rem;
}

.section-nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  min-height: 3rem;
}

.section-nav-who {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  min-width: 0;
}

.section-nav-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: oklch(var(--bc));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.section-nav-score {
  flex: none;
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.6);
}

.section-nav-score strong {
  margin-left: 0.25rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: oklch(var(--bc));
}

.section-nav-tabs {
  display: flex;
  gap: 0.125rem;
  overflow-x: auto;
  scrollbar-width: none;
}

.section-nav-tabs::-webkit-scrollbar {
  display: none;
}

.section-nav-tab {
  position: relative;
  flex: none;
  padding: 0.8rem 0.7rem;
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  color: oklch(var(--bc) / 0.55);
  transition: color 0.2s ease;
}

.section-nav-tab:hover {
  color: oklch(var(--bc) / 0.85);
}

/* 当前区块用一条 2px 下划线标注，比整块染色安静得多 */
.section-nav-tab::after {
  content: '';
  position: absolute;
  inset-inline: 0.35rem;
  bottom: -1px;
  height: 2px;
  border-radius: 2px;
  background: oklch(var(--p));
  transform: scaleX(0);
  transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1);
}

.section-nav-tab.is-active {
  color: oklch(var(--bc));
  font-weight: 600;
}

.section-nav-tab.is-active::after {
  transform: scaleX(1);
}

.section-nav-tab:focus-visible {
  outline: 2px solid oklch(var(--p) / 0.6);
  outline-offset: -2px;
  border-radius: 6px;
}

/* ============================================================
   面板骨架
   ============================================================ */
.panel {
  border: 1px solid oklch(var(--bc) / 0.12);
  border-radius: 18px;
  background: oklch(var(--b1));
  overflow: hidden;
}

[data-theme='night'] .panel {
  box-shadow: 0 16px 40px -24px rgb(0 0 0 / 0.75);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.25rem;
  flex-wrap: wrap;
  padding: 1.375rem 1.5rem 1.125rem;
  border-bottom: 1px solid oklch(var(--bc) / 0.1);
}

.eyebrow {
  display: block;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  color: oklch(var(--bc) / 0.45);
}

.panel-title {
  margin-top: 0.3rem;
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: oklch(var(--bc));
}

.panel-head-note {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  flex: none;
  padding-top: 0.4rem;
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.6);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: oklch(var(--su));
  box-shadow: 0 0 0 3px oklch(var(--su) / 0.18);
}

.panel-body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1.5rem;
}

.panel-lede {
  font-size: 0.875rem;
  line-height: 1.75;
  color: oklch(var(--bc) / 0.72);
}

.hint-line {
  font-size: 0.8125rem;
  color: oklch(var(--bc) / 0.6);
}

.hint-line-warn {
  color: oklch(var(--wa));
}

/* 区块内的小标题：一条细线 + 右侧注解 */
.subsection-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.6rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid oklch(var(--bc) / 0.08);
}

.subsection-head h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: oklch(var(--bc) / 0.9);
}

.subsection-note {
  flex: none;
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.5);
}

/* 列数跟着内容数量走：写死列数时，5 个元素放进 4 列就会剩一个孤儿，
   1 个元素放进 4 列就是 3/4 的空白 */
.auto-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(13.5rem, 1fr));
}

.auto-grid-cap {
  display: grid;
  gap: 1rem;
  justify-content: start;
  grid-template-columns: repeat(auto-fit, minmax(15.5rem, 21rem));
}

.learn-tag {
  padding: 0.3rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: 999px;
  color: oklch(var(--bc) / 0.72);
  background: oklch(var(--bc) / 0.07);
  border: 1px solid oklch(var(--bc) / 0.12);
}

/* ============================================================
   左侧身份栏
   ============================================================ */
.identity-banner {
  position: relative;
  height: 5.5rem;
  background:
    radial-gradient(circle at 1px 1px, oklch(var(--bc) / 0.13) 1px, transparent 0) 0 0 / 12px 12px,
    linear-gradient(108deg, oklch(var(--p) / 0.22), oklch(var(--s) / 0.13) 58%, transparent);
  border-bottom: 1px solid oklch(var(--bc) / 0.08);
}

/* 3px 卡面色的内圈把头像「抠」出卡片，外面再补 1px 发丝线 ——
   比原来的 ring-4 ring-primary 安静，但边界更清楚 */
.avatar-shell {
  width: 5.5rem;
  height: 5.5rem;
  flex: none;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 3px solid oklch(var(--b1));
  border-radius: 9999px;
  background: oklch(var(--b2));
  box-shadow: 0 0 0 1px oklch(var(--bc) / 0.15), 0 10px 24px -12px rgb(0 0 0 / 0.55);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}

.avatar-shell:hover {
  transform: translateY(-1px);
  box-shadow: 0 0 0 1px oklch(var(--p) / 0.55), 0 12px 26px -12px rgb(0 0 0 / 0.6);
}

.avatar-shell:focus-visible {
  outline: 2px solid oklch(var(--p));
  outline-offset: 2px;
}

.avatar-shell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-shell i {
  font-size: 1.75rem;
  color: oklch(var(--bc) / 0.3);
}

.identity-role {
  position: absolute;
  top: 0.7rem;
  right: 0.8rem;
  padding: 0.2rem 0.55rem;
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 6px;
  color: oklch(var(--p));
  background: oklch(var(--p) / 0.12);
  border: 1px solid oklch(var(--p) / 0.25);
}

.identity-name {
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: oklch(var(--bc));
  overflow-wrap: anywhere;
}

/* ---------- 主分数 ---------- */
.score-block {
  margin-top: 1.125rem;
  padding: 0.9rem 1rem 1rem;
  border: 1px solid oklch(var(--bc) / 0.1);
  border-radius: 14px;
  background: oklch(var(--b2) / 0.6);
}

.score-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: oklch(var(--bc) / 0.45);
}

.score-value {
  margin-top: 0.15rem;
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.04em;
  color: oklch(var(--bc));
}

.score-value em {
  margin-left: 0.15rem;
  font-size: 0.875rem;
  font-style: normal;
  font-weight: 500;
  color: oklch(var(--bc) / 0.4);
}

.score-track {
  position: relative;
  height: 4px;
  margin-top: 0.7rem;
  border-radius: 999px;
  background: oklch(var(--bc) / 0.1);
  overflow: hidden;
}

.score-fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 999px;
  background: linear-gradient(90deg, oklch(var(--p) / 0.7), oklch(var(--p)));
  transition: width 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.score-desc {
  margin-top: 0.7rem;
  font-size: 0.75rem;
  line-height: 1.65;
  color: oklch(var(--bc) / 0.6);
}

/* ---------- 2×2 关键数字 ---------- */
.rail-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin-top: 1.125rem;
  border: 1px solid oklch(var(--bc) / 0.1);
  border-radius: 14px;
  background: oklch(var(--bc) / 0.1);
  overflow: hidden;
}

.rail-stat {
  padding: 0.7rem 0.8rem;
  background: oklch(var(--b1));
}

.rail-stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: oklch(var(--bc) / 0.9);
}

.rail-stat-value.is-accent {
  color: oklch(var(--p));
}

.rail-stat-label {
  margin-top: 0.15rem;
  font-size: 0.6875rem;
  color: oklch(var(--bc) / 0.5);
}

.rail-hours {
  margin-top: 0.6rem;
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.5);
}

.rail-hours strong {
  color: oklch(var(--bc) / 0.8);
}

/* ---------- 键值表 ---------- */
.rail-facts {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid oklch(var(--bc) / 0.08);
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.rail-facts > div {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr);
  gap: 0.75rem;
  align-items: baseline;
}

.rail-facts dt {
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.45);
}

.rail-facts dd {
  font-size: 0.8125rem;
  font-weight: 500;
  color: oklch(var(--bc) / 0.88);
  overflow-wrap: anywhere;
}

.rail-facts-muted dd {
  font-weight: 400;
  color: oklch(var(--bc) / 0.6);
}

.rail-note {
  margin-top: 0.75rem;
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.5);
}

/* ============================================================
   §1 优势 / 短板
   ============================================================ */
.focus-card {
  position: relative;
  padding: 1rem 1.1rem;
  border: 1px solid oklch(var(--bc) / 0.1);
  border-left-width: 3px;
  border-radius: 14px;
  background: oklch(var(--b2) / 0.45);
}

.focus-card-strength {
  border-left-color: oklch(var(--su));
}

.focus-card-gap {
  border-left-color: oklch(var(--wa));
}

.focus-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.focus-card-title {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: oklch(var(--bc) / 0.5);
}

.focus-card-badge {
  flex: none;
  font-size: 0.6875rem;
  color: oklch(var(--bc) / 0.5);
}

.focus-card-value {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.focus-card-skill {
  font-size: 1.0625rem;
  font-weight: 700;
  color: oklch(var(--bc));
}

.focus-card-score {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.03em;
  color: oklch(var(--bc) / 0.85);
}

.focus-card-desc {
  margin-top: 0.55rem;
  font-size: 0.75rem;
  line-height: 1.7;
  color: oklch(var(--bc) / 0.62);
}

/* ============================================================
   §1 技能条
   原来五条各用一个语义色（primary/secondary/accent/info/success），
   彩虹一片，反而看不出谁高谁低。现在统一主色、按分数排序，
   只有末位换成 warning —— 页面上唯一需要注意的那一条
   ============================================================ */
/* 行式布局：名称 | 进度 | 读数。原来名称在上、条在下、条通吃整行宽度，
   在 1490px 的面板里 6px 高的条被拉成一根发丝，反而看不出长度差 */
.skill-list {
  display: grid;
  gap: 0.85rem 2.75rem;
}

@media (min-width: 1280px) {
  .skill-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.skill-row {
  display: grid;
  /* 名称列要装得下「排障能力 + 短板」而不折行 */
  grid-template-columns: 7.5rem minmax(0, 1fr) 4.25rem;
  align-items: center;
  gap: 0.85rem;
}

.skill-name {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
  font-size: 0.8125rem;
  font-weight: 500;
  color: oklch(var(--bc) / 0.85);
}

.skill-flag {
  padding: 0.05rem 0.35rem;
  font-size: 0.625rem;
  font-weight: 700;
  border-radius: 4px;
  color: oklch(var(--wa));
  background: oklch(var(--wa) / 0.14);
}

.skill-score {
  flex: none;
  text-align: right;
  font-size: 0.8125rem;
  font-weight: 700;
  color: oklch(var(--bc) / 0.75);
}

.skill-score em {
  font-size: 0.6875rem;
  font-style: normal;
  font-weight: 400;
  color: oklch(var(--bc) / 0.35);
}

.skill-score.is-weak {
  color: oklch(var(--wa));
}

.skill-track {
  position: relative;
  height: 6px;
  border-radius: 999px;
  background: oklch(var(--bc) / 0.09);
  overflow: hidden;
}

/* 60 / 80 两条参考刻度，让读数有个参照 */
.skill-tick {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: oklch(var(--b1) / 0.75);
}

.skill-fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: 999px;
  background: oklch(var(--p) / 0.85);
  transition: width 0.7s cubic-bezier(0.16, 1, 0.3, 1);
}

.skill-fill.is-weak {
  background: oklch(var(--wa) / 0.85);
}

/* ============================================================
   §1 AI 建议
   ============================================================ */
.advice-block {
  padding: 1.1rem 1.25rem;
  border: 1px solid oklch(var(--in) / 0.22);
  border-radius: 14px;
  background: oklch(var(--in) / 0.07);
}

.advice-head {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: oklch(var(--in));
}

.advice-body {
  margin-top: 0.6rem;
  font-size: 0.875rem;
  line-height: 1.8;
  color: oklch(var(--bc) / 0.8);
}

.advice-foot {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  margin-top: 0.9rem;
  padding-top: 0.8rem;
  border-top: 1px solid oklch(var(--in) / 0.18);
  font-size: 0.8125rem;
  color: oklch(var(--bc) / 0.62);
}

/* ============================================================
   §4 近期训练小卡 / 薄弱维度 / 空态
   ============================================================ */
.mini-card {
  padding: 0.95rem 1rem;
  border: 1px solid oklch(var(--bc) / 0.1);
  border-radius: 14px;
  background: oklch(var(--b2) / 0.4);
}

.mini-card-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: oklch(var(--bc) / 0.9);
}

.mini-card-time {
  margin-top: 0.2rem;
  font-size: 0.6875rem;
  color: oklch(var(--bc) / 0.45);
}

.mini-card-desc {
  margin-top: 0.6rem;
  font-size: 0.8125rem;
  line-height: 1.7;
  color: oklch(var(--bc) / 0.65);
}

.dim-card {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  padding: 0.9rem 1rem;
  border-left-width: 3px;
  border-radius: 12px;
  background: oklch(var(--b2) / 0.45);
}

.dim-card > i {
  margin-top: 0.15rem;
  font-size: 1rem;
  opacity: 0.85;
}

.dim-card-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: oklch(var(--bc) / 0.9);
}

.dim-card-desc {
  margin-top: 0.35rem;
  font-size: 0.75rem;
  line-height: 1.65;
  color: oklch(var(--bc) / 0.62);
}

/* 空态用虚线框 + 图标 + 一句解释，和 SolveHistoryPanel 里的写法保持一致，
   比一行灰字更像「设计过的状态」而不是漏了内容 */
.empty-state {
  padding: 2.25rem 1.5rem;
  text-align: center;
  border: 1px dashed oklch(var(--bc) / 0.18);
  border-radius: 14px;
  background: oklch(var(--b2) / 0.3);
}

.empty-state > i {
  font-size: 1.5rem;
  color: oklch(var(--bc) / 0.25);
}

.empty-state-title {
  margin-top: 0.7rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: oklch(var(--bc) / 0.75);
}

.empty-state p {
  margin-top: 0.3rem;
  font-size: 0.8125rem;
  color: oklch(var(--bc) / 0.5);
}

/* ============================================================
   §4 推荐强化任务
   ============================================================ */
.rec-card {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 1.25rem;
  padding: 1.25rem;
  border: 1px solid oklch(var(--bc) / 0.11);
  border-left-width: 3px;
  border-radius: 16px;
  background: oklch(var(--b1));
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}

/* 优先级从「又一个 badge」升级成左侧色条：不占横向空间，扫一眼就能分堆 */
.rec-card-high {
  border-left-color: oklch(var(--er) / 0.75);
}

.rec-card-normal {
  border-left-color: oklch(var(--wa) / 0.6);
}

.rec-card:hover {
  border-color: oklch(var(--bc) / 0.2);
  box-shadow: 0 10px 26px -18px rgb(0 0 0 / 0.6);
}

.rec-main {
  flex: 1 1 20rem;
  min-width: 0;
}

.rec-title-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.rec-title {
  font-size: 1.0625rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: oklch(var(--bc));
}

.rec-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: oklch(var(--bc) / 0.55);
}

.rec-meta > span:not(:last-child)::after {
  content: '·';
  margin-left: 0.5rem;
  color: oklch(var(--bc) / 0.3);
}

.rec-meta strong {
  font-weight: 700;
  color: oklch(var(--bc) / 0.8);
}

.rec-reason {
  margin-top: 0.85rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid oklch(var(--p) / 0.14);
  border-radius: 10px;
  background: oklch(var(--p) / 0.05);
  font-size: 0.8125rem;
  line-height: 1.75;
  color: oklch(var(--bc) / 0.78);
}

.rec-reason strong {
  margin-right: 0.4rem;
  font-weight: 700;
  color: oklch(var(--bc) / 0.9);
}

.rec-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.75rem;
}

.rec-tags > span {
  padding: 0.15rem 0.45rem;
  font-size: 0.6875rem;
  border-radius: 5px;
  color: oklch(var(--bc) / 0.55);
  background: oklch(var(--bc) / 0.06);
}

.rec-action {
  flex: 0 0 13.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1rem;
  border: 1px solid oklch(var(--bc) / 0.09);
  border-radius: 12px;
  background: oklch(var(--b2) / 0.45);
}

@media (max-width: 767px) {
  .rec-action {
    flex: 1 1 100%;
  }
}

.rec-action-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: oklch(var(--bc) / 0.45);
}

.rec-action-text {
  font-size: 0.8125rem;
  line-height: 1.65;
  color: oklch(var(--bc) / 0.75);
}

.rec-action-wait {
  font-size: 0.6875rem;
  line-height: 1.6;
  color: oklch(var(--bc) / 0.55);
}

/* ============================================================
   §5 知识点复习卡
   ============================================================ */
.review-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  border: 1px solid oklch(var(--bc) / 0.11);
  border-radius: 14px;
  background: oklch(var(--b1));
  transition: border-color 0.25s ease, transform 0.25s ease;
}

.review-card:hover {
  transform: translateY(-2px);
  border-color: oklch(var(--s) / 0.45);
}

.review-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.review-card-icon {
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 10px;
  color: oklch(var(--s));
  background: linear-gradient(135deg, oklch(var(--s) / 0.18), oklch(var(--p) / 0.1));
}

.review-card-type {
  flex: none;
  padding: 0.15rem 0.45rem;
  font-size: 0.6875rem;
  font-weight: 600;
  border-radius: 5px;
  color: oklch(var(--bc) / 0.6);
  background: oklch(var(--bc) / 0.07);
}

.review-card-title {
  font-size: 0.9375rem;
  font-weight: 700;
  line-height: 1.45;
  color: oklch(var(--bc));
  overflow-wrap: anywhere;
}

.review-card-desc {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 0.75rem;
  line-height: 1.65;
  color: oklch(var(--bc) / 0.6);
}

.review-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.35rem;
}

.review-card-tags > span {
  padding: 0.1rem 0.4rem;
  font-size: 0.625rem;
  border-radius: 4px;
  color: oklch(var(--bc) / 0.5);
  background: oklch(var(--bc) / 0.06);
}

/* ============================================================
   资料弹窗（保留原有的字号偏好）
   ============================================================ */
.form-control .input,
.form-control .select {
  font-size: 1.05rem;
  padding: 0.75rem 1rem;
}

.label-text {
  font-weight: 500;
  font-size: 0.95rem;
}

.training-answer {
  overflow-wrap: anywhere;
}
</style>
