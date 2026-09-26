/**
 * useLabState - 全局靶机运行状态（跨组件共享）
 *
 * 用于 Module 页面 → FloatingChatButton / FloatingChat 的状态传递：
 *   - currentLabContainer : 当前运行的靶机容器名（空字符串=未启动）
 *   - labStartTime        : 靶机启动时刻
 *   - setLabRunning(name) : 靶机启动时调用
 *   - clearLab()          : 靶机关闭时调用
 */
import { ref } from 'vue'

// 容器名 → 对人类友好的标签
export const CONTAINER_NAMES: Record<number, string> = {
  1: 'sqli-lab-web-1',
  2: 'xss-lab-web-1',
  3: 'csrf-lab-web-1',
  4: 'command-inject-web-1',
  5: 'file-upload-lab-web-1',
  6: 'directory-traversal-lab-web-1',
  15: 'stack-overflow-lab-web-1',
  16: 'protocol-analysis-lab-web-1',
}

/** 当前靶机容器名，空字符串表示未启动 */
export const currentLabContainer = ref<string>('')

/** 靶机启动时刻 */
export const labStartTime = ref<Date | null>(null)

/** 实验是否进行中 */
export const isLabRunning = ref<boolean>(false)

export interface LabEvent {
  event_id: string
  event_type: string
  event_time: string
  [key: string]: any
}

export interface LabContext {
  moduleId?: number | string | null
  moduleName?: string
  experimentId?: number | string | null
  experimentTitle?: string
  currentTask?: string
  labSessionId?: string
  containerName?: string
  currentLabContainer?: string
  targetUrl?: string
  targetMachineUrl?: string
  userId?: number | string | null
  classId?: number | string | null
  courseId?: number | string | null
}

const labEvents = ref<LabEvent[]>([])
let labSessionId = ''
export const currentLabContext = ref<LabContext>({})

function generateId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`
}

/** 靶机启动 */
export function setLabRunning(containerName: string, sessionId?: string) {
  currentLabContainer.value = containerName
  labStartTime.value = new Date()
  isLabRunning.value = true
  labSessionId = sessionId || `lab-${Date.now()}`
  currentLabContext.value = {
    ...currentLabContext.value,
    labSessionId,
    containerName,
    currentLabContainer: containerName
  }
  labEvents.value = [
    {
      event_id: generateId('evt-lab-start'),
      event_type: 'LAB_START',
      event_time: new Date().toISOString(),
      container_name: containerName,
      extra: {}
    }
  ]
}

/** 靶机关闭 */
export function clearLab() {
  currentLabContainer.value = ''
  labStartTime.value = null
  isLabRunning.value = false
  labSessionId = ''
  currentLabContext.value = {}
  labEvents.value = []
}

export function setLabSessionId(sessionId: string) {
  labSessionId = sessionId
  currentLabContext.value = {
    ...currentLabContext.value,
    labSessionId: sessionId
  }
}

export function setLabContext(context: Partial<LabContext>) {
  currentLabContext.value = {
    ...currentLabContext.value,
    ...context
  }
}

export function getLabSessionId() {
  return labSessionId
}

export function addLabEvent(event: Partial<LabEvent> & { event_type: string }) {
  labEvents.value.push({
    event_id: event.event_id || generateId('evt'),
    event_type: event.event_type,
    event_time: event.event_time || new Date().toISOString(),
    ...event
  })
}

export function getLabEvents() {
  return [...labEvents.value]
}

export function getLabDurationSeconds() {
  if (!labStartTime.value) return 0
  return Math.round((Date.now() - labStartTime.value.getTime()) / 1000)
}
