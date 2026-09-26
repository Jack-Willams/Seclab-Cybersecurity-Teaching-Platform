<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
// @ts-expect-error — @novnc/novnc 没有官方 TypeScript 声明
import RFB from '@novnc/novnc'

interface Props {
  wsUrl: string
  password?: string
  title?: string
  viewOnly?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  password: '',
  title: '操作环境',
  viewOnly: false,
})

const screenRef = ref<HTMLDivElement | null>(null)
const status = ref<'connecting' | 'connected' | 'disconnected'>('connecting')
const errorMsg = ref<string>('')
let rfb: any = null
const remoteClipboard = ref<string>('')
const clipboardNotice = ref<string>('')
const manualPasteVisible = ref(false)
const manualPasteText = ref('')
let resizeObserver: ResizeObserver | null = null
let resizeDebounce: number | null = null
let clipboardNoticeTimer: number | null = null

const KEYSYM_CONTROL_LEFT = 0xffe3
const KEYSYM_V = 0x0076

function tearDown() {
  if (resizeObserver) {
    try { resizeObserver.disconnect() } catch { /* swallow */ }
    resizeObserver = null
  }
  if (resizeDebounce !== null) {
    window.clearTimeout(resizeDebounce)
    resizeDebounce = null
  }
  if (clipboardNoticeTimer !== null) {
    window.clearTimeout(clipboardNoticeTimer)
    clipboardNoticeTimer = null
  }
  if (rfb) {
    try { rfb.disconnect() } catch { /* swallow */ }
    rfb = null
  }
  if (screenRef.value) screenRef.value.innerHTML = ''
}

function connect() {
  if (!screenRef.value || !props.wsUrl) return
  tearDown()
  status.value = 'connecting'
  errorMsg.value = ''

  rfb = new RFB(screenRef.value, props.wsUrl, {
    credentials: { password: props.password },
  })
  // 让远程桌面分辨率跟随面板，避免本地缩放裁掉底部任务栏。
  rfb.scaleViewport = false
  rfb.resizeSession = true
  rfb.clipViewport = false
  rfb.viewOnly = props.viewOnly
  // 不解析视频质量，简化首次接入
  rfb.background = '#000'

  rfb.addEventListener('connect', () => {
    status.value = 'connected'
    scheduleResizeBurst()
  })
  rfb.addEventListener('disconnect', (e: any) => {
    status.value = 'disconnected'
    if (e?.detail && !e.detail.clean) {
      errorMsg.value = '连接异常断开'
    }
  })
  rfb.addEventListener('securityfailure', (e: any) => {
    errorMsg.value = `认证失败：${e?.detail?.reason || '密码错误'}`
  })
  rfb.addEventListener('credentialsrequired', () => {
    // 默认 props.password 已经透传过；若仍被要求，提示让上层重启
    errorMsg.value = '需要 VNC 密码，请联系管理员'
  })
  rfb.addEventListener('clipboard', (e: any) => {
    const text = e?.detail?.text || ''
    remoteClipboard.value = text
    if (text && navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => { /* 用户没授权 */ })
    }
  })

  resizeObserver = new ResizeObserver(() => {
    if (resizeDebounce !== null) window.clearTimeout(resizeDebounce)
    resizeDebounce = window.setTimeout(() => {
      window.dispatchEvent(new Event('resize'))
      resizeDebounce = null
    }, 150)
  })
  resizeObserver.observe(screenRef.value)
}

function scheduleResizeBurst() {
  for (const delay of [0, 250, 800]) {
    window.setTimeout(() => {
      if (!rfb || !screenRef.value) return
      window.dispatchEvent(new Event('resize'))
    }, delay)
  }
}

function showClipboardNotice(message: string) {
  clipboardNotice.value = message
  if (clipboardNoticeTimer !== null) window.clearTimeout(clipboardNoticeTimer)
  clipboardNoticeTimer = window.setTimeout(() => {
    clipboardNotice.value = ''
    clipboardNoticeTimer = null
  }, 1800)
}

function sendCtrlV() {
  if (!rfb || status.value !== 'connected') return
  rfb.focus?.({ preventScroll: true })
  rfb.sendKey(KEYSYM_CONTROL_LEFT, 'ControlLeft', true)
  rfb.sendKey(KEYSYM_V, 'KeyV', true)
  rfb.sendKey(KEYSYM_V, 'KeyV', false)
  rfb.sendKey(KEYSYM_CONTROL_LEFT, 'ControlLeft', false)
}

function sleep(ms: number) {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

async function pasteToRemote() {
  if (!rfb || status.value !== 'connected') return
  if (!navigator.clipboard || !window.isSecureContext) {
    manualPasteVisible.value = true
    showClipboardNotice('请在下方输入框粘贴内容')
    return
  }
  try {
    const text = await navigator.clipboard.readText()
    if (!text) {
      showClipboardNotice('本地剪贴板为空')
      return
    }
    rfb.clipboardPasteFrom(text)
    await sleep(120)
    sendCtrlV()
    showClipboardNotice('已发送粘贴')
  } catch {
    manualPasteVisible.value = true
    showClipboardNotice('浏览器限制读取剪贴板，请手动粘贴')
  }
}

async function typeClipboardToRemote() {
  if (!rfb || status.value !== 'connected') return
  if (!navigator.clipboard || !window.isSecureContext) {
    manualPasteVisible.value = true
    showClipboardNotice('请在下方输入框粘贴内容')
    return
  }
  try {
    const text = await navigator.clipboard.readText()
    if (!text) {
      showClipboardNotice('本地剪贴板为空')
      return
    }
    rfb.focus?.({ preventScroll: true })
    for (const char of text) {
      const keysym = char.codePointAt(0)
      if (!keysym) continue
      rfb.sendKey(keysym)
      await sleep(4)
    }
    showClipboardNotice('已输入剪贴板文本')
  } catch {
    manualPasteVisible.value = true
    showClipboardNotice('浏览器限制读取剪贴板，请手动粘贴')
  }
}

async function sendManualPaste() {
  if (!rfb || status.value !== 'connected') return
  const text = manualPasteText.value
  if (!text) {
    showClipboardNotice('输入内容为空')
    return
  }
  rfb.clipboardPasteFrom(text)
  await sleep(120)
  sendCtrlV()
  showClipboardNotice('已发送粘贴内容')
}

function hideManualPaste() {
  manualPasteVisible.value = false
}

async function copyFromRemote() {
  if (remoteClipboard.value && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(remoteClipboard.value)
      showClipboardNotice('已复制远程剪贴板')
    } catch {
      showClipboardNotice('写入剪贴板失败')
    }
  } else {
    showClipboardNotice('远程剪贴板为空')
  }
}

function reconnect() { connect() }

onMounted(connect)
onBeforeUnmount(tearDown)
watch(() => props.wsUrl, () => connect())
</script>

<template>
  <div class="flex flex-col w-full h-full min-h-0 overflow-hidden bg-base-300">
    <!-- 顶栏 -->
    <div class="flex items-center justify-between px-3 py-1 bg-base-200 border-b border-base-300 text-xs">
      <div class="flex items-center gap-2">
        <i class="fas fa-desktop opacity-60"></i>
        <span class="font-medium">{{ title }}</span>
        <span
          class="badge badge-xs"
          :class="{
            'badge-warning': status === 'connecting',
            'badge-success': status === 'connected',
            'badge-error': status === 'disconnected',
          }"
        >
          {{ status === 'connecting' ? '连接中' : status === 'connected' ? '已连接' : '已断开' }}
        </span>
      </div>
      <div class="flex items-center gap-1">
        <span v-if="clipboardNotice" class="text-[11px] text-base-content/60 mr-1">
          {{ clipboardNotice }}
        </span>
        <button
          v-if="status === 'connected'"
          class="btn btn-ghost btn-xs"
          @click="copyFromRemote"
          title="复制远程剪贴板"
        >
          <i class="fas fa-copy"></i>
        </button>
        <button
          v-if="status === 'connected'"
          class="btn btn-ghost btn-xs"
          @click="pasteToRemote"
          title="粘贴本地剪贴板到远程焦点"
        >
          <i class="fas fa-paste"></i>
        </button>
        <button
          v-if="status === 'connected'"
          class="btn btn-ghost btn-xs"
          @click="typeClipboardToRemote"
          title="直接输入本地剪贴板文本"
        >
          <i class="fas fa-keyboard"></i>
        </button>
        <button class="btn btn-ghost btn-xs" @click="reconnect" title="重连">
          <i class="fas fa-sync-alt"></i>
        </button>
      </div>
    </div>

    <!-- 画布 -->
    <div class="relative flex-1 min-h-0 overflow-auto">
      <div ref="screenRef" class="w-full h-full"></div>

      <div
        v-if="manualPasteVisible && status === 'connected'"
        class="absolute left-3 right-3 bottom-3 z-20 flex items-center gap-2 rounded bg-base-100/95 p-2 shadow-lg border border-base-300"
      >
        <input
          v-model="manualPasteText"
          class="input input-bordered input-xs flex-1 font-mono"
          placeholder="在这里粘贴要发送到操作环境的内容"
          @keydown.enter.prevent="sendManualPaste"
        />
        <button class="btn btn-primary btn-xs" @click="sendManualPaste">
          发送
        </button>
        <button class="btn btn-ghost btn-xs" @click="hideManualPaste">
          关闭
        </button>
      </div>

      <div
        v-if="status === 'disconnected'"
        class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-base-100/80 backdrop-blur-sm"
      >
        <i class="fas fa-plug-circle-xmark text-5xl text-error"></i>
        <div class="text-center">
          <h3 class="font-semibold">连接已断开</h3>
          <p class="text-xs text-base-content/70">{{ errorMsg || '与操作环境的连接已中断' }}</p>
        </div>
        <button class="btn btn-primary btn-sm" @click="reconnect">
          <i class="fas fa-sync-alt mr-1"></i>重新连接
        </button>
      </div>

      <div
        v-else-if="status === 'connecting'"
        class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-base-100/40"
      >
        <span class="loading loading-spinner loading-md"></span>
        <span class="text-xs text-base-content/70">正在连接桌面…</span>
      </div>
    </div>
  </div>
</template>
