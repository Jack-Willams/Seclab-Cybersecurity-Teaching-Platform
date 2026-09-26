<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Chart from 'chart.js/auto'

import type {
  CapabilityGrowthEvidenceDto,
  CapabilityGrowthDimensionDto,
  CapabilityGrowthHistoryDto,
  CapabilityGrowthResponseDto,
} from '../api'
import {
  formatGrowthDelta,
  formatMetricValue,
  metricDirectionLabel,
} from './capabilityGrowthPresentation'

const props = withDefaults(defineProps<{
  data?: CapabilityGrowthResponseDto | null
  loading?: boolean
  error?: string
  teacherMode?: boolean
}>(), {
  data: null,
  loading: false,
  error: '',
  teacherMode: false,
})

defineEmits<{ retry: [] }>()

const selectedKey = ref<string>('knowledge_mastery')
const chartCanvas = ref<HTMLCanvasElement | null>(null)
let chart: Chart | null = null

const hasGrowthData = computed(() => {
  const data = props.data
  if (!data) return false
  if (typeof data.overall.baselineScore === 'number' || typeof data.overall.currentScore === 'number') {
    return true
  }
  if (data.history.length) return true
  return data.dimensions.some((dimension) =>
    typeof dimension.baselineScore === 'number'
    || typeof dimension.currentScore === 'number'
    || dimension.metrics.length > 0
    || dimension.evidence.length > 0,
  )
})

const selectedDimension = computed<CapabilityGrowthDimensionDto | null>(() =>
  props.data?.dimensions.find((item) => item.key === selectedKey.value)
  ?? props.data?.dimensions[0]
  ?? null,
)

const overallTone = computed(() => {
  const delta = props.data?.overall.delta
  if (delta == null) return 'neutral'
  if (delta > 0) return 'improved'
  if (delta < 0) return 'declined'
  return 'stable'
})

function formatScore(value: number | null | undefined): string {
  return value == null ? '—' : value.toFixed(1)
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '日期待积累'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

function formatDuration(value: number | null | undefined): string {
  if (value == null || value < 0) return '未记录'
  const totalSeconds = Math.round(value)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (hours) return `${hours}小时${minutes}分${seconds}秒`
  if (minutes) return `${minutes}分${seconds}秒`
  return `${seconds}秒`
}

function evidenceStatusLabel(status: string | null | undefined): string {
  const normalized = String(status || '').toLowerCase()
  if (['completed', 'success'].includes(normalized)) return '已完成'
  if (['stopped', 'ended'].includes(normalized)) return '已结束'
  if (['running', 'active'].includes(normalized)) return '进行中'
  if (['failed', 'error'].includes(normalized)) return '未完成'
  return status || '状态未记录'
}

function evidenceEventLabel(eventType: string): string {
  return {
    LAB_START: '进入实验',
    LAB_STOP: '退出实验',
    COMMAND_EXEC: '执行命令',
    AI_INTERACTION: 'AI 交互',
    ERROR_OCCURRED: '发生错误',
    FLAG_SUBMIT: '提交 Flag',
  }[eventType] || eventType
}

function hasLabTrace(item: CapabilityGrowthEvidenceDto): boolean {
  return Boolean(
    item.labSessionId
    || item.targetUrl
    || item.containerName
    || item.startedAt
    || item.endedAt
    || item.eventTypes?.length,
  )
}

/**
 * 证据详情里到底有没有可展示的业务明细。
 *
 * 原先只看 hasLabTrace + messageContent，于是「知识掌握 / 排障 / 自主学习」三个维度
 * 一律显示「该历史记录没有保存更多业务明细」——后端本来就没往证据里放这些字段。
 * 后端补齐字段后，这里也要跟着判断，否则明细有了却仍被兜底文案盖住。
 */
function hasBusinessDetail(item: CapabilityGrowthEvidenceDto): boolean {
  return Boolean(
    hasLabTrace(item)
    || item.messageContent
    || item.knowledgePointName
    || item.questionType
    || item.difficulty
    || item.costTime != null
    || item.failedCommand
    || item.recoveredCommand
    || item.recoverySeconds != null
    || item.aiAskCount != null
    || item.activeSeconds != null,
  )
}

const QUESTION_TYPE_LABELS: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  fill_blank: '填空题',
  short_answer: '简答题',
  judgement: '判断题',
}

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

function questionTypeLabel(value?: string | null): string {
  if (!value) return ''
  return QUESTION_TYPE_LABELS[value] || value
}

function difficultyLabel(value?: string | null): string {
  if (!value) return ''
  return DIFFICULTY_LABELS[value] || value
}

function historyValue(row: CapabilityGrowthHistoryDto): number | null | undefined {
  if (selectedKey.value === 'knowledge_mastery') return row.knowledge_masteryScore
  if (selectedKey.value === 'troubleshooting') return row.troubleshootingScore
  if (selectedKey.value === 'autonomy') return row.autonomyScore
  if (selectedKey.value === 'ai_collaboration') return row.ai_collaborationScore
  if (selectedKey.value === 'engagement') return row.engagementScore
  return row.overallScore
}

function renderChart(): void {
  if (!chartCanvas.value) return
  chart?.destroy()
  chart = null
  const history = props.data?.history ?? []
  const points = history
    .map((row) => ({ row, value: historyValue(row) }))
    .filter((item): item is { row: CapabilityGrowthHistoryDto; value: number } =>
      typeof item.value === 'number',
    )
  if (points.length < 2) return
  chart = new Chart(chartCanvas.value, {
    type: 'line',
    data: {
      labels: points.map(({ row }) => formatDate(row.computedAt)),
      datasets: [{
        data: points.map(({ value }) => value),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.10)',
        pointBackgroundColor: '#ffffff',
        pointBorderColor: '#2563eb',
        pointBorderWidth: 2,
        pointRadius: 4,
        tension: 0.32,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#64748b', maxRotation: 0, font: { size: 11 } },
          border: { display: false },
        },
        y: {
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: { color: '#94a3b8', font: { size: 11 } },
          grid: { color: 'rgba(148, 163, 184, 0.14)' },
          border: { display: false },
        },
      },
    },
  })
}

watch(
  () => [props.data?.history, selectedKey.value],
  () => nextTick(renderChart),
  { deep: true },
)

watch(
  () => props.data?.dimensions,
  (dimensions) => {
    if (dimensions?.length && !dimensions.some((item) => item.key === selectedKey.value)) {
      selectedKey.value = dimensions[0].key
    }
  },
)

onMounted(() => nextTick(renderChart))
onBeforeUnmount(() => chart?.destroy())
</script>

<template>
  <section class="growth-panel" aria-labelledby="capability-growth-title">
    <header class="growth-header">
      <div>
        <h2 id="capability-growth-title">能力成长</h2>
        <p>
          {{ teacherMode ? '基于学生真实学习行为的可比成长证据' : '用真实学习记录，看见你在哪些方面正在进步' }}
        </p>
      </div>
      <div v-if="data?.dataProvenance.mode === 'production_events'" class="source-status">
        <span class="status-dot" aria-hidden="true"></span>
        真实记录计算
      </div>
    </header>

    <div v-if="loading" class="state-view" role="status">
      <span class="loading-ring" aria-hidden="true"></span>
      <strong>正在汇总成长证据</strong>
      <p>系统正在核对可比任务与原始记录。</p>
    </div>

    <div v-else-if="error" class="state-view error-view" role="alert">
      <strong>成长数据暂时无法读取</strong>
      <p>{{ error }}</p>
      <button type="button" @click="$emit('retry')">重新加载</button>
    </div>

    <div v-else-if="!data || !hasGrowthData" class="state-view empty-view">
      <span class="empty-symbol" aria-hidden="true">↗</span>
      <strong>{{ data?.message || '暂无真实成长数据' }}</strong>
      <p>完成真实实验和练习后，这里会形成可追溯的成长证据。</p>
    </div>

    <div v-else class="growth-content">
      <div class="overall-strip">
        <div class="overall-title">
          <span>综合能力</span>
          <strong :class="`tone-${overallTone}`">{{ formatGrowthDelta(data.overall.delta) }}</strong>
        </div>
        <div class="score-journey">
          <div>
            <span>早期基线</span>
            <strong>{{ formatScore(data.overall.baselineScore) }}</strong>
            <small>{{ formatDate(data.baselineComputedAt) }}</small>
          </div>
          <div class="journey-line" aria-hidden="true">
            <span></span>
          </div>
          <div class="current-score">
            <span>当前表现</span>
            <strong>{{ formatScore(data.overall.currentScore) }}</strong>
            <small>{{ formatDate(data.currentComputedAt) }}</small>
          </div>
        </div>
      </div>

      <nav class="dimension-tabs" aria-label="能力维度">
        <button
          v-for="dimension in data.dimensions"
          :key="dimension.key"
          type="button"
          :class="{ active: selectedDimension?.key === dimension.key }"
          :aria-current="selectedDimension?.key === dimension.key ? 'true' : undefined"
          @click="selectedKey = dimension.key"
        >
          <span>{{ dimension.label }}</span>
          <strong>{{ formatGrowthDelta(dimension.delta) }}</strong>
        </button>
      </nav>

      <article v-if="selectedDimension" class="dimension-detail">
        <div class="dimension-summary">
          <div>
            <h3>{{ selectedDimension.label }}</h3>
            <p>{{ selectedDimension.summary }}</p>
          </div>
          <div v-if="data.history.length >= 2" class="trend-chart">
            <canvas ref="chartCanvas" :aria-label="`${selectedDimension.label}历史趋势`"></canvas>
          </div>
        </div>

        <div v-if="selectedDimension.metrics.length" class="metrics-list">
          <section
            v-for="metric in selectedDimension.metrics"
            :key="metric.key"
            class="metric-row"
          >
            <div class="metric-name">
              <span :class="`direction direction-${metric.direction}`">
                {{ metricDirectionLabel(metric.direction) }}
              </span>
              <h4>{{ metric.label }}</h4>
            </div>
            <div class="metric-comparison">
              <div>
                <span>早期</span>
                <strong>{{ formatMetricValue(metric.baselineValue, metric.unit) }}</strong>
              </div>
              <span class="comparison-arrow" aria-hidden="true">→</span>
              <div class="metric-current">
                <span>近期</span>
                <strong>{{ formatMetricValue(metric.currentValue, metric.unit) }}</strong>
              </div>
            </div>
            <div class="metric-explanation">
              <p>{{ metric.explanation }}</p>
              <small>
                早期 {{ metric.baselineSampleCount }} 条 · 近期 {{ metric.currentSampleCount }} 条
              </small>
              <small v-if="teacherMode && metric.sourceRecordIds.length" class="trace">
                来源记录 {{ metric.sourceRecordIds.join('、') }}
              </small>
            </div>
          </section>
        </div>

        <div v-else class="metric-empty">
          该维度已有当前能力结果，但还没有足够的同类任务形成前后对比。
        </div>

        <div v-if="selectedDimension.evidence.length" class="evidence-list">
          <h4>最近证据</h4>
          <details
            v-for="item in selectedDimension.evidence"
            :key="`${item.sourceType}-${item.sourceId}`"
            class="evidence-row"
          >
            <summary>
              <span class="evidence-mark" aria-hidden="true"></span>
              <div class="evidence-summary-main">
                <div class="evidence-title">
                  <strong>{{ item.title }}</strong>
                  <span v-if="item.status" class="evidence-status">{{ evidenceStatusLabel(item.status) }}</span>
                </div>
                <p>{{ item.detail || '该历史记录未保存内容摘要' }}</p>
                <div v-if="item.durationSeconds != null || item.eventCount != null" class="evidence-facts">
                  <span v-if="item.durationSeconds != null">持续 {{ formatDuration(item.durationSeconds) }}</span>
                  <span v-if="item.eventCount != null">记录 {{ item.eventCount }} 条事件</span>
                </div>
              </div>
              <time>{{ formatDate(item.occurredAt) }}</time>
              <span class="evidence-toggle" aria-hidden="true">展开详情</span>
            </summary>

            <div class="evidence-detail">
              <dl>
                <template v-if="item.moduleName || item.moduleId != null">
                  <dt>实验模块</dt>
                  <dd>{{ item.moduleName || `模块 ${item.moduleId}` }}</dd>
                </template>
                <template v-if="item.courseId != null">
                  <dt>课程 ID</dt>
                  <dd>{{ item.courseId }}</dd>
                </template>
                <template v-if="item.taskId != null">
                  <dt>任务 ID</dt>
                  <dd>{{ item.taskId }}</dd>
                </template>
                <template v-if="item.targetUrl">
                  <dt>访问目标</dt>
                  <dd class="trace-value">{{ item.targetUrl }}</dd>
                </template>
                <template v-if="item.containerName">
                  <dt>实验容器</dt>
                  <dd class="trace-value">{{ item.containerName }}</dd>
                </template>
                <template v-if="item.startedAt">
                  <dt>开始时间</dt>
                  <dd>{{ formatDateTime(item.startedAt) }}</dd>
                </template>
                <template v-if="item.endedAt">
                  <dt>结束时间</dt>
                  <dd>{{ formatDateTime(item.endedAt) }}</dd>
                </template>
                <template v-if="item.durationSeconds != null">
                  <dt>实际时长</dt>
                  <dd>{{ formatDuration(item.durationSeconds) }}</dd>
                </template>
                <template v-if="item.messageContent">
                  <dt>实际提问</dt>
                  <dd class="message-content">{{ item.messageContent }}</dd>
                </template>
                <template v-if="item.knowledgePointName">
                  <dt>知识点</dt>
                  <dd>{{ item.knowledgePointName }}</dd>
                </template>
                <template v-if="item.questionType || item.difficulty">
                  <dt>题型 / 难度</dt>
                  <dd>{{ [questionTypeLabel(item.questionType), difficultyLabel(item.difficulty)].filter(Boolean).join(' · ') }}</dd>
                </template>
                <template v-if="item.costTime != null">
                  <dt>作答用时</dt>
                  <dd>{{ formatDuration(item.costTime) }}</dd>
                </template>
                <template v-if="item.failedCommand">
                  <dt>失败命令</dt>
                  <dd class="trace-value">{{ item.failedCommand }}</dd>
                </template>
                <template v-if="item.recoveredCommand">
                  <dt>恢复命令</dt>
                  <dd class="trace-value">{{ item.recoveredCommand }}</dd>
                </template>
                <template v-if="item.recoverySeconds != null">
                  <dt>恢复用时</dt>
                  <dd>{{ formatDuration(item.recoverySeconds) }}</dd>
                </template>
                <template v-if="item.commandCategory">
                  <dt>命令类别</dt>
                  <dd>{{ item.commandCategory }}</dd>
                </template>
                <template v-if="item.aiAskCount != null">
                  <dt>AI 求助次数</dt>
                  <dd>{{ item.aiAskCount }} 次</dd>
                </template>
                <template v-if="item.activeSeconds != null">
                  <dt>有效用时</dt>
                  <dd>{{ formatDuration(item.activeSeconds) }}</dd>
                </template>
                <template v-if="item.difficulty && !item.questionType">
                  <dt>任务难度</dt>
                  <dd>{{ difficultyLabel(item.difficulty) }}</dd>
                </template>
                <template v-if="item.eventTypes?.length">
                  <dt>记录事件</dt>
                  <dd class="event-types">
                    <span v-for="eventType in item.eventTypes" :key="eventType">
                      {{ eventType }}（{{ evidenceEventLabel(eventType) }}）
                    </span>
                  </dd>
                </template>
                <template v-if="item.labSessionId">
                  <dt>会话 ID</dt>
                  <dd class="trace-value">{{ item.labSessionId }}</dd>
                </template>
                <template v-if="item.conversationId">
                  <dt>对话 ID</dt>
                  <dd class="trace-value">{{ item.conversationId }}</dd>
                </template>
                <template v-if="!hasBusinessDetail(item)">
                  <dt>原始记录</dt>
                  <dd>该历史记录没有保存更多业务明细</dd>
                </template>
                <dt>来源记录</dt>
                <dd class="trace-value">{{ item.sourceType }} / {{ item.sourceId }}</dd>
              </dl>
            </div>
          </details>
        </div>
      </article>

      <footer class="provenance-bar">
        <span>计算版本 {{ data.calculationVersion }}</span>
        <span>纳入 {{ data.dataProvenance.eligibleRecordCount ?? 0 }} 条生产记录</span>
        <span v-if="data.dataProvenance.excludedRecordCount">
          已排除 {{ data.dataProvenance.excludedRecordCount }} 条非生产数据
        </span>
        <span v-if="data.dataProvenance.unverifiableRecordCount">
          {{ data.dataProvenance.unverifiableRecordCount }} 条来源不明记录未参与
        </span>
      </footer>
    </div>
  </section>
</template>

<style scoped>
.growth-panel {
  overflow: hidden;
  border: 1px solid oklch(var(--bc) / .12);
  border-radius: 18px;
  background: oklch(var(--b1));
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.06);
  color: oklch(var(--bc));
}

.growth-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px 22px;
  border-bottom: 1px solid oklch(var(--bc) / .12);
}

.growth-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.growth-header p,
.dimension-summary p,
.metric-explanation p,
.evidence-row p,
.state-view p {
  margin: 6px 0 0;
  color: oklch(var(--bc) / .6);
  font-size: 14px;
  line-height: 1.65;
}

.source-status {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 8px;
  color: oklch(var(--su));
  font-size: 13px;
  font-weight: 600;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: oklch(var(--su));
  box-shadow: 0 0 0 4px oklch(var(--bc) / .12);
}

.overall-strip {
  display: grid;
  grid-template-columns: minmax(150px, .6fr) minmax(360px, 1.4fr);
  align-items: center;
  gap: 32px;
  padding: 26px 30px;
  background: oklch(var(--b2));
}

.overall-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.overall-title > span {
  color: oklch(var(--bc));
  font-size: 14px;
  font-weight: 600;
}

.overall-title strong {
  font-size: 24px;
  font-weight: 750;
}

.tone-improved,
.direction-improved {
  color: oklch(var(--su)) !important;
}

.tone-declined,
.direction-declined {
  color: oklch(var(--wa)) !important;
}

.tone-stable,
.tone-neutral {
  color: oklch(var(--bc));
}

.score-journey {
  display: grid;
  grid-template-columns: auto minmax(80px, 1fr) auto;
  align-items: center;
  gap: 18px;
}

.score-journey > div:not(.journey-line) {
  display: grid;
  gap: 2px;
}

.score-journey span,
.metric-comparison span,
.metric-explanation small,
.score-journey small {
  color: oklch(var(--bc) / .6);
  font-size: 12px;
}

.score-journey strong {
  font-size: 30px;
  font-weight: 750;
  letter-spacing: -0.03em;
}

.current-score {
  text-align: right;
}

.current-score strong {
  color: oklch(var(--p));
}

.journey-line {
  position: relative;
  height: 2px;
  background: oklch(var(--bc) / .6);
}

.journey-line::before,
.journey-line::after {
  position: absolute;
  top: 50%;
  width: 8px;
  height: 8px;
  border: 2px solid oklch(var(--bc) / .6);
  border-radius: 50%;
  background: oklch(var(--b1));
  content: "";
  transform: translateY(-50%);
}

.journey-line::before { left: -1px; }
.journey-line::after {
  right: -1px;
  border-color: oklch(var(--p));
  background: oklch(var(--p));
}

.dimension-tabs {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  border-top: 1px solid oklch(var(--bc) / .12);
  border-bottom: 1px solid oklch(var(--bc) / .12);
}

.dimension-tabs button {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 17px 14px 15px;
  border: 0;
  border-right: 1px solid oklch(var(--bc) / .12);
  border-bottom: 3px solid transparent;
  background: oklch(var(--b1));
  color: oklch(var(--bc) / .6);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background .18s ease, border-color .18s ease, color .18s ease;
}

.dimension-tabs button:last-child { border-right: 0; }
.dimension-tabs button:hover { background: oklch(var(--b2)); }
.dimension-tabs button.active {
  border-bottom-color: oklch(var(--p));
  color: oklch(var(--bc));
  background: oklch(var(--b1));
}

.dimension-tabs span {
  overflow: hidden;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dimension-tabs strong {
  color: inherit;
  font-size: 12px;
  font-weight: 600;
}

.dimension-detail {
  padding: 28px 30px;
}

.dimension-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(250px, .8fr);
  align-items: center;
  gap: 36px;
  margin-bottom: 22px;
}

.direction {
  display: inline-flex;
  align-items: center;
  color: oklch(var(--bc));
  font-size: 12px;
  font-weight: 650;
}

.dimension-summary h3 {
  margin: 8px 0 0;
  font-size: 20px;
}

.trend-chart {
  height: 130px;
}

.metrics-list {
  border-top: 1px solid oklch(var(--bc) / .12);
}

.metric-row {
  display: grid;
  grid-template-columns: minmax(145px, .7fr) minmax(220px, 1fr) minmax(260px, 1.25fr);
  align-items: center;
  gap: 24px;
  padding: 22px 0;
  border-bottom: 1px solid oklch(var(--bc) / .12);
}

.metric-name h4,
.evidence-list h4 {
  margin: 6px 0 0;
  font-size: 15px;
}

.metric-comparison {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
}

.metric-comparison > div {
  display: grid;
  gap: 3px;
}

.metric-comparison strong {
  font-size: 22px;
  letter-spacing: -0.02em;
}

.metric-current { text-align: right; }
.metric-current strong { color: oklch(var(--p)); }
.comparison-arrow { color: oklch(var(--bc) / .6) !important; }

.metric-explanation p { margin: 0; }
.metric-explanation small {
  display: block;
  margin-top: 6px;
}

.metric-explanation .trace {
  overflow-wrap: anywhere;
  color: oklch(var(--bc));
}

.metric-empty {
  padding: 24px;
  border: 1px dashed oklch(var(--bc) / .6);
  border-radius: 12px;
  background: oklch(var(--b2));
  color: oklch(var(--bc) / .6);
  font-size: 14px;
}

.evidence-list {
  margin-top: 26px;
}

.evidence-row {
  border-bottom: 1px solid oklch(var(--b2));
}

.evidence-row summary {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto auto;
  align-items: start;
  gap: 12px;
  padding: 16px 0;
  cursor: pointer;
  list-style: none;
}

.evidence-row summary::-webkit-details-marker { display: none; }
.evidence-row strong { font-size: 14px; }
.evidence-row p { margin-top: 2px; }
.evidence-row time {
  color: oklch(var(--bc) / .6);
  font-size: 12px;
}

.evidence-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.evidence-status {
  padding: 2px 7px;
  border-radius: 999px;
  background: oklch(var(--b2));
  color: oklch(var(--su));
  font-size: 11px;
  font-weight: 650;
}

.evidence-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  margin-top: 7px;
  color: oklch(var(--bc));
  font-size: 12px;
}

.evidence-toggle {
  min-width: 56px;
  color: oklch(var(--p));
  font-size: 12px;
  font-weight: 650;
  text-align: right;
}

.evidence-row[open] .evidence-toggle {
  font-size: 0;
}

.evidence-row[open] .evidence-toggle::after {
  content: '收起详情';
  font-size: 12px;
}

.evidence-detail {
  margin: 0 0 16px 22px;
  padding: 16px 18px;
  border: 1px solid oklch(var(--bc) / .12);
  border-radius: 12px;
  background: oklch(var(--b1));
}

.evidence-detail dl {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 10px 16px;
  margin: 0;
  font-size: 13px;
}

.evidence-detail dt {
  color: oklch(var(--bc) / .6);
}

.evidence-detail dd {
  margin: 0;
  color: oklch(var(--bc));
}

.trace-value {
  overflow-wrap: anywhere;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.message-content {
  white-space: pre-wrap;
}

.event-types {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.event-types span {
  padding: 3px 7px;
  border-radius: 6px;
  background: oklch(var(--bc) / .12);
  color: oklch(var(--p));
  font-size: 11px;
}

.evidence-mark {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: oklch(var(--p));
}

.provenance-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  padding: 14px 30px;
  border-top: 1px solid oklch(var(--bc) / .12);
  background: oklch(var(--b2));
  color: oklch(var(--bc) / .6);
  font-size: 12px;
}

.state-view {
  display: grid;
  justify-items: center;
  padding: 58px 30px;
  text-align: center;
}

.state-view strong { font-size: 16px; }
.state-view button {
  margin-top: 18px;
  padding: 9px 16px;
  border: 0;
  border-radius: 8px;
  background: oklch(var(--p));
  color: oklch(var(--pc));
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.loading-ring {
  width: 24px;
  height: 24px;
  margin-bottom: 16px;
  border: 3px solid oklch(var(--bc) / .12);
  border-top-color: oklch(var(--p));
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

.empty-symbol {
  display: grid;
  width: 42px;
  height: 42px;
  margin-bottom: 16px;
  place-items: center;
  border-radius: 50%;
  background: oklch(var(--b2));
  color: oklch(var(--p));
  font-size: 21px;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 900px) {
  .overall-strip,
  .dimension-summary {
    grid-template-columns: 1fr;
  }

  .dimension-tabs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dimension-tabs button { border-bottom-width: 1px; }
  .dimension-tabs button.active { box-shadow: inset 3px 0 oklch(var(--p)); }

  .metric-row {
    grid-template-columns: minmax(130px, .7fr) minmax(210px, 1fr);
  }

  .metric-explanation { grid-column: 1 / -1; }
}

@media (max-width: 600px) {
  .growth-header,
  .overall-strip,
  .dimension-detail {
    padding-right: 20px;
    padding-left: 20px;
  }

  .growth-header { flex-direction: column; }
  .score-journey { grid-template-columns: auto 1fr auto; }
  .score-journey strong { font-size: 25px; }
  .dimension-tabs { grid-template-columns: 1fr; }
  .dimension-tabs button {
    grid-template-columns: 1fr auto;
    border-right: 0;
  }

  .metric-row { grid-template-columns: 1fr; }
  .metric-explanation { grid-column: auto; }
  .evidence-row summary {
    grid-template-columns: 10px 1fr auto;
  }
  .evidence-row time {
    grid-column: 2;
  }
  .evidence-toggle {
    grid-column: 3;
    grid-row: 1;
  }
  .evidence-detail {
    margin-left: 0;
  }
  .evidence-detail dl {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .evidence-detail dd {
    margin-bottom: 8px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-ring { animation: none; }
  .dimension-tabs button { transition: none; }
}
</style>
