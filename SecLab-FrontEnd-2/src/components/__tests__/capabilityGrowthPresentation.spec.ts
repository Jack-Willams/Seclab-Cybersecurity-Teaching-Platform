import { describe, expect, it } from 'vitest'

import {
  confidenceLabel,
  formatGrowthDelta,
  formatMetricValue,
  metricDirectionLabel,
} from '../capabilityGrowthPresentation'

describe('capability growth presentation', () => {
  it('formats score movement without inventing a comparison', () => {
    expect(formatGrowthDelta(12.4)).toBe('↑ 12.4')
    expect(formatGrowthDelta(-3)).toBe('↓ 3.0')
    expect(formatGrowthDelta(0)).toBe('→ 0.0')
    expect(formatGrowthDelta(null)).toBe('尚无对比')
  })

  it('formats real metric units for quick reading', () => {
    expect(formatMetricValue(83.333, 'percent')).toBe('83.3%')
    expect(formatMetricValue(420, 'seconds')).toBe('7分钟')
    expect(formatMetricValue(75, 'seconds')).toBe('1分15秒')
    expect(formatMetricValue(null, 'seconds')).toBe('—')
  })

  it('translates confidence and direction into restrained claims', () => {
    expect(confidenceLabel('high')).toBe('高可信')
    expect(confidenceLabel('emerging')).toBe('初步趋势')
    expect(confidenceLabel('insufficient')).toBe('样本不足')
    expect(metricDirectionLabel('improved')).toBe('提升')
    expect(metricDirectionLabel('declined')).toBe('需关注')
    expect(metricDirectionLabel('insufficient')).toBe('暂不判断')
  })
})
