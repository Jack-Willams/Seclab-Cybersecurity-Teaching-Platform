import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import KnowledgeAiAnalysisPanel from '../components/KnowledgeAiAnalysisPanel.vue'
import IssuePersonalizedPracticeDialog from '../components/IssuePersonalizedPracticeDialog.vue'
import TeachingActionPanel from '../components/TeachingActionPanel.vue'

const exercises = [
  { exerciseId: 1, analysisId: 9, role: 'FOUNDATION', questionType: 'short_answer', stem: '先验证什么？', options: [], standardAnswer: '验证列数', explanation: '建立验证顺序', difficulty: 1, generationRationale: '补足基础', reviewStatus: 'APPROVED', reviewComment: '', sourceVersion: 1 },
  { exerciseId: 2, analysisId: 9, role: 'CONSOLIDATION', questionType: 'short_answer', stem: '怎样定位回显位？', options: [], standardAnswer: '使用标记值', explanation: '巩固方法', difficulty: 2, generationRationale: '同类巩固', reviewStatus: 'PENDING_REVIEW', reviewComment: '', sourceVersion: 1 },
  { exerciseId: 3, analysisId: 9, role: 'TRANSFER', questionType: 'short_answer', stem: '无报错时如何验证？', options: [], standardAnswer: '使用布尔或时间差异', explanation: '迁移方法', difficulty: 3, generationRationale: '迁移应用', reviewStatus: 'NEEDS_REVISION', reviewComment: '范围太大', sourceVersion: 1 },
] as const

const analysis = {
  teacherId: 7,
  teachingClassId: 101,
  courseId: 7,
  knowledgePointId: 71,
  analysisStatus: 'READY',
  analysis: {
    overallConclusion: '多数错误来自跳过列数验证。',
    commonMistakes: [{ title: '直接猜列数', reason: '没有形成验证顺序' }],
    teachingAdvice: [{ title: '先证据后结论', action: '下节课演示 ORDER BY 递增验证' }],
  },
  evidence: {},
  lastErrorMessage: null,
  generatedAt: '2026-07-18T12:00:00',
  exercises,
}

describe('KnowledgeAiAnalysisPanel', () => {
  it('renders grounded advice and three independently reviewed exercises', async () => {
    const html = await renderToString(createSSRApp(KnowledgeAiAnalysisPanel, {
      classId: 101,
      courseId: 7,
      knowledgePointId: 71,
      knowledgePointName: '联合查询列数判断',
      affectedStudents: [{ studentId: 261, studentName: '陈宇航' }],
      allStudents: [],
      initialAnalysis: analysis,
    }))

    expect(html).toContain('多数错误来自跳过列数验证')
    expect(html).toContain('下节课演示 ORDER BY 递增验证')
    expect(html).toContain('基础例题')
    expect(html).toContain('巩固例题')
    expect(html).toContain('迁移例题')
    expect(html.match(/data-exercise-id=/g)).toHaveLength(3)
    expect(html).toContain('已审核通过 1/3')
  })

  it('only offers approved exercises for immutable assignment snapshots', async () => {
    const html = await renderToString(createSSRApp(IssuePersonalizedPracticeDialog, {
      open: true,
      classId: 101,
      courseId: 7,
      knowledgePointId: 71,
      knowledgePointName: '联合查询列数判断',
      exercises,
      affectedStudents: [{ studentId: 261, studentName: '陈宇航' }],
      allStudents: [{ studentId: 261, studentName: '陈宇航', studentNumber: '2026001' }],
    }))

    expect(html).toContain('下发个性化练习')
    expect(html).toContain('先验证什么？')
    expect(html).not.toContain('怎样定位回显位？')
    expect(html).not.toContain('不可变快照')
    expect(html).not.toContain('不会再次调用 AI')
  })

  it('does not expose the legacy unreviewed targeted-practice path', async () => {
    const html = await renderToString(createSSRApp(TeachingActionPanel, {
      classId: 101,
      students: [],
      selectedRisk: null,
      interventions: [],
    }))

    expect(html).not.toContain('<option value="TARGETED_PRACTICE"')
    expect(html).not.toContain('专项练习请在知识点详情中审核例题后下发')
  })

  it('shows student completion and answer results in the teacher feedback loop', async () => {
    const html = await renderToString(createSSRApp(TeachingActionPanel, {
      classId: 101,
      students: [],
      selectedRisk: null,
      interventions: [{
        interventionId: 17, teacherId: 7, teachingClassId: 101, courseId: 7,
        title: '列数判断个性化练习', actionType: 'TARGETED_PRACTICE', knowledgePointId: 71,
        description: '专项练习', status: 'ACTIVE', baselineAt: '2026-07-18T10:00:00',
        dueAt: '2026-07-20T10:00:00', createdAt: '2026-07-18T10:00:00', updatedAt: '2026-07-18T10:00:00',
        students: [{ studentId: 261, studentName: '陈宇航', assignmentStatus: 'COMPLETED', resultSummary: { attemptCount: 3, correctCount: 2, averageScore: 82 } }],
        questions: [], progress: { studentCount: 1, completedCount: 1, completionRate: 1, evaluationDue: false },
      }],
    }))

    expect(html).toContain('陈宇航')
    expect(html).toContain('平均 82 分')
    expect(html).toContain('已完成')
  })
})
