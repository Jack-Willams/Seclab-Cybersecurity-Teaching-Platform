export function trainingWaitMessage(elapsedSeconds: number, questionCount: number) {
  if (elapsedSeconds < 30) {
    return `正在从真实知识库生成 ${questionCount} 道训练题，已等待 ${elapsedSeconds} 秒`
  }
  return `模型仍在准备 ${questionCount} 道训练题，已等待 ${elapsedSeconds} 秒；最晚 45 秒会给出结果`
}

export function trainingGenerationErrorMessage(errorCode: string, requestTimedOut: boolean) {
  if (errorCode === 'QUESTION_SET_GENERATION_TIMEOUT' || requestTimedOut) {
    return '训练题准备超过 45 秒，请重试；本次没有保存半成品。'
  }
  if (errorCode === 'LLM_NOT_CONFIGURED') {
    return 'AI 出题服务尚未配置，请稍后再试。'
  }
  if (errorCode === 'KNOWLEDGE_CONTEXT_NOT_FOUND' || errorCode === 'MISSING_KNOWLEDGE_TARGET') {
    return '当前推荐缺少足够知识库上下文，暂时不能生成训练题。'
  }
  return '训练题准备失败，请稍后重试。'
}
