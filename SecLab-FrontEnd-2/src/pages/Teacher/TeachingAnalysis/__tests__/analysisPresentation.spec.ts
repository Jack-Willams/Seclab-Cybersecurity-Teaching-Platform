import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import {
  buildKnowledgeRiskPie,
  classifyKnowledgeRisk,
  findMatchingRiskItem,
  getAnalysisRefreshPresentation,
  getRiskPresentation,
  getTimelineEventPresentation,
  normalizeEvidenceCount,
} from '../analysisPresentation'

function pieRisk(overrides: Record<string, unknown> = {}) {
  return {
    courseId: 7,
    courseName: 'SQL 注入攻击',
    knowledgePointName: '联合查询列数判断',
    knowledgeCategory: 'SQL 注入',
    riskLevel: 'attention',
    incorrectRate: 0.25,
    attemptedCount: 8,
    incorrectCount: 2,
    affectedStudents: [],
    ...overrides,
  }
}

describe('teaching analysis presentation', () => {
  it('uses pie-chart and experiment wording throughout the teacher page', () => {
    const pageSource = readFileSync(new URL('../index.vue', import.meta.url), 'utf8')
    const pieSource = readFileSync(new URL('../components/KnowledgeRiskPieChart.vue', import.meta.url), 'utf8')
    expect(pageSource).not.toContain('热力图')
    expect(pageSource).toContain('本实验')
    expect(pieSource).toContain('知识点错误占比饼图')
  })

  it('does not expose implementation explanations to teachers', () => {
    const componentNames = [
      'CourseAnalysisPanel.vue',
      'CourseQuestionRecords.vue',
      'IssuePersonalizedPracticeDialog.vue',
      'KnowledgeAiAnalysisPanel.vue',
      'KnowledgeExerciseReview.vue',
      'KnowledgeRiskPieChart.vue',
      'TeachingActionPanel.vue',
      'CapabilityEvidencePanel.vue',
      'LearningReplayTimeline.vue',
    ]
    const source = componentNames
      .map((name) => readFileSync(new URL(`../components/${name}`, import.meta.url), 'utf8'))
      .join('\n')
    for (const phrase of [
      '每个知识点都是独立扇区，同色不会合并',
      '不绘制虚假的饼图面积',
      '由老师手动发起',
      '不会凭空补人数或错误情况',
      '生成不可变快照',
      '不会再次调用 AI',
      '三类题互相独立',
      'Dify 恢复后',
      '五维画像不作为题目分组',
      '真实作答证据、画像和知识点饼图仍可正常查看',
      '画像和学习记录持续同步',
      '本实验知识点饼图和作答证据已经可用',
      '题目生成并提交后，会自动',
      '自动比较能力分数和错题表现',
      '已同步到相关学生的画像页',
      '点击任一能力，查看支撑分数',
      '按时间还原“开始实验',
    ]) expect(source).not.toContain(phrase)

    const pageSource = readFileSync(new URL('../index.vue', import.meta.url), 'utf8')
    for (const phrase of [
      '真实作答证据、画像和知识点饼图仍可正常查看',
      '画像和学习记录持续同步',
      '本实验知识点饼图和作答证据已经可用',
      '五维分数用于综合观察',
      '已保留上一次成功结果',
      'aiHealth.message',
    ]) expect(pageSource).not.toContain(phrase)
  })

  it('turns a provider refresh failure into a scoped teacher-facing status', () => {
    const presentation = getAnalysisRefreshPresentation(
      {
        response: {
          status: 503,
          data: {
            detail: 'Dify 已返回内容，但 Agent 输出格式不正确。',
          },
        },
      },
      true,
    )

    expect(presentation).toEqual({
      tone: 'warning',
      message: '本次智能分析未更新，当前仍显示上次结果；原始作答统计不受影响。',
    })
    expect(presentation.message).not.toContain('Dify')
    expect(presentation.message).not.toContain('Agent')
    expect(presentation.message).not.toContain('格式')
  })
  it('maps risk levels to stable teacher-facing labels', () => {
    expect(getRiskPresentation('high')).toEqual({ label: '高风险', tone: 'danger' })
    expect(getRiskPresentation('medium')).toEqual({ label: '需关注', tone: 'warning' })
    expect(getRiskPresentation('low')).toEqual({ label: '基本掌握', tone: 'success' })
  })

  it('describes failed and recovered commands as different learning outcomes', () => {
    expect(getTimelineEventPresentation('COMMAND', 'failed').label).toBe('命令执行失败')
    expect(getTimelineEventPresentation('COMMAND', 'recovered').label).toBe('重试后成功')
    expect(getTimelineEventPresentation('HINT').label).toBe('请求提示')
  })

  it('never presents a negative evidence count', () => {
    expect(normalizeEvidenceCount(-2)).toBe(0)
    expect(normalizeEvidenceCount(7)).toBe(7)
  })

  it('matches a class problem to its clickable risk details', () => {
    const matched = findMatchingRiskItem(
      {
        title: 'XSS 输出上下文判断不稳定',
        evidence: '11 名学生在文本、属性与脚本上下文中出现错误。',
        questionIds: ['question-xss-1'],
      },
      [
        {
          courseName: 'Web 安全',
          knowledgePointName: 'XSS 与 CSRF 攻击',
          knowledgeCategory: 'XSS',
          studentCount: 32,
          attemptedStudentCount: 11,
          incorrectStudentCount: 9,
          attemptedCount: 15,
          incorrectCount: 9,
          incorrectRate: 60,
          riskLevel: 'high',
          affectedStudents: [{ studentId: 261, studentName: '陈宇航' }],
          representativeQuestions: [{ generatedQuestionId: 'question-xss-1', title: 'XSS 输出编码判断' }],
        },
      ],
    )

    expect(matched?.knowledgePointName).toBe('XSS 与 CSRF 攻击')
    expect(matched?.affectedStudents[0].studentName).toBe('陈宇航')
  })

  it('keeps same-colour knowledge points as independent pie slices', () => {
    const result = buildKnowledgeRiskPie([
      pieRisk({ knowledgePointId: 1, knowledgePointName: '列数判断', incorrectCount: 2, attemptedCount: 8, incorrectRate: 0.25 }),
      pieRisk({ knowledgePointId: 2, knowledgePointName: '回显位判断', incorrectCount: 3, attemptedCount: 10, incorrectRate: 0.30 }),
    ], 7)

    expect(result.slices).toHaveLength(2)
    expect(result.slices.map((item) => item.key)).toEqual(['1-列数判断', '2-回显位判断'])
    expect(result.slices.map((item) => item.tone)).toEqual(['attention', 'attention'])
    expect(result.slices.map((item) => item.sharePercent)).toEqual([40, 60])
    expect(result.slices.reduce((total, item) => total + item.sharePercent, 0)).toBe(100)
  })

  it('scopes pie data to the selected experiment and separates zero-error mastery', () => {
    const result = buildKnowledgeRiskPie([
      pieRisk({ knowledgePointId: 1, incorrectCount: 2 }),
      pieRisk({ knowledgePointId: 2, incorrectCount: 0, incorrectRate: 0 }),
      pieRisk({ courseId: 8, knowledgePointId: 3, incorrectCount: 9, incorrectRate: 0.9 }),
    ], 7)

    expect(result.totalIncorrect).toBe(2)
    expect(result.slices.map((item) => item.item.knowledgePointId)).toEqual([1])
    expect(result.mastered.map((item) => item.knowledgePointId)).toEqual([2])
  })

  it('uses red orange yellow and green thresholds from each point error rate', () => {
    expect(classifyKnowledgeRisk(0.60).tone).toBe('high')
    expect(classifyKnowledgeRisk(0.40).tone).toBe('medium')
    expect(classifyKnowledgeRisk(0.20).tone).toBe('attention')
    expect(classifyKnowledgeRisk(0.1999).tone).toBe('good')
  })
})
