<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ProfileDashboardSolveRecord } from '../../../api'

const props = defineProps<{
  records: ProfileDashboardSolveRecord[]
}>()

type RecordFilter = 'all' | 'wrong' | 'correct'

const activeFilter = ref<RecordFilter>('all')

const wrongCount = computed(() => props.records.filter((record) => record.isCorrect === false).length)
const correctCount = computed(() => props.records.filter((record) => record.isCorrect === true).length)
const visibleRecords = computed(() => {
  if (activeFilter.value === 'wrong') {
    return props.records.filter((record) => record.isCorrect === false)
  }
  if (activeFilter.value === 'correct') {
    return props.records.filter((record) => record.isCorrect === true)
  }
  return props.records
})

const filters = computed(() => [
  { key: 'all' as const, label: '全部', count: props.records.length },
  { key: 'wrong' as const, label: '错题', count: wrongCount.value },
  { key: 'correct' as const, label: '正确', count: correctCount.value },
])

function sourceLabel(sourceType: string) {
  if (sourceType === 'generated_training') return '专项训练'
  if (sourceType === 'flag') return 'Flag 提交'
  return '课程题'
}

function questionTypeLabel(questionType: string) {
  const normalized = questionType.toLowerCase().replaceAll('_', '-')
  if (normalized.includes('multiple')) return '多选题'
  if (normalized.includes('single') || normalized.includes('choice')) return '选择题'
  if (normalized.includes('short')) return '简答题'
  if (normalized === 'flag') return 'Flag'
  return questionType || '题目'
}

function answerText(value: unknown) {
  if (value === null || value === undefined || value === '') return '未记录'
  if (Array.isArray(value)) return value.map(answerText).join('、')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function durationText(costTime: number | null) {
  if (costTime === null || costTime <= 0) return '未记录用时'
  if (costTime < 60) return `${costTime} 秒`
  const minutes = Math.floor(costTime / 60)
  const seconds = costTime % 60
  return seconds ? `${minutes} 分 ${seconds} 秒` : `${minutes} 分钟`
}

function scoreText(score: number) {
  return Number.isInteger(score) ? `${score} 分` : `${score.toFixed(1)} 分`
}
</script>

<template>
  <section aria-label="解题记录">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div class="flex flex-wrap gap-2" role="group" aria-label="筛选解题记录">
        <button
          v-for="filter in filters"
          :key="filter.key"
          type="button"
          class="btn btn-sm rounded-full"
          :class="activeFilter === filter.key ? 'btn-primary' : 'btn-ghost border border-base-300'"
          :aria-pressed="activeFilter === filter.key"
          @click="activeFilter = filter.key"
        >
          {{ filter.label }} {{ filter.count }}
        </button>
      </div>
      <div v-if="records.length" class="text-xs text-base-content/55">
        记录均来自实际提交数据
      </div>
    </div>

    <div v-if="visibleRecords.length" class="space-y-3">
      <details
        v-for="record in visibleRecords"
        :key="record.id"
        class="group overflow-hidden rounded-2xl border bg-base-100 transition-colors"
        :class="record.isCorrect === false ? 'border-error/35' : 'border-base-300'"
      >
        <summary class="flex cursor-pointer list-none items-start gap-3 p-4 hover:bg-base-200/45">
          <div
            class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
            :class="record.isCorrect === false ? 'bg-error/10 text-error' : record.isCorrect === true ? 'bg-success/10 text-success' : 'bg-base-200 text-base-content/60'"
          >
            <i class="fas" :class="record.isCorrect === false ? 'fa-xmark' : record.isCorrect === true ? 'fa-check' : 'fa-file-lines'"></i>
          </div>

          <div class="min-w-0 flex-1">
            <div class="mb-1 flex flex-wrap items-center gap-2">
              <span v-if="record.isCorrect === false" class="badge badge-error badge-sm">错题</span>
              <span v-else-if="record.isCorrect === true" class="badge badge-success badge-outline badge-sm">正确</span>
              <span class="badge badge-ghost badge-sm">{{ sourceLabel(record.sourceType) }}</span>
              <span class="badge badge-ghost badge-sm">{{ questionTypeLabel(record.questionType) }}</span>
            </div>
            <h3 class="truncate font-semibold text-base-content">{{ record.title }}</h3>
            <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-base-content/55">
              <span>{{ record.module }}</span>
              <span>{{ record.time }}</span>
              <span>{{ durationText(record.costTime) }}</span>
              <span>{{ scoreText(record.score) }}</span>
            </div>
          </div>

          <span class="mt-2 shrink-0 text-sm font-medium text-primary">
            查看详情
            <i class="fas fa-chevron-down ml-1 transition-transform group-open:rotate-180"></i>
          </span>
        </summary>

        <div class="border-t border-base-200 bg-base-200/25 p-4 md:p-5">
          <div v-if="record.contentAvailable" class="space-y-4">
            <div>
              <div class="mb-1 text-xs font-bold uppercase tracking-wide text-base-content/50">题目</div>
              <p class="whitespace-pre-wrap leading-7 text-base-content/85">{{ record.stem }}</p>
            </div>

            <ol v-if="record.options.length" class="grid gap-2 sm:grid-cols-2">
              <li
                v-for="(option, index) in record.options"
                :key="`${record.id}-option-${index}`"
                class="rounded-xl border border-base-300 bg-base-100 px-3 py-2 text-sm"
              >
                <span class="mr-2 font-bold text-primary">{{ String.fromCharCode(65 + index) }}.</span>
                {{ option }}
              </li>
            </ol>
          </div>
          <div v-else class="alert border-warning/25 bg-warning/10 text-sm">
            <i class="fas fa-triangle-exclamation text-warning"></i>
            <span>该历史记录未保存题干，只能展示当时的作答结果。</span>
          </div>

          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div class="rounded-xl border border-base-300 bg-base-100 p-4">
              <div class="mb-2 text-xs font-bold text-base-content/50">我的答案</div>
              <div class="whitespace-pre-wrap text-sm font-medium" :class="record.isCorrect === false ? 'text-error' : 'text-base-content'">
                {{ answerText(record.studentAnswer) }}
              </div>
            </div>
            <div class="rounded-xl border border-success/25 bg-success/5 p-4">
              <div class="mb-2 text-xs font-bold text-success">正确答案</div>
              <div class="whitespace-pre-wrap text-sm text-base-content/85">
                {{ answerText(record.standardAnswer) }}
              </div>
            </div>
          </div>

          <div v-if="record.explanation" class="mt-3 rounded-xl border border-info/20 bg-info/5 p-4">
            <div class="mb-2 text-xs font-bold text-info">题目解析</div>
            <p class="whitespace-pre-wrap text-sm leading-6 text-base-content/80">{{ record.explanation }}</p>
          </div>
        </div>
      </details>
    </div>

    <div v-else class="rounded-2xl border border-dashed border-base-300 bg-base-200/30 py-10 text-center">
      <i class="fas fa-clipboard-list mb-3 text-3xl text-base-content/25"></i>
      <div class="font-medium text-base-content/70">
        {{ records.length ? '这个筛选下暂无记录' : '暂无真实作答记录' }}
      </div>
      <p class="mt-1 text-sm text-base-content/50">
        完成课程题、专项训练或 Flag 提交后会自动出现在这里。
      </p>
    </div>
  </section>
</template>
