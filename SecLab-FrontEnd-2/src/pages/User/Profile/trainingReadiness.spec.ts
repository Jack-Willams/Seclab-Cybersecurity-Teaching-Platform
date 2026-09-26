import { describe, expect, it } from 'vitest'

import { trainingGenerationErrorMessage, trainingWaitMessage } from './trainingReadiness'

describe('training readiness presentation', () => {
  it('shows elapsed time and a realistic expectation while generating', () => {
    expect(trainingWaitMessage(12, 7)).toBe('正在从真实知识库生成 7 道训练题，已等待 12 秒')
    expect(trainingWaitMessage(31, 7)).toBe('模型仍在准备 7 道训练题，已等待 31 秒；最晚 45 秒会给出结果')
  })

  it('turns backend and browser timeouts into a retryable message', () => {
    expect(trainingGenerationErrorMessage('QUESTION_SET_GENERATION_TIMEOUT', false))
      .toBe('训练题准备超过 45 秒，请重试；本次没有保存半成品。')
    expect(trainingGenerationErrorMessage('', true))
      .toBe('训练题准备超过 45 秒，请重试；本次没有保存半成品。')
  })
})
