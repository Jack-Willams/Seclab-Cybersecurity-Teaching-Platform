import type {
  ClassProfileLatestDto,
  ClassProfileStudentsResponse,
  CourseSummaryDto,
  LabEventsResponse,
  ProfileDashboardResponse,
  ProfileLatestResponse,
  TrainingDiagnoseResponse,
  TrainingSessionData,
  WeakKnowledgePoint,
} from '../api'
import type { ModuleOverViewType } from '../pages/User/Modules/components/ModuleOverView'
import type { User } from '../types/user'

type StudentPersona = {
  userId: number
  userName: string
  userStudentNumber: string
  userAcademy: string
  userClass: string
  classId: number
  courseId: number
  recentFocus: string
  tags: string[]
  weakDimensions: string[]
}

const studentPersonas: StudentPersona[] = [
  {
    userId: 1008,
    userName: '周书铭',
    userStudentNumber: '2023231008',
    userAcademy: '网络空间安全学院',
    userClass: '网络安全231班',
    classId: 2,
    courseId: 1,
    recentFocus: '调试器断点跟踪与二进制调用栈',
    tags: ['逆向基础待强化', '课堂出勤稳定', '调试复盘需要增加'],
    weakDimensions: ['自主探索', '知识掌握'],
  },
  {
    userId: 1012,
    userName: '何宇宸',
    userStudentNumber: '2023231012',
    userAcademy: '网络空间安全学院',
    userClass: '网络安全231班',
    classId: 2,
    courseId: 1,
    recentFocus: '应急日志分析与事件归因',
    tags: ['行为记录不完整', '实验参与积极', '事件链分析待补强'],
    weakDimensions: ['排障能力', 'AI协同'],
  },
  {
    userId: 1003,
    userName: '陈思远',
    userStudentNumber: '2023232003',
    userAcademy: '网络空间安全学院',
    userClass: '网络安全232班',
    classId: 1,
    courseId: 1,
    recentFocus: '命令执行与容器环境排查',
    tags: ['主动复盘', '实验参与稳定', '环境排障待提升'],
    weakDimensions: ['排障能力', 'AI协同'],
  },
  {
    userId: 1017,
    userName: '刘子涵',
    userStudentNumber: '2023232017',
    userAcademy: '网络空间安全学院',
    userClass: '网络安全232班',
    classId: 1,
    courseId: 1,
    recentFocus: 'XSS 输出点过滤与上下文判断',
    tags: ['知识掌握稳定', '提问意识较强', '上下文表达待强化'],
    weakDimensions: ['AI协同', '自主探索'],
  },
  {
    userId: 1024,
    userName: '王嘉豪',
    userStudentNumber: '2023232024',
    userAcademy: '网络空间安全学院',
    userClass: '网络安全232班',
    classId: 1,
    courseId: 1,
    recentFocus: 'SQL 注入联合查询与报错回显',
    tags: ['课堂配合积极', '知识点回顾需求高', '训练节奏稳定'],
    weakDimensions: ['知识掌握', '学习投入'],
  },
  {
    userId: 1030,
    userName: '林一鸣',
    userStudentNumber: '2023233030',
    userAcademy: '信息安全学院',
    userClass: '信息安全231班',
    classId: 3,
    courseId: 2,
    recentFocus: 'Linux 提权链与 SUID 误配分析',
    tags: ['综合能力较强', '提权路径需补足', '复盘表达清晰'],
    weakDimensions: ['排障能力', '知识掌握'],
  },
  {
    userId: 1033,
    userName: '郭沐晨',
    userStudentNumber: '2023233033',
    userAcademy: '信息安全学院',
    userClass: '信息安全231班',
    classId: 3,
    courseId: 2,
    recentFocus: '文件上传解析链与绕过策略',
    tags: ['错题复盘认真', '上传绕过需强化', '课堂协作良好'],
    weakDimensions: ['知识掌握', '自主探索'],
  },
]

const fallbackTeacherUser: User = {
  userId: 9001,
  userStudentNumber: '',
  userName: '王老师',
  userImage: '',
  userAcademy: '网络空间安全学院',
  userClass: '网络安全232班',
  classId: 1,
  createTime: '2026-04-27 10:53',
}

const fallbackCourseList: CourseSummaryDto[] = [
  {
    id: 1,
    name: 'Web安全综合实训',
    description: '覆盖 SQL 注入、XSS、CSRF 与文件上传的核心实验课。',
    difficulty: 3,
    imageUrl: '/default-course-image.png',
    type: '综合实训',
    tags: ['Web安全', '综合实训'],
    status: 'published',
  },
  {
    id: 2,
    name: '漏洞利用进阶训练',
    description: '聚焦命令执行、目录穿越与权限绕过。',
    difficulty: 4,
    imageUrl: '/default-course-image.png',
    type: '攻防提升',
    tags: ['漏洞利用', '提权排障'],
    status: 'published',
  },
  {
    id: 3,
    name: 'AI辅助安全分析',
    description: '训练学生用 AI 进行错误定位、上下文补充和复盘。',
    difficulty: 2,
    imageUrl: '/default-course-image.png',
    type: '方法训练',
    tags: ['AI协同', '学习画像'],
    status: 'published',
  },
]

const fallbackModuleList: ModuleOverViewType[] = [
  {
    id: 1,
    name: 'SQL 注入基础',
    description: '联合查询、列数判断和报错注入。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '45分钟',
    score: 100,
  },
  {
    id: 2,
    name: 'XSS 输出点分析',
    description: '反射型与存储型 XSS 的输入输出链路。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '40分钟',
    score: 100,
  },
  {
    id: 3,
    name: '命令执行与环境恢复',
    description: '命令拼接、环境变量和容器排障。',
    difficulty: 4,
    type: '系统安全',
    status: 'available',
    estimatedTime: '60分钟',
    score: 100,
  },
  {
    id: 4,
    name: '文件上传绕过',
    description: 'MIME 绕过、后缀绕过和解析链路。',
    difficulty: 3,
    type: 'Web安全',
    status: 'available',
    estimatedTime: '35分钟',
    score: 100,
  },
]

const fallbackRecentLabEvents: LabEventsResponse = {
  total: 6,
  events: [
    {
      event_type: 'LAB_STARTED',
      timestamp: '2026-04-27T10:32:00',
      levelTitle: '命令执行靶机已启动',
      container: 'command-inject-web-1',
      message: '班级实验活跃，近一小时内有 11 次启动记录。',
    },
    {
      event_type: 'FLAG_SUBMITTED',
      timestamp: '2026-04-27T10:21:00',
      levelTitle: 'SQL 注入实验提交成功',
      prompt: '学生已完成联合查询关卡。',
      message: '平均尝试次数下降到 2.4 次。',
    },
    {
      event_type: 'AI_HINT_REQUESTED',
      timestamp: '2026-04-27T10:10:00',
      levelTitle: 'AI 提示请求',
      prompt: '近期热点集中在报错回显与命令过滤。',
      message: '建议继续加强上下文表达训练。',
    },
    {
      event_type: 'ERROR_RECORDED',
      timestamp: '2026-04-27T09:54:00',
      levelTitle: '实验错误记录',
      prompt: '容器路径错误和权限不足仍较常见。',
      message: '适合增加排障步骤书写要求。',
    },
  ],
}

function resolveStudentPersona(userId: number): StudentPersona {
  const exactMatch = studentPersonas.find((item) => item.userId === userId)
  if (exactMatch) {
    return exactMatch
  }

  return {
    userId,
    userName: `学生${userId}`,
    userStudentNumber: `2023${String(userId).padStart(6, '0')}`,
    userAcademy: '网络空间安全学院',
    userClass: '网络安全232班',
    classId: 1,
    courseId: 1,
    recentFocus: '综合靶场基础复盘',
    tags: ['静态展示用户', '画像待补充', '建议继续完成训练'],
    weakDimensions: ['知识掌握', 'AI协同'],
  }
}

function clampScore(score: number) {
  return Math.max(0, Math.min(100, Math.round(score)))
}

function scoreWithOffset(base: number, offset: number) {
  return clampScore(base + offset)
}

function buildWeakKnowledgePoints(persona: StudentPersona): WeakKnowledgePoint[] {
  return [
    {
      knowledge_point_id: 301,
      name: '联合查询列数判断',
      category: 'SQL 注入',
      description: '根据报错信息快速判断字段数量并完成回显位定位。',
      difficulty_level: 'medium',
      module_id: 1,
      task_id: 2,
      confidence: 0.88,
      evidence_level: 'profile',
      reason: '最近练习中在字段数试探与回显位选择上反复出错。',
    },
    {
      knowledge_point_id: 407,
      name: '命令执行过滤绕过',
      category: '命令执行',
      description: '结合空格绕过、变量拼接和环境探测完成命令注入。',
      difficulty_level: 'hard',
      module_id: 3,
      task_id: 1,
      confidence: 0.82,
      evidence_level: 'profile',
      reason: `${persona.userName} 在环境恢复和命令上下文表达上还有提升空间。`,
    },
    {
      knowledge_point_id: 512,
      name: 'XSS 输出上下文判断',
      category: 'XSS',
      description: '根据属性、标签和脚本上下文选择合适 payload。',
      difficulty_level: 'medium',
      module_id: 2,
      task_id: 3,
      confidence: 0.79,
      evidence_level: 'approximate',
      reason: '近期 AI 提问集中在 payload 为什么无效，说明上下文判断还不稳定。',
    },
  ]
}

export function createFallbackStudent(userId = 1003): User {
  const persona = resolveStudentPersona(userId)
  return {
    userId: persona.userId,
    userStudentNumber: persona.userStudentNumber,
    userName: persona.userName,
    userTel: '13800000000',
    userImage: '',
    userAcademy: persona.userAcademy,
    userClass: persona.userClass,
    userEmail: `${persona.userStudentNumber}@seclab.local`,
    userGender: 1,
    classId: persona.classId,
    createTime: '2026-04-27 10:53',
  }
}

export function createFallbackProfileLatest(
  userId = 1003,
  classId = 1,
  courseId = 1,
): ProfileLatestResponse {
  const persona = resolveStudentPersona(userId)
  const offset = ((userId % 5) - 2) * 2
  const knowledge = scoreWithOffset(74, offset)
  const troubleshooting = scoreWithOffset(61, offset - 2)
  const autonomy = scoreWithOffset(69, offset + 1)
  const aiCollaboration = scoreWithOffset(66, offset)
  const engagement = scoreWithOffset(82, offset + 2)
  const overallScore = clampScore((knowledge + troubleshooting + autonomy + aiCollaboration + engagement) / 5)

  return {
    snapshot_id: `mock-profile-${userId}`,
    user_id: userId,
    class_id: classId || persona.classId,
    course_id: courseId || persona.courseId,
    computed_at: '2026-04-27T10:53:00',
    knowledge_mastery_score: knowledge,
    troubleshooting_score: troubleshooting,
    autonomy_score: autonomy,
    ai_collaboration_score: aiCollaboration,
    engagement_score: engagement,
    overall_score: overallScore,
    profile_summary_json: {
      strengths: ['学习投入', '知识掌握'],
      weak_dimensions: persona.weakDimensions,
    },
    source_range_start: '2026-04-20T08:00:00',
    source_range_end: '2026-04-27T10:53:00',
    created_at: '2026-04-27T10:53:00',
    message: `${persona.userName} 的本地静态画像快照`,
  }
}

export function createFallbackProfileDashboard(userId = 1003): ProfileDashboardResponse {
  const persona = resolveStudentPersona(userId)
  const latest = createFallbackProfileLatest(userId, persona.classId, persona.courseId)

  return {
    userStats: {
      completedCourses: 3,
      totalScore: 846,
      ranking: 5,
      activeStreak: 9,
    },
    learningProfile: {
      skills: [
        { name: '知识掌握', score: latest.knowledge_mastery_score || 0, color: 'text-primary' },
        { name: '排障能力', score: latest.troubleshooting_score || 0, color: 'text-secondary' },
        { name: '自主探索', score: latest.autonomy_score || 0, color: 'text-accent' },
        { name: 'AI协同', score: latest.ai_collaboration_score || 0, color: 'text-info' },
        { name: '学习投入', score: latest.engagement_score || 0, color: 'text-success' },
      ],
      tags: persona.tags.map((text, index) => ({
        text,
        type: ['badge-primary', 'badge-secondary', 'badge-accent'][index % 3],
      })),
      recentFocus: persona.recentFocus,
      comprehensiveScore: latest.overall_score || 0,
      evaluation: `${persona.userName} 当前学习投入稳定，知识点掌握整体向好，但在 ${persona.weakDimensions.join('、')} 上还需要更多结构化训练与复盘。`,
    },
    solveRecords: [
      {
        id: 1,
        experiment: 'SQL 注入基础关卡',
        module: 'Web安全模块',
        time: '2026-04-26 20:15',
        result: '正确',
        score: 92,
      },
      {
        id: 2,
        experiment: 'XSS 输出点分析',
        module: 'Web安全模块',
        time: '2026-04-25 19:40',
        result: '正确',
        score: 88,
      },
      {
        id: 3,
        experiment: '命令执行与环境恢复',
        module: '系统安全模块',
        time: '2026-04-24 21:08',
        result: '错误',
        score: 56,
      },
    ],
  }
}

export function createFallbackTrainingDiagnose(
  userId = 1003,
  classId = 1,
  courseId = 1,
): TrainingDiagnoseResponse {
  const persona = resolveStudentPersona(userId)
  const latest = createFallbackProfileLatest(userId, classId, courseId)

  return {
    profile_snapshot_id: latest.snapshot_id || `mock-profile-${userId}`,
    user_id: userId,
    class_id: classId || persona.classId,
    course_id: courseId || persona.courseId,
    dimension_scores: {
      knowledge_mastery_score: latest.knowledge_mastery_score,
      troubleshooting_score: latest.troubleshooting_score,
      autonomy_score: latest.autonomy_score,
      ai_collaboration_score: latest.ai_collaboration_score,
      engagement_score: latest.engagement_score,
      overall_score: latest.overall_score,
    },
    weak_dimensions: persona.weakDimensions,
    tags: persona.tags,
    recent_focus: persona.recentFocus,
    weak_knowledge_points: buildWeakKnowledgePoints(persona),
    generation_constraints: {
      difficulty: 'medium',
      question_types: ['single_choice', 'fill_blank', 'short_answer'],
      question_count: 5,
    },
    recent_evidence: {
      recent_errors: ['字段数判断偏慢', '命令过滤绕过失败', '容器路径确认不完整'],
      recent_failed_tasks: [3, 7],
      recent_ai_topics: ['报错回显定位', '命令执行上下文补充'],
    },
  }
}

export function createFallbackTrainingSessions(
  userId = 1003,
  classId = 1,
  courseId = 1,
): TrainingSessionData[] {
  return [
    {
      training_session_id: `mock-session-${userId}-1`,
      user_id: userId,
      class_id: classId,
      course_id: courseId,
      profile_snapshot_id: `mock-profile-${userId}`,
      source_type: 'static-fallback',
      created_at: '2026-04-26T20:30:00',
      question_count: 5,
      attempt_count: 5,
    },
    {
      training_session_id: `mock-session-${userId}-2`,
      user_id: userId,
      class_id: classId,
      course_id: courseId,
      profile_snapshot_id: `mock-profile-${userId}`,
      source_type: 'static-fallback',
      created_at: '2026-04-24T18:10:00',
      question_count: 4,
      attempt_count: 4,
    },
  ]
}

export function createFallbackTeacherDashboard() {
  const classLatest: ClassProfileLatestDto = {
    snapshot_id: 'mock-class-1',
    class_id: 1,
    course_id: 1,
    computed_at: '2026-04-27T10:53:00',
    student_count: 42,
    class_avg_knowledge_mastery: 78,
    class_avg_troubleshooting: 64,
    class_avg_autonomy: 72,
    class_avg_ai_collaboration: 69,
    class_avg_engagement: 83,
    class_overall_score: 76,
    weak_dimensions_json: [
      { dimension_name: '排障能力', average_score: 64 },
      { dimension_name: 'AI 协同', average_score: 69 },
    ],
    strengths_json: [
      { dimension_name: '学习投入', average_score: 83 },
      { dimension_name: '知识掌握', average_score: 78 },
    ],
    summary_json: {
      main_strengths: [{ dimension_name: '学习投入' }, { dimension_name: '知识掌握' }],
      main_weak_dimensions: [{ dimension_name: '排障能力' }, { dimension_name: 'AI 协同' }],
    },
    created_at: '2026-04-27T10:53:00',
  }

  const classStudents: ClassProfileStudentsResponse = {
    class_id: 1,
    snapshot_id: 'mock-class-1',
    student_count: 42,
    source: 'static-fallback',
    students: [
      {
        user_id: 1003,
        overall_score: 48,
        knowledge_mastery_score: 58,
        troubleshooting_score: 42,
        autonomy_score: 50,
        ai_collaboration_score: 51,
        engagement_score: 39,
        risk_level: 'high',
        weak_dimensions: ['排障能力', '学习投入'],
        risk_reasons: ['靶机启动后中断次数较多', '错误恢复链路记录不完整'],
      },
      {
        user_id: 1017,
        overall_score: 57,
        knowledge_mastery_score: 68,
        troubleshooting_score: 55,
        autonomy_score: 60,
        ai_collaboration_score: 47,
        engagement_score: 58,
        risk_level: 'medium',
        weak_dimensions: ['AI 协同'],
        risk_reasons: ['AI 提问上下文缺少容器状态与报错片段'],
      },
      {
        user_id: 1024,
        overall_score: 61,
        knowledge_mastery_score: 49,
        troubleshooting_score: 66,
        autonomy_score: 63,
        ai_collaboration_score: 64,
        engagement_score: 63,
        risk_level: 'medium',
        weak_dimensions: ['知识掌握'],
        risk_reasons: ['基础题回顾不足，错题复盘频次偏低'],
      },
    ],
  }

  return {
    currentUser: fallbackTeacherUser,
    totalUsers: 128,
    courses: fallbackCourseList,
    modules: fallbackModuleList,
    classLatest,
    classStudents,
    recentLabEvents: fallbackRecentLabEvents,
  }
}
