<script setup lang="ts">
import { ChevronUpIcon, EyeIcon } from '@heroicons/vue/outline'
import { computed, onMounted, ref } from 'vue'
import {
  getApiErrorMessage,
  getTeacherGeneratedQuestions,
  type TeacherGeneratedQuestionDto,
} from '../../../api'

const loading = ref(false)
const error = ref<string | null>(null)
const questions = ref<TeacherGeneratedQuestionDto[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const status = ref('')
const expandedId = ref<string | null>(null)
let requestVersion = 0

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / size.value)))

function formatScore(value: number | string | null | undefined) {
  const numeric = Number(value || 0)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : '0.0'
}

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 16) : '暂无时间'
}

function statusLabel(value: string) {
  const normalized = String(value || '').toUpperCase()
  if (normalized === 'APPROVED') return '已通过'
  if (normalized === 'REJECTED') return '未通过'
  if (normalized === 'NEEDS_REVISION') return '需修改'
  return '待审核'
}

function statusClasses(value: string) {
  const normalized = String(value || '').toUpperCase()
  if (normalized === 'APPROVED') return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  if (normalized === 'REJECTED') return 'border-rose-200 bg-rose-50 text-rose-700'
  if (normalized === 'NEEDS_REVISION') return 'border-orange-200 bg-orange-50 text-orange-700'
  return 'border-amber-200 bg-amber-50 text-amber-700'
}

function difficultyLabel(value?: string | null) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'easy') return '简单'
  if (normalized === 'medium') return '中等'
  if (normalized === 'hard') return '困难'
  return value || '未知'
}

function questionTypeLabel(value?: string | null) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'single_choice') return '单选题'
  if (normalized === 'multiple_choice') return '多选题'
  if (normalized === 'short_answer') return '简答题'
  if (normalized === 'fill_blank') return '填空题'
  return value || '未知'
}

function formatRubric(value: unknown) {
  if (!value) return '暂无评分标准'
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    if (!value.length) return '暂无评分标准'
    return value
      .map((item, index) => {
        if (typeof item === 'string') return `${index + 1}. ${item}`
        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>
          const label = record.label || record.name || record.dimension || `标准 ${index + 1}`
          const detail = record.description || record.detail || record.criteria || record.score || ''
          return `${label}${detail ? `：${detail}` : ''}`
        }
        return String(item)
      })
      .join('\n')
  }
  if (typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}：${String(item)}`)
      .join('\n')
  }
  return String(value)
}

async function fetchQuestions() {
  const version = ++requestVersion
  loading.value = true
  error.value = null
  try {
    const response = await getTeacherGeneratedQuestions({
      status: status.value || undefined,
      page: page.value,
      size: size.value,
    })
    if (version !== requestVersion) return
    questions.value = response.items || []
    total.value = response.total || 0
  } catch (err) {
    if (version !== requestVersion) return
    error.value = getApiErrorMessage(err, '生成题记录加载失败，请重新加载。')
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

function applyStatusFilter() {
  page.value = 1
  void fetchQuestions()
}

function changePage(nextPage: number) {
  page.value = Math.min(Math.max(nextPage, 1), totalPages.value)
  void fetchQuestions()
}

onMounted(() => {
  void fetchQuestions()
})
</script>

<template>
  <div class="h-full overflow-y-auto bg-base-100 p-6">
    <div class="mb-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-2xl font-bold">AI 生成题记录</h1>
        <p class="mt-1 text-sm text-base-content/60">只读展示个性化训练题、学生作答情况和教学审核信息</p>
      </div>
      <div class="flex items-center gap-2">
        <select v-model="status" class="select select-bordered select-sm" @change="applyStatusFilter">
          <option value="">全部状态</option>
          <option value="PENDING_REVIEW">待审核</option>
          <option value="APPROVED">已通过</option>
          <option value="REJECTED">未通过</option>
          <option value="NEEDS_REVISION">需修改</option>
        </select>
        <button class="btn btn-outline btn-sm" @click="fetchQuestions">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ error }}</span>
      <button class="btn btn-sm" @click="fetchQuestions">重新加载</button>
    </div>

    <div v-else-if="!questions.length" class="rounded-lg border border-base-200 p-10 text-center text-base-content/60 shadow-sm">
      暂无 AI 生成题记录
    </div>

    <div v-else class="rounded-lg border border-base-200 bg-base-100 shadow-sm">
      <div class="overflow-x-auto">
        <table class="table">
          <thead>
            <tr>
              <th>题目</th>
              <th>题型</th>
              <th>难度</th>
              <th>知识标签</th>
              <th>质量分</th>
              <th>来源学生</th>
              <th>作答</th>
              <th>审核状态</th>
              <th>生成时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in questions" :key="item.generatedQuestionId">
              <tr>
                <td class="max-w-xs">
                  <div class="font-semibold">{{ item.title }}</div>
                  <div class="truncate text-xs text-base-content/50">题目编号：{{ item.generatedQuestionId }}</div>
                </td>
                <td>{{ questionTypeLabel(item.questionType) }}</td>
                <td>{{ difficultyLabel(item.difficulty) }}</td>
                <td>
                  <div class="flex max-w-xs flex-wrap gap-1">
                    <span v-for="tag in item.knowledgeTags" :key="tag" class="badge badge-ghost badge-sm">{{ tag }}</span>
                    <span v-if="!item.knowledgeTags.length" class="text-xs text-base-content/50">暂无标签</span>
                  </div>
                </td>
                <td>{{ formatScore(item.qualityScore) }}</td>
                <td>{{ item.username }}</td>
                <td>{{ item.attemptCount }} 次 · {{ formatScore(item.averageScore) }}</td>
                <td>
                  <span
                    class="inline-flex h-7 min-w-[4.5rem] items-center justify-center whitespace-nowrap rounded-full border px-2.5 text-xs font-medium"
                    :class="statusClasses(item.reviewStatus)"
                  >
                    {{ statusLabel(item.reviewStatus) }}
                  </span>
                </td>
                <td>{{ formatTime(item.createdAt) }}</td>
                <td>
                  <button
                    type="button"
                    class="inline-flex h-8 min-w-[4.75rem] items-center justify-center gap-1.5 whitespace-nowrap rounded-lg border border-primary/30 bg-base-100 px-2.5 text-xs font-medium text-primary shadow-sm transition hover:border-primary/50 hover:bg-primary/5 focus:outline-none focus:ring-2 focus:ring-primary/30"
                    :aria-expanded="expandedId === item.generatedQuestionId"
                    @click="expandedId = expandedId === item.generatedQuestionId ? null : item.generatedQuestionId"
                  >
                    <ChevronUpIcon v-if="expandedId === item.generatedQuestionId" class="h-4 w-4 shrink-0" aria-hidden="true" />
                    <EyeIcon v-else class="h-4 w-4 shrink-0" aria-hidden="true" />
                    {{ expandedId === item.generatedQuestionId ? '收起' : '查看' }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedId === item.generatedQuestionId">
                <td colspan="10" class="bg-base-200/40">
                  <div class="grid grid-cols-1 gap-4 p-4 lg:grid-cols-3">
                    <div class="lg:col-span-2">
                      <div class="mb-2 font-semibold">题干</div>
                      <p class="whitespace-pre-wrap text-sm leading-relaxed">{{ item.stem || '暂无题干' }}</p>
                    </div>
                    <div class="space-y-4">
                      <div>
                        <div class="mb-2 font-semibold">标准答案</div>
                        <p class="whitespace-pre-wrap text-sm text-base-content/80">{{ item.standardAnswer || item.referenceAnswer || '暂无标准答案' }}</p>
                      </div>
                      <div>
                        <div class="mb-2 font-semibold">解析 / 教学分析</div>
                        <p class="whitespace-pre-wrap text-sm text-base-content/80">{{ item.explanation || '暂无解析' }}</p>
                      </div>
                      <div>
                        <div class="mb-2 font-semibold">教学目标</div>
                        <p class="whitespace-pre-wrap text-sm text-base-content/80">{{ item.teachingObjective || '暂无教学目标' }}</p>
                      </div>
                      <div>
                        <div class="mb-2 font-semibold">预期能力</div>
                        <p class="whitespace-pre-wrap text-sm text-base-content/80">{{ item.expectedSkill || '暂无预期能力' }}</p>
                      </div>
                      <div>
                        <div class="mb-2 font-semibold">评分标准</div>
                        <p class="whitespace-pre-wrap text-sm text-base-content/80">{{ formatRubric(item.gradingRubric) }}</p>
                      </div>
                      <div class="alert alert-info py-2 text-sm">
                        <span>本轮仅做真实记录展示，完整审核流后续扩展。</span>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="flex items-center justify-between gap-4 border-t border-base-200 p-4">
        <span class="text-sm text-base-content/60">共 {{ total }} 条记录，第 {{ page }} / {{ totalPages }} 页</span>
        <div class="join">
          <button class="btn join-item btn-sm" :disabled="page <= 1" @click="changePage(page - 1)">上一页</button>
          <button class="btn join-item btn-sm" :disabled="page >= totalPages" @click="changePage(page + 1)">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>
