import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'

import type { ProfileDashboardSolveRecord } from '../../../api'
import SolveHistoryPanel from './SolveHistoryPanel.vue'

const records: ProfileDashboardSolveRecord[] = [
  {
    id: 'course:sub-1',
    sourceType: 'course_question',
    questionId: '1',
    title: '以下哪种方法最适合初步判断 SQL 注入？',
    experiment: '以下哪种方法最适合初步判断 SQL 注入？',
    stem: '以下哪种方法最适合初步判断 SQL 注入？',
    questionType: 'multiple-choice',
    module: '模块 #1',
    time: '2026-07-24 20:58:31',
    result: '正确',
    isCorrect: true,
    score: 4,
    costTime: 18,
    studentAnswer: ['输入单引号'],
    standardAnswer: ['输入单引号'],
    options: ['输入随机字符', '输入单引号', '执行 JavaScript', '修改 HTTP 头'],
    explanation: '',
    contentAvailable: true,
  },
  {
    id: 'generated:attempt-1',
    sourceType: 'generated_training',
    questionId: 'gq-1',
    trainingSessionId: 'train-1',
    title: '联合查询列数判断',
    experiment: '联合查询列数判断',
    stem: '如何判断 UNION SELECT 的列数？',
    questionType: 'SHORT_ANSWER',
    module: '模块 #1',
    time: '2026-07-25 10:00:00',
    result: '错误',
    isCorrect: false,
    score: 35,
    costTime: 42,
    studentAnswer: '直接猜三列',
    standardAnswer: '使用 ORDER BY 递增或 UNION SELECT NULL 逐步验证。',
    options: [],
    explanation: '应通过数据库响应差异逐步确认列数。',
    contentAvailable: true,
  },
  {
    id: 'course:old',
    sourceType: 'course_question',
    questionId: 'legacy-99',
    title: '历史题目 legacy-99',
    experiment: '历史题目 legacy-99',
    stem: '',
    questionType: 'single-choice',
    module: '未关联模块',
    time: '2025-01-01 00:00:00',
    result: '错误',
    isCorrect: false,
    score: 0,
    costTime: null,
    studentAnswer: [0],
    standardAnswer: [1],
    options: [],
    explanation: '',
    contentAvailable: false,
  },
]

describe('SolveHistoryPanel', () => {
  it('renders real question identity, wrong count, and expandable review details', async () => {
    const html = await renderToString(createSSRApp(SolveHistoryPanel, { records }))

    expect(html).toContain('全部 3')
    expect(html).toContain('错题 2')
    expect(html).toContain('正确 1')
    expect(html).toContain('以下哪种方法最适合初步判断 SQL 注入？')
    expect(html).toContain('联合查询列数判断')
    expect(html).toContain('查看详情')
    expect(html).toContain('我的答案')
    expect(html).toContain('直接猜三列')
    expect(html).toContain('正确答案')
    expect(html).toContain('使用 ORDER BY 递增或 UNION SELECT NULL 逐步验证。')
    expect(html).toContain('应通过数据库响应差异逐步确认列数。')
    expect(html).toContain('该历史记录未保存题干')
    expect(html).not.toContain('问题 #')
  })

  it('shows an honest empty state without creating placeholder records', async () => {
    const html = await renderToString(createSSRApp(SolveHistoryPanel, { records: [] }))

    expect(html).toContain('暂无真实作答记录')
    expect(html).not.toContain('问题 #1')
  })
})
