import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import KnowledgeRiskPieChart from '../components/KnowledgeRiskPieChart.vue'
import KnowledgeRiskDetailDrawer from '../components/KnowledgeRiskDetailDrawer.vue'

const base = {
  courseId: 7,
  courseName: 'SQL 注入攻击',
  teachingOrder: 2,
  knowledgeCategory: 'SQL 注入',
  studentCount: 10,
  attemptedStudentCount: 8,
  incorrectStudentCount: 2,
  attemptedCount: 8,
  affectedStudents: [],
  representativeQuestions: [],
}

describe('KnowledgeRiskPieChart', () => {
  it('renders same-colour points and zero-error mastery as independent controls', async () => {
    const html = await renderToString(createSSRApp(KnowledgeRiskPieChart, {
      selectedCourseId: 7,
      items: [
        { ...base, knowledgePointId: 71, knowledgePointName: '列数判断', incorrectCount: 2, incorrectRate: .25, riskLevel: 'attention' },
        { ...base, knowledgePointId: 72, knowledgePointName: '回显位判断', incorrectCount: 3, incorrectRate: .30, riskLevel: 'attention' },
        { ...base, knowledgePointId: 73, knowledgePointName: '结果验证', incorrectCount: 0, incorrectRate: 0, riskLevel: 'good' },
      ],
    }))

    expect(html).toContain('data-risk-key="71-列数判断"')
    expect(html).toContain('data-risk-key="72-回显位判断"')
    expect(html.match(/data-tone="attention"/g)).toHaveLength(2)
    expect(html).toContain('data-mastered-key="73-结果验证"')
    expect(html).not.toContain('每个知识点都是独立扇区，同色不会合并')
    expect(html).not.toContain('不绘制虚假的饼图面积')
  })

  it('renders deterministic knowledge evidence in the detail drawer', async () => {
    const item = { ...base, knowledgePointId: 71, knowledgePointName: '列数判断', incorrectCount: 2, incorrectRate: .25, riskLevel: 'attention' }
    const html = await renderToString(createSSRApp(KnowledgeRiskDetailDrawer, {
      open: true,
      classId: 101,
      courseId: 7,
      item,
      initialDetail: {
        ...item,
        commonMistakes: [{ answer: '直接猜三列', count: 2, studentCount: 2 }],
        representativeAttempts: [{ studentId: 261, studentName: '陈宇航', generatedQuestionId: 'q-1', title: '列数判断', answer: '直接猜三列', standardAnswer: '先用 ORDER BY 验证', score: 50 }],
        affectedStudents: [{ studentId: 261, studentName: '陈宇航' }],
        pagination: { page: 1, size: 20, total: 1 },
      },
    }))

    expect(html).toContain('知识点详细情况')
    expect(html).toContain('直接猜三列')
    expect(html).toContain('先用 ORDER BY 验证')
    expect(html).toContain('陈宇航')
  })
})
