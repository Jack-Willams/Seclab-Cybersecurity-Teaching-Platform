import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'

import CourseAnalysisPanel from './CourseAnalysisPanel.vue'

describe('CourseAnalysisPanel', () => {
  it('renders a concrete teaching plan instead of a generic action sentence', async () => {
    const html = await renderToString(createSSRApp(CourseAnalysisPanel, {
      subjectLabel: '班级',
      data: {
        teacherId: 1,
        teachingClassId: 1,
        courseId: 1,
        scope: 'CLASS',
        analysisStatus: 'READY',
        analysis: {
          scope: 'class_course',
          courseId: 1,
          courseName: 'SQL注入攻击',
          generatedBy: 'course_evidence_fallback',
          fallbackUsed: true,
          overallComment: '本实验共记录 5 道题。',
          knowledgeFindings: [{
            knowledgePointName: 'SQL注入联合查询列数判断',
            accuracyRate: 0.2,
            evidence: '5 道题中有 4 道最后一次仍答错。',
            affectedStudents: ['陈宇航', '刘子涵'],
            representativeQuestionTitle: 'UNION 查询列数判断',
            observedAnswer: '只写出了部分步骤，缺少验证依据。',
            standardAnswer: '从 ORDER BY 1 开始递增，首次报错序号减一。',
            diagnosis: '作答缺少 ORDER BY 逐级探测和列数验证。',
            instruction: '演示 ORDER BY 1、2、3 直到报错，再用 UNION SELECT NULL 验证。',
            check: '让陈宇航、刘子涵独立完成一个不同列数的查询。',
            teacherAction: '结构化教学计划',
          }],
          teachingSuggestions: [],
        },
      },
    }))

    expect(html).toContain('先处理学生')
    expect(html).toContain('陈宇航、刘子涵')
    expect(html).toContain('代表题')
    expect(html).toContain('UNION 查询列数判断')
    expect(html).toContain('学生最后作答')
    expect(html).toContain('标准答案')
    expect(html).toContain('错因定位')
    expect(html).toContain('课堂讲解')
    expect(html).toContain('当堂验证')
    expect(html).toContain('UNION SELECT NULL')
    expect(html).not.toContain('打开下方错题')
  })
})
