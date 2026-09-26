export type GrowthMetricUnit = 'percent' | 'seconds' | 'score' | string

export function formatGrowthDelta(delta: number | null | undefined): string {
  if (delta == null) return '尚无对比'
  if (delta > 0) return `↑ ${delta.toFixed(1)}`
  if (delta < 0) return `↓ ${Math.abs(delta).toFixed(1)}`
  return '→ 0.0'
}

export function formatMetricValue(
  value: number | null | undefined,
  unit: GrowthMetricUnit,
): string {
  if (value == null) return '—'
  if (unit === 'percent') return `${value.toFixed(1)}%`
  if (unit === 'seconds') {
    const seconds = Math.max(0, Math.round(value))
    const minutes = Math.floor(seconds / 60)
    const remainder = seconds % 60
    if (!minutes) return `${remainder}秒`
    if (!remainder) return `${minutes}分钟`
    return `${minutes}分${remainder}秒`
  }
  return value.toFixed(1)
}

export function confidenceLabel(confidence: string): string {
  return {
    high: '高可信',
    moderate: '中等可信',
    emerging: '初步趋势',
    insufficient: '样本不足',
  }[confidence] ?? '可信度未知'
}

export function metricDirectionLabel(direction: string): string {
  return {
    improved: '提升',
    stable: '稳定',
    declined: '需关注',
    insufficient: '暂不判断',
  }[direction] ?? '暂不判断'
}
