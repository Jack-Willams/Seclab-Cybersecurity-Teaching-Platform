<template>
  <div class="floating-chat" 
       :class="{ 'minimized': isMinimized, 'maximized': isMaximized }"
       :style="{ right: position.x + 'px', bottom: position.y + 'px' }">
    
    <!-- 拖动条 -->
    <div class="drag-handle" @mousedown="startDragging">
      <div class="flex items-center justify-between w-full px-2">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-sm">
            <i class="fas fa-shield-alt text-xs text-white"></i>
          </div>
          <div v-if="!isMinimized">
            <h3 class="text-sm font-bold">Sec<span class="text-primary">Lab</span> <span class="text-secondary">Agent</span></h3>
          </div>
        </div>
        <div class="flex gap-1">
          <button @click="toggleMinimize" class="btn btn-ghost btn-xs px-1">
            <i :class="isMinimized ? 'fas fa-expand-alt' : 'fas fa-minus'"></i>
          </button>
          <button @click="toggleMaximize" class="btn btn-ghost btn-xs px-1" v-if="!isMinimized">
            <i :class="isMaximized ? 'fas fa-compress-alt' : 'fas fa-expand'"></i>
          </button>
          <button @click="closeChat" class="btn btn-ghost btn-xs px-1 text-error" v-if="!isMinimized">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- 聊天内容区域 -->
    <div v-if="!isMinimized" class="chat-container">
      <!-- 消息区域 -->
      <div ref="chatContainer" class="messages-container">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="flex flex-col items-center justify-center h-full text-center text-base-content/50 py-4">
            <div class="w-12 h-12 rounded-full bg-gradient-to-br from-primary/20 to-secondary/20 
                      flex items-center justify-center mb-2 animate-pulse">
              <i class="fas fa-shield-alt text-xl text-primary"></i>
            </div>
            <h3 class="text-sm font-bold mb-1">
              SecLab AI 助手
            </h3>
            <div class="max-w-xs text-xs text-base-content/70 px-2">
              您的网络安全学习伙伴
            </div>
          </div>
        </div>
            
        <template v-else>
          <div
            v-for="(message, index) in messages"
            :key="index"
            class="mb-2" 
          >
            <!-- 用户消息 -->
            <div 
              v-if="message.role === 'user'"
              class="chat chat-end"
            >
              <div class="chat-image avatar">
                <div class="w-6 rounded-full ring ring-primary ring-offset-base-100 ring-offset-1">
                  <img 
                    src="https://api.dicebear.com/7.x/avataaars/svg?seed=user"
                    alt="用户"
                  />
                </div>
              </div>
              <div class="chat-bubble chat-bubble-primary text-xs">
                {{ message.content }}
              </div>
              <div class="chat-footer opacity-50 text-xs">
                <span>{{ formatTime(message.timestamp) }}</span>
              </div>
            </div>

            <!-- AI回复 -->
            <div 
              v-else
              class="chat chat-start"
            >
              <div class="chat-image avatar">
                <div class="w-6 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center shadow-md">
                  <i class="fas fa-shield-alt text-xs text-white"></i>
                </div>
              </div>
              <div class="chat-bubble assistant-bubble p-0 text-xs">
                <!-- ── 工具调用可视化卡片 ─────────────────────── -->
                <div
                  v-if="message.toolCalls && message.toolCalls.length > 0"
                  class="px-2 pt-2 space-y-1"
                >
                  <div
                    v-for="tc in message.toolCalls"
                    :key="tc.id"
                    class="rounded-lg border border-secondary/25 bg-base-200/60 p-2 text-xs"
                  >
                    <!-- 工具名 + 状态 -->
                    <div class="flex items-center gap-1.5 font-medium">
                      <span
                        v-if="tc.status === 'calling'"
                        class="loading loading-spinner loading-xs text-secondary"
                      ></span>
                      <i v-else class="fas fa-check-circle text-success" style="font-size:10px"></i>
                      <span class="text-secondary">
                        {{ TOOL_LABELS[tc.tool] || ('🔧 ' + tc.tool) }}
                      </span>
                      <span class="ml-auto text-base-content/40 font-normal">
                        {{ tc.status === 'calling' ? '调用中…' : '✔ 完成' }}
                      </span>
                    </div>
                    <!-- 参数摘要 -->
                    <div
                      v-if="tc.toolInput"
                      class="mt-1 rounded bg-base-300/50 px-1.5 py-0.5 font-mono text-base-content/50"
                    >
                      {{ tc.toolInput }}
                    </div>
                    <!-- 结果预览（截断） -->
                    <div
                      v-if="tc.observation"
                      class="mt-1 text-base-content/55 leading-snug"
                    >
                      {{ tc.observation.length > 140 ? tc.observation.slice(0, 140) + '…' : tc.observation }}
                    </div>
                  </div>
                </div>

                <!-- ── 思考过程 - 可折叠面板 ─────────────────── -->
                <div v-if="message.thinking && message.showThinking" class="collapse collapse-arrow bg-base-200/30 mb-2 rounded-lg">
                  <input type="checkbox" class="min-h-0" checked />
                  <div class="collapse-title py-1 px-2 min-h-0 flex items-center gap-2 text-base-content/70 text-xs font-medium">
                    <i class="fas fa-brain text-secondary text-xs"></i>
                    <span class="text-xs">思考过程</span>
                  </div>
                  <div class="collapse-content px-2 pt-0">
                    <div class="text-xs text-base-content/70 thinking-content p-2">
                      <div v-if="message.isStreaming">
                        <MarkdownRenderer :content="message.thinking || ''" />
                        <span v-if="message.thinking" class="inline-block ml-1">
                          <span class="loading loading-dots loading-xs"></span>
                        </span>
                      </div>
                      <div v-else>
                        <MarkdownRenderer :content="message.thinking || ''" />
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 回复内容 -->
                <div class="p-2" v-if="message.content || message.streamContent">
                  <div v-if="message.isStreaming">
                    <MarkdownRenderer :content="message.streamContent || ''" />
                  </div>
                  <div v-else>
                    <MarkdownRenderer :content="message.content" />
                  </div>
                </div>
                <div v-else class="flex items-center gap-2 p-2">
                  <span class="loading loading-dots loading-xs"></span>
                  <span class="text-xs">思考中...</span>
                </div>
              </div>
              <div class="chat-footer opacity-50 flex gap-1 text-xs">
                <span>{{ formatTime(message.timestamp) }}</span>
                <button 
                  v-if="message.content" 
                  class="opacity-50 hover:opacity-100" 
                  @click="copyToClipboard(message.content)"
                  title="复制内容"
                >
                  <i class="fas fa-copy"></i>
                </button>
              </div>
            </div>
          </div>
          <div class="h-6"></div>
        </template>
      </div>

      <!-- 输入区域 -->
      <div class="input-container">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-1 mb-1">
            <div class="flex items-center gap-1 text-xs text-base-content/50 flex-1">
              <i class="fas fa-robot text-secondary text-xs"></i>
              <span>SecLabAssistant · Dify Agent</span>
              <!-- 靶机运行中标识 -->
              <span v-if="labContainer" class="badge badge-success badge-xs ml-1">
                <i class="fas fa-circle text-[8px] mr-0.5"></i>运行中
              </span>
            </div>
            <!-- 一键提示按钮 -->
            <button
              v-if="labContainer"
              class="btn btn-xs btn-warning gap-1"
              @click="sendHint"
              :disabled="isLoading"
              title="让 Agent 读取 Docker 日志并给出提示"
            >
              <i class="fas fa-lightbulb text-xs"></i>
              一键提示
            </button>
          </div>
          <div class="join w-full">
            <textarea
              class="textarea textarea-bordered join-item flex-1 min-h-[40px] max-h-[80px] resize-none focus:outline-primary text-xs"
              placeholder="输入您的问题..."
              v-model="inputMessage"
              @keydown.enter.ctrl="handleSendMessage"
              ref="inputField"
            ></textarea>
          </div>
          <div class="flex justify-between items-center">
            <div class="text-xs text-base-content/60">
              Ctrl+Enter
            </div>
            <button
              class="btn btn-xs btn-primary"
              @click="handleSendMessage"
              :disabled="isLoading || !inputMessage.trim()"
            >
              <i class="fas fa-paper-plane mr-1"></i>
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import { currentLabContext } from '../composables/useLabState'
import { reportLearningEvent } from '../api'

// Dify SSE 事件类型
interface DifyChunk {
  event: string
  conversation_id?: string
  answer?: string
  message_id?: string
  id?: string
  thought?: string
  observation?: string
  tool?: string
  tool_input?: string  // 工具调用入参（JSON 字符串）
  message?: string
}

// 单次工具调用记录
interface ToolCall {
  id: string
  tool: string
  toolInput?: string   // 格式化后的入参摘要
  observation?: string // 工具返回结果
  status: 'calling' | 'done'
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  thinking?: string
  streamContent?: string
  isStreaming?: boolean
  showThinking?: boolean
  toolCalls?: ToolCall[]  // 该消息产生的工具调用列表
}

const props = defineProps({
  visible: {
    type: Boolean,
    default: true
  },
  compact: {
    type: Boolean,
    default: false
  },
  initialPosition: {
    type: Object,
    default: () => ({ x: 20, y: 20 })
  },
  /** 当前运行中的靶机容器名（空字符串=无靶机）*/
  labContainer: {
    type: String,
    default: ''
  },
  /** 父组件传入：true 时自动发送一键提示消息 */
  autoHint: {
    type: Boolean,
    default: false
  },
  /** 来自 iframe postMessage 的自定义提示文本（非空时自动发送）*/
  iframeHintPrompt: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'toggle-visibility', 'hint-sent'])

const labContextText = computed(() => {
  const context = currentLabContext.value
  const entries = [
    ['模块ID', context.moduleId],
    ['模块名称', context.moduleName],
    ['实验ID', context.experimentId],
    ['实验标题', context.experimentTitle],
    ['当前任务', context.currentTask],
    ['会话ID', context.labSessionId],
    ['容器名', context.containerName || context.currentLabContainer],
    ['靶机URL', context.targetMachineUrl || context.targetUrl],
    ['用户ID', context.userId],
    ['班级ID', context.classId],
    ['课程ID', context.courseId]
  ]
  return entries
    .filter(([, value]) => value !== undefined && value !== null && String(value).trim() !== '')
    .map(([label, value]) => `${label}: ${value}`)
    .join('\n')
})

function normalizeOptionalNumber(value: unknown) {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? numeric : null
}

function buildEventId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

async function persistAiInteractionEvent(userQuestion: string, assistantReply: string, toolCalls: ToolCall[]) {
  const context = currentLabContext.value
  await reportLearningEvent({
    event_id: buildEventId('evt-ai'),
    request_id: buildEventId('req-ai'),
    event_type: 'AI_INTERACTION',
    event_time: new Date().toISOString(),
    user_id: normalizeOptionalNumber(context.userId),
    class_id: normalizeOptionalNumber(context.classId),
    course_id: normalizeOptionalNumber(context.courseId),
    module_id: normalizeOptionalNumber(context.moduleId),
    task_id: null,
    question_id: null,
    lab_session_id: context.labSessionId || null,
    container_name: String(context.containerName || context.currentLabContainer || props.labContainer || '').trim() || null,
    target_url: String(context.targetMachineUrl || context.targetUrl || '').trim() || null,
    prompt: userQuestion,
    assistant_reply: assistantReply,
    message_role: 'user',
    used_context_injection: Boolean(labContextText.value),
    context: labContextText.value
      ? {
          moduleId: context.moduleId ?? null,
          moduleName: context.moduleName ?? null,
          experimentId: context.experimentId ?? null,
          experimentTitle: context.experimentTitle ?? null,
          currentTask: context.currentTask ?? null,
          labSessionId: context.labSessionId ?? null,
          containerName: context.containerName || context.currentLabContainer || props.labContainer || null,
          targetUrl: context.targetMachineUrl || context.targetUrl || null,
          userId: context.userId ?? null,
          classId: context.classId ?? null,
          courseId: context.courseId ?? null,
        }
      : null,
    tool_calls: toolCalls.map((toolCall) => ({
      id: toolCall.id,
      tool: toolCall.tool,
      tool_input: toolCall.toolInput || '',
      observation: toolCall.observation || '',
      status: toolCall.status,
    })),
  })
}

// ── 一键提示 ─────────────────────────────────────────────────────
const sendHint = () => {
  const container = props.labContainer || 'sqli-lab-web-1'
  const contextText = labContextText.value ? `\n\n当前实验上下文：\n${labContextText.value}` : ''
  inputMessage.value =
    `请帮我读取 ${container} 容器的最新50行日志，结合当前实验上下文分析我的操作进展，并给出针对性的提示。${contextText}`
  handleSendMessage()
  emit('hint-sent')
}

// 监听父组件 autoHint 变化（父组件从弹窗触发）
watch(() => props.autoHint, (val) => {
  if (val) sendHint()
})

// 监听来自 iframe postMessage 的提示文本
watch(() => props.iframeHintPrompt, (prompt) => {
  if (prompt) {
    inputMessage.value = prompt
    handleSendMessage()
    emit('hint-sent')
  }
})

// 悬浮窗状态
const isMinimized = ref(false)
const isMaximized = ref(false)

const position = ref(props.initialPosition)
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })

// 聊天状态
const messages = ref<Message[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)
const inputField = ref<HTMLTextAreaElement | null>(null)
// Agent 服务地址（指向本地 FastAPI）
const AGENT_BASE_URL = import.meta.env.VITE_AGENT_BASE_URL || (import.meta.env.DEV ? 'http://localhost:8010' : '')

// 会话 ID（保持多轮对话上下文）
const conversationId = ref<string>('')

// 工具名称 → 可读标签映射
const TOOL_LABELS: Record<string, string> = {
  'get_container_status': '📊 获取容器状态',
  'get_container_logs':   '📋 读取容器日志',
  'exec_in_container':    '⚡ 执行容器指令',
  'stop_container':       '🛑 停止容器',
}

// 格式化工具入参（JSON → 人类可读摘要）
const formatToolInput = (raw: string): string => {
  try {
    const obj = JSON.parse(raw)
    // 优先显示 container_name，再显示其他键
    const parts: string[] = []
    if (obj.container_name) parts.push(`容器: ${obj.container_name}`)
    if (obj.tail)           parts.push(`最近 ${obj.tail} 行`)
    if (obj.command)        parts.push(`命令: ${obj.command}`)
    if (obj.name)           parts.push(`名称: ${obj.name}`)
    return parts.length ? parts.join(' | ') : raw
  } catch {
    return raw
  }
}

// 格式化时间
const formatTime = (date: Date) => {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// 复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
    .then(() => {
      console.log('复制成功')
    })
    .catch(err => {
      console.error('复制失败:', err)
    })
}

// 滚动到底部
const scrollToBottom = () => {
  if (chatContainer.value) {
    setTimeout(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight + 100
      }
    }, 100)
  }
}

// ── 调用 Dify Agent（SSE 流式）──────────────────────────────
const callDifyAgent = async (userQuestion: string, messageIndex: number) => {
  messages.value[messageIndex].isStreaming = true
  messages.value[messageIndex].streamContent = ''
  messages.value[messageIndex].showThinking = true
  messages.value[messageIndex].thinking = ''

  let completeResponse = ''
  let completeThinking = ''

  try {
    const response = await fetch(`${AGENT_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: userQuestion,
        conversation_id: conversationId.value,
        user: 'student',
        inputs: {}
      })
    })

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''                       // 保留不完整行

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const raw = trimmed.slice(5).trim()
        if (!raw || raw === '[DONE]') continue

        try {
          const chunk = JSON.parse(raw) as DifyChunk

          // 保存 conversation_id 用于多轮对话
          if (chunk.conversation_id) {
            conversationId.value = chunk.conversation_id
          }

          // Agent 思考步骤（tool 调用过程）
          if (chunk.event === 'agent_thought') {
            // 纯思考文字（无工具调用时）
            if (chunk.thought && !chunk.tool) {
              completeThinking += chunk.thought + '\n'
              messages.value[messageIndex].thinking = completeThinking
            }

            // 工具调用 → 可视化卡片
            if (chunk.tool) {
              const tcId = chunk.id || `tc-${Date.now()}-${Math.random()}`
              const toolCalls = messages.value[messageIndex].toolCalls || []
              const existing = toolCalls.find((tc: ToolCall) => tc.id === tcId)

              if (!existing) {
                // 第一次收到此工具调用（calling 状态）
                toolCalls.push({
                  id: tcId,
                  tool: chunk.tool,
                  toolInput: chunk.tool_input ? formatToolInput(chunk.tool_input) : '',
                  observation: chunk.observation || '',
                  status: chunk.observation ? 'done' : 'calling'
                } as ToolCall)
              } else {
                // 第二次收到（含 observation，done 状态）
                if (chunk.observation) {
                  existing.observation = chunk.observation
                  existing.status = 'done'
                }
              }
              messages.value[messageIndex].toolCalls = toolCalls
              nextTick(() => scrollToBottom())
            }
          }

          // 流式回答文本片段
          if (chunk.event === 'agent_message' || chunk.event === 'message') {
            const delta = chunk.answer ?? ''
            if (delta) {
              completeResponse += delta
              messages.value[messageIndex].streamContent = completeResponse
              nextTick(() => scrollToBottom())
            }
          }

          // 消息结束
          if (chunk.event === 'message_end') {
            messages.value[messageIndex].content = completeResponse
            messages.value[messageIndex].isStreaming = false
          }

          // 错误事件
          if (chunk.event === 'error') {
            throw new Error(chunk.message || '未知错误')
          }
        } catch (_) {
          // JSON 解析失败时跳过该行
        }
      }
    }

    // 兜底：流结束但未收到 message_end
    if (messages.value[messageIndex].isStreaming) {
      messages.value[messageIndex].content = completeResponse || '（无回复）'
      messages.value[messageIndex].isStreaming = false
    }

  } catch (error: any) {
    messages.value[messageIndex].streamContent = ''
    messages.value[messageIndex].content = `连接 Agent 服务失败：${error.message || '未知错误'}`
    messages.value[messageIndex].isStreaming = false
  }

  const finalReply =
    messages.value[messageIndex].content ||
    messages.value[messageIndex].streamContent ||
    completeResponse

  try {
    await persistAiInteractionEvent(userQuestion, finalReply, messages.value[messageIndex].toolCalls || [])
  } catch (eventError) {
    console.warn('AI interaction learning event report failed:', eventError)
  }
}

// 发送消息
const handleSendMessage = () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  // 如果窗口最小化，先还原
  if (isMinimized.value) {
    isMinimized.value = false
  }

  const newMessage: Message = {
    role: 'user',
    content: inputMessage.value,
    timestamp: new Date()
  }

  messages.value.push(newMessage)
  const userQuestion = inputMessage.value
  inputMessage.value = ''
  
  // 自动滚动到底部
  scrollToBottom()
  
  // 添加加载状态的消息
  isLoading.value = true
  const responseIndex = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    timestamp: new Date(),
    toolCalls: []
  })
  
  // 确保滚动到底部
  scrollToBottom()
  
  // 调用 Dify Agent
  callDifyAgent(userQuestion, responseIndex)
    .finally(() => {
      isLoading.value = false
      // 回答完成后再次滚动到底部
      scrollToBottom()
    })
}

// 悬浮窗控制函数
const toggleMinimize = () => {
  isMinimized.value = !isMinimized.value
  if (isMinimized.value) {
    isMaximized.value = false
  }
}

const toggleMaximize = () => {
  isMaximized.value = !isMaximized.value
}

const closeChat = () => {
  emit('close')
}

// 拖动功能
const startDragging = (event: MouseEvent) => {
  // 如果点击的是控制按钮，不启动拖动
  if ((event.target as HTMLElement).closest('button')) {
    return
  }
  
  isDragging.value = true
  const chatElement = (event.currentTarget as HTMLElement).parentElement as HTMLElement
  const rect = chatElement.getBoundingClientRect()
  
  dragOffset.value = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
  
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDragging)
}

const onDrag = (event: MouseEvent) => {
  if (!isDragging.value) return
  
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const chatElement = document.querySelector('.floating-chat') as HTMLElement
  const width = chatElement.offsetWidth
  const height = chatElement.offsetHeight
  
  // 计算新位置，确保不超出视口
  const newX = Math.max(0, Math.min(viewportWidth - width, event.clientX - dragOffset.value.x))
  const newY = Math.max(0, Math.min(viewportHeight - height, event.clientY - dragOffset.value.y))
  
  // 转换为right和bottom定位
  position.value = {
    x: viewportWidth - newX - width,
    y: viewportHeight - newY - height
  }
}

const stopDragging = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDragging)
}

// 监听消息变化
watch(messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

// 从localStorage加载聊天记录
const loadMessagesFromStorage = () => {
  try {
    const savedMessages = localStorage.getItem('chatMessages')
    if (savedMessages) {
      // 需要将JSON字符串中的日期字符串转换回Date对象
      const parsedMessages = JSON.parse(savedMessages, (key, value) => {
        if (key === 'timestamp' && value) {
          return new Date(value)
        }
        return value
      })
      messages.value = parsedMessages
    }
  } catch (error) {
    console.error('加载聊天记录失败:', error)
  }
}

// 组件挂载
onMounted(() => {
  // 加载聊天记录
  loadMessagesFromStorage()
  
  // 聚焦输入框
  if (!isMinimized.value) {
    inputField.value?.focus()
  }
  
  // 监听窗口大小变化，确保悬浮窗不超出视口
  window.addEventListener('resize', () => {
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    const chatElement = document.querySelector('.floating-chat') as HTMLElement
    
    if (chatElement) {
      const width = chatElement.offsetWidth
      const height = chatElement.offsetHeight
      
      position.value = {
        x: Math.min(position.value.x, viewportWidth - width),
        y: Math.min(position.value.y, viewportHeight - height)
      }
    }
  })
})
</script>

<style scoped>
.floating-chat {
  position: fixed;
  display: flex;
  flex-direction: column;
  width: 350px;
  height: 450px;
  background-color: var(--fallback-b1,oklch(var(--b1)/var(--tw-bg-opacity, 1)));
  border-radius: 0.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  z-index: 1000;
  overflow: hidden;
  border: 1px solid var(--b3);
}

.floating-chat.minimized {
  width: 200px;
  height: 40px;
}

.floating-chat.maximized {
  width: 450px;
  height: 650px;
}

.drag-handle {
  height: 40px;
  width: 100%;
  cursor: move;
  display: flex;
  align-items: center;
  background-color: var(--b2);
  border-bottom: 1px solid var(--b3);
  user-select: none;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100% - 40px);
}

.messages-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 0.5rem;
  background-color: var(--b1, #131414);
}

.input-container {
  padding: 0.5rem;
  border-top: 1px solid var(--b3);
  background-color: var(--b2);
}

:deep(.chat-bubble) {
  max-width: 85%;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.assistant-bubble {
  background-color: hsl(var(--b1));
  color: hsl(var(--bc));
  border: 1px solid hsl(var(--b3));
}

.assistant-bubble :deep(.markdown-body),
.assistant-bubble :deep(.markdown-body p),
.assistant-bubble :deep(.markdown-body li),
.assistant-bubble :deep(.markdown-body h1),
.assistant-bubble :deep(.markdown-body h2),
.assistant-bubble :deep(.markdown-body h3),
.assistant-bubble :deep(.markdown-body blockquote) {
  color: hsl(var(--bc));
}

.assistant-bubble :deep(.markdown-body code),
.assistant-bubble :deep(.markdown-body pre) {
  background-color: hsl(var(--b2));
  color: hsl(var(--bc));
}

:deep(.chat-bubble a) {
  color: var(--p);
  text-decoration: underline;
}

:deep(.chat-bubble pre) {
  background-color: hsl(var(--n) / 0.1);
  padding: 0.5rem;
  border-radius: 0.3rem;
  overflow-x: auto;
  margin: 0.5rem 0;
  font-size: 0.7rem;
}

:deep(.chat-bubble code) {
  background-color: hsl(var(--n) / 0.1);
  padding: 0.1rem 0.2rem;
  border-radius: 0.2rem;
  font-size: 0.7rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
}
</style> 
