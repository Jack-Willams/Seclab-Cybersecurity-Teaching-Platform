import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { describe, expect, it } from 'vitest'

import type { CapabilityGrowthResponseDto } from '../../api'
import CapabilityGrowthPanel from '../CapabilityGrowthPanel.vue'

const realGrowth: CapabilityGrowthResponseDto = {
  studentId: 261,
  teachingClassId: 101,
  baselineComputedAt: '2026-07-01T09:00:00',
  currentComputedAt: '2026-07-20T09:00:00',
  calculationVersion: 'capability-growth-v1',
  dataProvenance: {
    mode: 'production_events',
    eligibleRecordCount: 18,
    excludedRecordCount: 2,
    unverifiableRecordCount: 0,
    sourceTypes: ['generated_question_attempt', 'container_command_event'],
    snapshotIds: ['profile-1', 'profile-2'],
  },
  overall: { baselineScore: 61, currentScore: 76, delta: 15 },
  dimensions: [
    {
      key: 'knowledge_mastery',
      label: '知识掌握',
      baselineScore: 62,
      currentScore: 78,
      delta: 16,
      confidence: 'moderate',
      summary: '可比题目正确率由 50.0% 变为 83.3%。',
      metrics: [
        {
          key: 'accuracy',
          label: '可比题目正确率',
          baselineValue: 50,
          currentValue: 83.3,
          unit: 'percent',
          changeRate: 33.3,
          direction: 'improved',
          baselineSampleCount: 6,
          currentSampleCount: 6,
          confidence: 'moderate',
          explanation: '同知识点、题型和难度的可比题目正确率提升 33.3 个百分点。',
          sourceTypes: ['generated_question_attempt'],
          sourceRecordIds: ['attempt-1', 'attempt-2'],
        },
        {
          key: 'answer_time',
          label: '有效作答时间',
          baselineValue: 120,
          currentValue: 75,
          unit: 'seconds',
          changeRate: -37.5,
          direction: 'improved',
          baselineSampleCount: 6,
          currentSampleCount: 6,
          confidence: 'moderate',
          explanation: '正确率没有下降的前提下，作答中位时间缩短。',
          sourceTypes: ['generated_question_attempt'],
          sourceRecordIds: ['attempt-1', 'attempt-2'],
        },
      ],
      evidence: [
        {
          kind: 'ATTEMPT',
          title: 'SQL 联合查询变式题',
          detail: '作答正确',
          occurredAt: '2026-07-20T09:00:00',
          sourceId: 'attempt-2',
          sourceType: 'generated_question_attempt',
        },
      ],
    },
    ...(['troubleshooting', 'autonomy', 'ai_collaboration', 'engagement'] as const).map((key) => ({
      key,
      label: {
        troubleshooting: '故障排查',
        autonomy: '自主学习',
        ai_collaboration: 'AI 协同',
        engagement: '学习投入',
      }[key],
      baselineScore: null,
      currentScore: null,
      delta: null,
      confidence: 'insufficient',
      summary: '当前没有足够的可比行为指标。',
      metrics: [],
      evidence: [],
    })),
  ],
  history: [
    { snapshotId: 'profile-1', computedAt: '2026-07-01T09:00:00', overallScore: 61 },
    { snapshotId: 'profile-2', computedAt: '2026-07-20T09:00:00', overallScore: 76 },
  ],
  message: null,
}

describe('CapabilityGrowthPanel', () => {
  it('renders an intuitive, traceable comparison from the API response', async () => {
    const html = await renderToString(createSSRApp(CapabilityGrowthPanel, {
      data: realGrowth,
      teacherMode: true,
    }))

    expect(html).toContain('能力成长')
    expect(html).toContain('综合能力')
    expect(html).toContain('61.0')
    expect(html).toContain('76.0')
    expect(html).toContain('可比题目正确率')
    expect(html).toContain('50.0%')
    expect(html).toContain('83.3%')
    expect(html).toContain('1分15秒')
    expect(html).toContain('早期 6 条 · 近期 6 条')
    expect(html).toContain('来源记录 attempt-1、attempt-2')
    expect(html).toContain('已排除 2 条非生产数据')
    expect(html).not.toContain('mock')
    expect(html).not.toContain('演示数据')
  })

  it('states insufficient data honestly instead of rendering fallback values', async () => {
    const html = await renderToString(createSSRApp(CapabilityGrowthPanel, {
      data: {
        ...realGrowth,
        overall: { baselineScore: null, currentScore: null, delta: null },
        dimensions: realGrowth.dimensions.map((dimension) => ({
          ...dimension,
          baselineScore: null,
          currentScore: null,
          delta: null,
          metrics: [],
          evidence: [],
        })),
        history: [],
        message: '暂无真实成长数据',
      },
    }))

    expect(html).toContain('暂无真实成长数据')
    expect(html).toContain('完成真实实验和练习后，这里会形成可追溯的成长证据')
    expect(html).not.toContain('0.0')
  })

  it('shows exactly which real experiment was accessed and exposes trace details', async () => {
    const engagement = realGrowth.dimensions.find((item) => item.key === 'engagement')!
    const html = await renderToString(createSSRApp(CapabilityGrowthPanel, {
      data: {
        ...realGrowth,
        dimensions: [{
          ...engagement,
          evidence: [{
            kind: 'LAB',
            title: 'SQL注入基础实验',
            detail: '访问 http://localhost:8091/index.php',
            occurredAt: '2026-07-25T00:48:42',
            sourceId: 'lab-real-1',
            sourceType: 'lab_session',
            labSessionId: 'lab-real-1',
            courseId: 1,
            moduleId: 1,
            taskId: null,
            moduleName: 'SQL注入基础实验',
            status: 'stopped',
            startedAt: '2026-07-25T00:48:42',
            endedAt: '2026-07-25T00:50:52',
            durationSeconds: 130,
            targetUrl: 'http://localhost:8091/index.php',
            containerName: 'sqli-lab-web-1',
            eventCount: 8,
            eventTypes: ['COMMAND_EXEC', 'LAB_START', 'LAB_STOP'],
          }],
        }],
      },
    }))

    expect(html).toContain('<details')
    expect(html).toContain('SQL注入基础实验')
    expect(html).toContain('访问 http://localhost:8091/index.php')
    expect(html).toContain('已结束')
    expect(html).toContain('2分10秒')
    expect(html).toContain('8 条事件')
    expect(html).toContain('sqli-lab-web-1')
    expect(html).toContain('lab-real-1')
    expect(html).toContain('COMMAND_EXEC')
    expect(html).not.toContain('已记录真实学习行为')
  })
})
