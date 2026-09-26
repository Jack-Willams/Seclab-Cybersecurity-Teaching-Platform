<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { avatarUrl, getScoreboard, type ScoreboardItemDto } from '../../../api'
import { getStoredCurrentUser, getStoredStudentNumber } from '../../../auth'

const REFRESH_INTERVAL_MS = 30_000

const items = ref<ScoreboardItemDto[]>([])
const updatedAt = ref('')
const source = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const classFilter = ref('')
const currentUserId = ref<number | null>(null)
const currentStudentNumber = ref('')
let refreshTimer: number | undefined

const classOptions = computed(() => {
  const names = items.value
    .map((item) => item.className?.trim())
    .filter((name): name is string => Boolean(name))
  return [...new Set(names)]
})

const filteredItems = computed(() => {
  if (!classFilter.value) return items.value
  return items.value.filter((item) => item.className === classFilter.value)
})

const currentUser = computed(() => {
  if (!items.value.length) return null
  const studentNumber = currentStudentNumber.value.trim()
  return items.value.find((item) => {
    if (currentUserId.value && item.userId === currentUserId.value) return true
    if (studentNumber && item.studentNumber === studentNumber) return true
    return false
  }) || null
})

const topThree = computed(() => items.value.slice(0, 3))

const currentUserLevel = computed(() => {
  const score = currentUser.value?.overallScore || 0
  return Math.max(1, Math.floor(score / 20))
})

function syncCurrentUserIdentity() {
  const stored = getStoredCurrentUser()
  currentUserId.value = stored?.userId || null
  currentStudentNumber.value = stored?.studentNumber || getStoredStudentNumber() || ''
}

async function loadScoreboard() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    // 名单以教学班为准，一个班可能几十人，取够整班的量
    const response = await getScoreboard(300)
    items.value = response.items || []
    updatedAt.value = response.updatedAt || ''
    source.value = response.source || ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '排行榜加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

// 后端 avatarUrl 字段带回来的是 user_image 原值（文件名），要拼成图片服务地址才能当 src
function studentAvatar(item: ScoreboardItemDto) {
  return avatarUrl(item.avatarUrl)
}

function isCurrentUser(item: ScoreboardItemDto) {
  const studentNumber = currentStudentNumber.value.trim()
  if (currentUserId.value && item.userId === currentUserId.value) return true
  if (studentNumber && item.studentNumber === studentNumber) return true
  return false
}

function formatDateTime(value?: string | null) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatScore(value?: number | null) {
  if (value === null || value === undefined) return '--'
  return Number(value).toFixed(1)
}

function rankClass(rank: number) {
  if (rank === 1) return 'bg-warning text-warning-content'
  if (rank === 2) return 'bg-base-300 text-base-content'
  if (rank === 3) return 'bg-accent text-accent-content'
  return 'bg-base-200 text-base-content'
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    loadScoreboard()
  }
}

onMounted(() => {
  syncCurrentUserIdentity()
  loadScoreboard()
  refreshTimer = window.setInterval(loadScoreboard, REFRESH_INTERVAL_MS)
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<template>
  <div class="container-fluid overflow-x-hidden px-4 py-6">
    <section class="mb-6 rounded-lg bg-base-100 p-6 shadow">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 class="text-2xl font-bold">排行榜</h1>
          <p class="mt-1 text-sm text-base-content/60">
            数据来自最新学习画像和生成题作答记录
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <select v-model="classFilter" class="select select-bordered select-sm min-w-40">
            <option value="">全部班级</option>
            <option v-for="className in classOptions" :key="className" :value="className">
              {{ className }}
            </option>
          </select>
          <button class="btn btn-primary btn-sm gap-2" :disabled="isLoading" @click="loadScoreboard">
            <i class="fas fa-sync-alt" :class="{ 'animate-spin': isLoading }"></i>
            刷新
          </button>
        </div>
      </div>

      <div class="mt-4 grid gap-3 md:grid-cols-3">
        <div class="rounded-lg bg-base-200 p-4">
          <div class="text-sm text-base-content/60">当前排名</div>
          <div class="mt-1 text-3xl font-bold text-primary">
            {{ currentUser ? `#${currentUser.rank}` : '--' }}
          </div>
        </div>
        <div class="rounded-lg bg-base-200 p-4">
          <div class="text-sm text-base-content/60">我的综合分</div>
          <div class="mt-1 text-3xl font-bold text-primary">
            {{ currentUser ? formatScore(currentUser.overallScore) : '--' }}
          </div>
        </div>
        <div class="rounded-lg bg-base-200 p-4">
          <div class="text-sm text-base-content/60">学习等级</div>
          <div class="mt-1 text-3xl font-bold text-primary">Lv.{{ currentUserLevel }}</div>
        </div>
      </div>
    </section>

    <section v-if="topThree.length" class="mb-6 grid gap-4 md:grid-cols-3">
      <div
        v-for="item in topThree"
        :key="item.userId"
        class="rounded-lg bg-base-100 p-5 shadow"
        :class="{ 'ring-2 ring-primary': isCurrentUser(item) }"
      >
        <div class="flex items-center gap-4">
          <div class="flex h-12 w-12 items-center justify-center rounded-full text-lg font-bold" :class="rankClass(item.rank)">
            {{ item.rank }}
          </div>
          <div class="min-w-0">
            <div class="truncate text-lg font-semibold">{{ item.nickname || item.username }}</div>
            <div class="truncate text-sm text-base-content/60">{{ item.className || '未分班' }}</div>
          </div>
        </div>
        <div class="mt-4 flex items-end justify-between">
          <div>
            <div class="text-sm text-base-content/60">综合分</div>
            <div class="text-3xl font-bold text-primary">{{ formatScore(item.overallScore) }}</div>
          </div>
          <div class="text-right text-sm text-base-content/60">
            <div>{{ item.bestDimension || '暂无优势维度' }}</div>
            <div>{{ formatDateTime(item.lastActiveAt) }}</div>
          </div>
        </div>
      </div>
    </section>

    <section class="rounded-lg bg-base-100 shadow">
      <div class="flex flex-col gap-2 border-b border-base-200 p-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-lg font-semibold">实时排名</h2>
          <p class="text-xs text-base-content/60">
            更新时间：{{ formatDateTime(updatedAt) }}
            <span v-if="source"> · {{ source }}</span>
          </p>
        </div>
        <div class="text-sm text-base-content/60">每 30 秒自动刷新</div>
      </div>

      <div v-if="errorMessage" class="p-6">
        <div class="alert alert-error">
          <i class="fas fa-circle-exclamation"></i>
          <span>{{ errorMessage }}</span>
        </div>
      </div>

      <div v-else-if="isLoading && !items.length" class="flex min-h-72 items-center justify-center">
        <span class="loading loading-spinner loading-lg text-primary"></span>
      </div>

      <div v-else-if="!filteredItems.length" class="flex min-h-72 flex-col items-center justify-center gap-3 text-base-content/60">
        <i class="fas fa-trophy text-4xl text-base-content/30"></i>
        <div>暂无排行榜数据，导入演示 seed 或完成训练后会显示排名。</div>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table table-zebra">
          <thead class="bg-base-200/60">
            <tr>
              <th class="text-center">排名</th>
              <th>用户</th>
              <th>班级</th>
              <th class="text-center">综合分</th>
              <th class="text-center">训练次数</th>
              <th class="text-center">生成题作答</th>
              <th class="text-center">平均训练分</th>
              <th>最近活跃</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in filteredItems"
              :key="item.userId"
              class="transition-colors"
              :class="{ 'bg-primary/10': isCurrentUser(item) }"
            >
              <td class="text-center">
                <div class="mx-auto flex h-9 w-9 items-center justify-center rounded-full font-bold" :class="rankClass(item.rank)">
                  {{ item.rank }}
                </div>
              </td>
              <td>
                <div class="flex items-center gap-3">
                  <div class="avatar placeholder">
                    <div class="h-10 w-10 rounded-full bg-primary/10 text-primary">
                      <img
                        v-if="studentAvatar(item)"
                        :src="studentAvatar(item)"
                        :alt="`${item.nickname || item.username} 的头像`"
                        class="w-full h-full object-cover"
                      />
                      <span v-else>{{ (item.nickname || item.username || 'U').slice(0, 1) }}</span>
                    </div>
                  </div>
                  <div class="min-w-0">
                    <div class="truncate font-semibold">
                      {{ item.nickname || item.username }}
                      <span v-if="isCurrentUser(item)" class="ml-1 text-xs text-primary">(我)</span>
                    </div>
                    <div class="truncate text-xs text-base-content/60">
                      {{ item.studentNumber || `ID ${item.userId}` }}
                    </div>
                  </div>
                </div>
              </td>
              <td>{{ item.className || '--' }}</td>
              <td
                class="text-center font-bold"
                :class="item.overallScore === null ? 'text-base-content/40' : 'text-primary'"
              >
                {{ formatScore(item.overallScore) }}
              </td>
              <td class="text-center">{{ item.trainingCount || '--' }}</td>
              <td class="text-center">{{ item.generatedQuestionAttemptCount || '--' }}</td>
              <td class="text-center">{{ formatScore(item.averageTrainingScore) }}</td>
              <td>
                <div>{{ formatDateTime(item.lastActiveAt) }}</div>
                <div class="text-xs text-base-content/60">
                  弱项：{{ item.weakDimension || '--' }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
