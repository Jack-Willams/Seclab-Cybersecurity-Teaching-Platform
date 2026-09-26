export type PresentationTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'
export type KnowledgeRiskTone = 'high' | 'medium' | 'attention' | 'good'

export function getAnalysisRefreshPresentation(
  _error: unknown,
  hasPreviousResult: boolean,
): { tone: PresentationTone; message: string } {
  if (hasPreviousResult) {
    return {
      tone: 'warning',
      message: '本次智能分析未更新，当前仍显示上次结果；原始作答统计不受影响。',
    }
  }
  return {
    tone: 'danger',
    message: '本次智能分析未生成可用结论，请稍后重试；原始作答统计不受影响。',
  }
}

const KNOWLEDGE_RISK_PRESENTATION: Record<KnowledgeRiskTone, { label: string; color: string }> = {
  high: { label: '严重错误', color: '#c9483c' },
  medium: { label: '重点关注', color: '#e98c3d' },
  attention: { label: '需要巩固', color: '#e7b23c' },
  good: { label: '掌握良好', color: '#3e9b65' },
}

export function classifyKnowledgeRisk(value?: number | null): {
  tone: KnowledgeRiskTone
  label: string
  color: string
} {
  const rate = Math.min(1, Math.max(0, Number(value) || 0))
  const tone: KnowledgeRiskTone = rate >= 0.6
    ? 'high'
    : rate >= 0.4
      ? 'medium'
      : rate >= 0.2
        ? 'attention'
        : 'good'
  return { tone, ...KNOWLEDGE_RISK_PRESENTATION[tone] }
}

export function getRiskPresentation(level?: string | null): { label: string; tone: PresentationTone } {
  const normalized = String(level || '').toLowerCase()
  if (normalized === 'high') return { label: '高风险', tone: 'danger' }
  if (normalized === 'medium') return { label: '需关注', tone: 'warning' }
  if (normalized === 'attention') return { label: '需要巩固', tone: 'warning' }
  if (normalized === 'good') return { label: '掌握良好', tone: 'success' }
  if (normalized === 'low') return { label: '基本掌握', tone: 'success' }
  return { label: '样本不足', tone: 'neutral' }
}

export function getTimelineEventPresentation(
  eventType?: string | null,
  outcome?: string | null,
): { label: string; tone: PresentationTone } {
  const type = String(eventType || '').toUpperCase()
  const normalizedOutcome = String(outcome || '').toLowerCase()
  if (type === 'COMMAND' && normalizedOutcome === 'failed') return { label: '命令执行失败', tone: 'danger' }
  if (type === 'COMMAND' && normalizedOutcome === 'recovered') return { label: '重试后成功', tone: 'success' }
  if (type === 'COMMAND') return { label: '执行命令', tone: 'info' }
  if (type === 'ERROR') return { label: '遇到报错', tone: 'danger' }
  if (type === 'HINT') return { label: '请求提示', tone: 'warning' }
  if (type === 'AI') return { label: 'AI 协作', tone: 'info' }
  if (type === 'ATTEMPT') return { label: '提交作答', tone: normalizedOutcome === 'success' ? 'success' : 'warning' }
  if (type === 'SUCCESS') return { label: '实验验证成功', tone: 'success' }
  if (type === 'LAB_START') return { label: '开始安全实验', tone: 'info' }
  return { label: '学习事件', tone: 'neutral' }
}

export function normalizeEvidenceCount(value?: number | null): number {
  return Math.max(0, Number.isFinite(Number(value)) ? Number(value) : 0)
}

interface ClassProblemLike {
  title?: string
  evidence?: string
  questionIds?: string[]
}

interface RiskItemLike {
  courseName: string
  knowledgePointName: string
  knowledgeCategory: string
  representativeQuestions: Array<{ generatedQuestionId: string }>
}

function searchable(value?: string | null): string {
  return String(value || '').toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]+/g, '')
}

export function findMatchingRiskItem<T extends RiskItemLike>(
  problem: ClassProblemLike,
  risks: T[],
): T | null {
  const problemText = searchable(`${problem.title || ''}${problem.evidence || ''}`)
  const questionIds = new Set((problem.questionIds || []).map(String))
  let best: { item: T; score: number } | null = null

  for (const item of risks) {
    let score = item.representativeQuestions.reduce(
      (total, question) => total + (questionIds.has(String(question.generatedQuestionId)) ? 10 : 0),
      0,
    )
    for (const label of [item.knowledgePointName, item.knowledgeCategory, item.courseName]) {
      const token = searchable(label)
      if (token.length >= 2 && (problemText.includes(token) || token.includes(problemText))) score += 3
    }
    if (score > 0 && (!best || score > best.score)) best = { item, score }
  }
  return best?.item || null
}

interface RiskPieItemLike {
  courseId?: number | null
  knowledgePointId?: number | null
  knowledgePointName: string
  incorrectCount: number
  attemptedCount: number
  incorrectRate: number
}

export interface KnowledgeRiskPieSlice<T extends RiskPieItemLike> {
  key: string
  item: T
  sharePercent: number
  incorrectRatePercent: number
  tone: KnowledgeRiskTone
  color: string
}

function allocateWholePercentages(values: number[], total: number): number[] {
  if (!total) return values.map(() => 0)
  const exact = values.map((value) => (value / total) * 100)
  const allocated = exact.map(Math.floor)
  let remainder = 100 - allocated.reduce((sum, value) => sum + value, 0)
  const order = exact
    .map((value, index) => ({ index, fraction: value - allocated[index] }))
    .sort((left, right) => right.fraction - left.fraction || left.index - right.index)
  for (let index = 0; index < remainder; index += 1) allocated[order[index].index] += 1
  return allocated
}

export function buildKnowledgeRiskPie<T extends RiskPieItemLike>(items: T[], selectedCourseId: number) {
  const scoped = items.filter((item) => Number(item.courseId) === Number(selectedCourseId))
  const mastered = scoped.filter((item) => Math.max(0, Number(item.incorrectCount) || 0) === 0)
  const withErrors = scoped.filter((item) => Math.max(0, Number(item.incorrectCount) || 0) > 0)
  const totalIncorrect = withErrors.reduce(
    (total, item) => total + Math.max(0, Number(item.incorrectCount) || 0),
    0,
  )
  const shares = allocateWholePercentages(
    withErrors.map((item) => Math.max(0, Number(item.incorrectCount) || 0)),
    totalIncorrect,
  )
  const slices: KnowledgeRiskPieSlice<T>[] = withErrors.map((item, index) => {
    const presentation = classifyKnowledgeRisk(item.incorrectRate)
    return {
      key: `${item.knowledgePointId ?? 'name'}-${item.knowledgePointName}`,
      item,
      sharePercent: shares[index],
      incorrectRatePercent: formatRiskRatePercent(item.incorrectRate),
      tone: presentation.tone,
      color: presentation.color,
    }
  })
  return { slices, mastered, totalIncorrect }
}

export function formatRiskRatePercent(value?: number | null): number {
  const rate = Number(value)
  if (!Number.isFinite(rate)) return 0
  return Math.round(Math.min(1, Math.max(0, rate)) * 100)
}
