<template>
  <div>
    <!-- ① 悬浮按钮（聊天窗口关闭时显示） -->
    <button
      v-if="!chatVisible"
      @click="openChat"
      class="fixed bottom-6 right-6 btn btn-circle btn-primary shadow-lg hover:shadow-xl transition-all duration-300 z-30 w-14 h-14"
      :title="currentLabContainer ? `当前靶机: ${currentLabContainer}` : 'AI 助手'"
    >
      <i class="fas fa-comment-dots text-xl"></i>
      <!-- 靶机运行中小圆点 -->
      <span
        v-if="currentLabContainer"
        class="absolute top-0 right-0 w-3 h-3 bg-green-400 rounded-full border-2 border-white animate-pulse"
      ></span>
    </button>

    <!-- ② 聊天窗口 -->
    <FloatingChat
      v-if="chatVisible"
      :initial-position="chatPosition"
      :compact="compact"
      :lab-container="currentLabContainer"
      :auto-hint="pendingHint"
      :iframe-hint-prompt="iframeHintPrompt"
      @close="chatVisible = false"
      @hint-sent="pendingHint = false; iframeHintPrompt = ''"
    />

    <!-- ③ 1分钟倒计时提示弹窗 -->
    <div
      v-if="showHintModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <div class="bg-base-100 rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4 border border-primary/30">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
            <i class="fas fa-robot text-primary text-lg"></i>
          </div>
          <div>
            <p class="font-bold text-base-content">SecLab 助手</p>
            <p class="text-xs text-base-content/60">实验进行中</p>
          </div>
        </div>
        <p class="text-sm text-base-content/80 mb-5 leading-relaxed">
          你已经在靶机中操作了 1 分钟，需要 AI 助手帮你分析当前操作并给出提示吗？
        </p>
        <div class="flex gap-3">
          <button class="btn btn-primary btn-sm flex-1" @click="acceptHint">
            <i class="fas fa-lightbulb mr-1"></i>需要提示
          </button>
          <button class="btn btn-ghost btn-sm flex-1" @click="dismissHint">
            继续自己尝试
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import FloatingChat from './FloatingChat.vue'
import { currentLabContainer, labStartTime, setLabRunning } from '../composables/useLabState'

const props = defineProps({
  compact: { type: Boolean, default: true },
  defaultPosition: { type: Object, default: () => ({ x: 20, y: 20 }) }
})

const chatVisible   = ref(false)
const chatPosition  = ref(props.defaultPosition)
const showHintModal = ref(false)

// 一键提示 pending：打开聊天后自动发送
const pendingHint     = ref(false)
// 来自 iframe postMessage 的提示文本（含关卡信息）
const iframeHintPrompt = ref('')

let hintTimer: ReturnType<typeof setTimeout> | null = null

/** 打开聊天窗口（可选：携带自动提示标志） */
function openChat(withHint = false) {
  if (withHint) pendingHint.value = true
  chatVisible.value = true
}

/** 弹窗"需要提示" */
function acceptHint() {
  showHintModal.value = false
  openChat(true)
}

/** 弹窗"继续自己" */
function dismissHint() {
  showHintModal.value = false
}

/** 监听靶机启动 → 自动展开聊天 + 启动1分钟倒计时 */
watch(currentLabContainer, (name) => {
  if (hintTimer) { clearTimeout(hintTimer); hintTimer = null }
  if (name) {
    // 靶机启动：自动打开助手窗口
    chatVisible.value = true
    // 1 分钟后弹提示（仅当聊天窗口关闭时才弹）
    hintTimer = setTimeout(() => {
      if (!chatVisible.value) showHintModal.value = true
      else {
        // 窗口开着就直接在聊天里发提示
        pendingHint.value = true
      }
    }, 60_000)
  }
})

// ── Listen for postMessage events from SQLi lab iframe ────────
function handleLabMessage(evt: MessageEvent) {
  const data = evt.data
  if (!data || typeof data !== 'object') return

  // Lab page opened → register container
  if (data.type === 'lab_opened' && data.container) {
    setLabRunning(data.container)
  }

  // Student clicked "获取提示" inside lab page
  if (data.type === 'hint_request') {
    const prompt: string = data.prompt ||
      `请分析 ${data.container || 'sqli-lab-web-1'} 容器的 Apache 日志，判断学生在"${data.levelTitle}"的当前进度，给出阶梯式提示。`
    iframeHintPrompt.value = prompt
    // Open chat and pre-fill the hint prompt
    pendingHint.value = false          // reset generic flag
    chatVisible.value = true
    // Small delay so FloatingChat has time to mount
    setTimeout(() => {
      iframeHintPrompt.value = prompt  // FloatingChat watches this prop
    }, 200)
  }
}

onMounted(() => window.addEventListener('message', handleLabMessage))
onUnmounted(() => {
  if (hintTimer) clearTimeout(hintTimer)
  window.removeEventListener('message', handleLabMessage)
})
</script>
