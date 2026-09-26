import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'
import TeacherAssignments from './TeacherAssignments.vue'

describe('TeacherAssignments', () => {
  it('renders the personal teaching task with experiment scope and learning result', async () => {
    const html = await renderToString(createSSRApp(TeacherAssignments, {
      userId: 261,
      initialAssignments: [{
        interventionId: 17,
        teacherId: 7,
        teachingClassId: 101,
        courseId: 7,
        title: '列数判断个性化练习',
        actionType: 'TARGETED_PRACTICE',
        knowledgePointId: 71,
        description: '完成老师审核后的题目',
        status: 'ACTIVE',
        baselineAt: '2026-07-18T10:00:00',
        dueAt: '2026-07-20T10:00:00',
        createdAt: '2026-07-18T10:00:00',
        updatedAt: '2026-07-18T10:00:00',
        students: [],
        questions: [],
        progress: { studentCount: 1, completedCount: 1, completionRate: 1, evaluationDue: false },
        className: '网安 1 班',
        teacherName: '李老师',
        courseName: 'SQL 注入攻击',
        knowledgePointName: '联合查询列数判断',
        assignmentStatus: 'COMPLETED',
        trainingSessionId: 'train-approved-1',
        questionCount: 3,
        estimatedMinutes: 15,
        isOverdue: false,
        resultSummary: { attemptCount: 3, correctCount: 2, averageScore: 78.5 },
      }],
    }))

    expect(html).toContain('老师布置的个性化练习')
    expect(html).toContain('SQL 注入攻击')
    expect(html).toContain('联合查询列数判断')
    expect(html).toContain('3 题')
    expect(html).toContain('平均 78.5 分')
    expect(html).toContain('查看作答结果')
    expect(html).not.toContain('作答结果会回流给老师')
  })
})
