<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { TeacherCourseQuestionsDto, TeacherGeneratedQuestionRecord } from '../../../../api'

const props = defineProps<{
  data: TeacherCourseQuestionsDto | null
  loading?: boolean
  scopeLabel: string
}>()

// 班级人数多时这份清单会很长，默认只铺开前 COLLAPSED_COUNT 条，
// 其余收进「展开全部」，避免要滚很久才能到下面的分析区块。
const COLLAPSED_COUNT = 15

const answerFilter = ref<'all' | 'incorrect' | 'correct' | 'unanswered'>('all')
const expandedId = ref<string | null>(null)
const showAll = ref(false)

const filteredItems = computed(() => (props.data?.items || []).filter((item) => {
  const latest = item.attemptHistory?.at(-1)
  if (answerFilter.value === 'incorrect') return latest?.isCorrect === false
  if (answerFilter.value === 'correct') return latest?.isCorrect === true
  if (answerFilter.value === 'unanswered') return !latest
  return true
}))

const visibleItems = computed(() =>
  showAll.value ? filteredItems.value : filteredItems.value.slice(0, COLLAPSED_COUNT))

const hiddenCount = computed(() => Math.max(0, filteredItems.value.length - visibleItems.value.length))

// 换实验或换筛选条件后重新收起，否则切过去还是展开状态
watch(() => props.data, (data) => {
  const firstIncorrect = data?.items.find((item) => item.attemptHistory?.at(-1)?.isCorrect === false)
  expandedId.value = firstIncorrect?.generatedQuestionId || data?.items[0]?.generatedQuestionId || null
  showAll.value = false
}, { immediate: true })

watch(answerFilter, () => { showAll.value = false })

function latest(item: TeacherGeneratedQuestionRecord) {
  return item.attemptHistory?.at(-1) || null
}

function formatAnswer(value: unknown) {
  if (value === null || value === undefined || value === '') return '未作答'
  if (typeof value === 'string') return value
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}

function formatTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '时间未知'
}
</script>

<template>
  <section class="course-records">
    <div class="records-head">
      <h2>{{ scopeLabel }}本实验全部做题情况</h2>
      <div class="join" aria-label="作答结果筛选">
        <button
          v-for="item in [['all','全部'],['incorrect','错题'],['correct','答对'],['unanswered','未作答']]"
          :key="item[0]"
          class="btn join-item btn-sm"
          :class="answerFilter === item[0] ? 'btn-primary' : 'btn-outline'"
          @click="answerFilter = item[0] as typeof answerFilter"
        >{{ item[1] }}</button>
      </div>
    </div>
    <div v-if="loading" class="records-empty">
      <span class="loading loading-spinner loading-md text-primary"></span>正在读取实验作答记录…
    </div>
    <div v-else-if="!data?.items.length" class="records-empty">
      <i class="fas fa-list-check text-3xl text-base-content/25"></i>
      <strong>本实验暂无做题记录</strong>
    </div>
    <div v-else-if="!visibleItems.length" class="records-empty">当前筛选条件下没有题目。</div>
    <div v-else class="question-list">
      <article v-for="(item,index) in visibleItems" :key="item.generatedQuestionId" class="question-card" :class="{ open: expandedId === item.generatedQuestionId }">
        <button class="question-summary" @click="expandedId = expandedId === item.generatedQuestionId ? null : item.generatedQuestionId">
          <span class="question-no">{{ index + 1 }}</span>
          <span class="question-main"><strong>{{ item.title }}</strong><small>{{ item.student.studentName }} · {{ item.knowledgePointName || '未标注知识点' }} · 共 {{ item.attemptHistory?.length || 0 }} 次作答</small></span>
          <span class="question-score">{{ latest(item) ? `${latest(item)?.score ?? 0} 分` : '未作答' }}</span>
          <span class="result-badge" :class="latest(item)?.isCorrect === true ? 'correct' : latest(item)?.isCorrect === false ? 'incorrect' : 'empty'">{{ latest(item)?.isCorrect === true ? '最终答对' : latest(item)?.isCorrect === false ? '最终答错' : '未作答' }}</span>
          <span class="chevron">{{ expandedId === item.generatedQuestionId ? '收起' : '详情' }}</span>
        </button>
        <div v-if="expandedId === item.generatedQuestionId" class="question-detail">
          <div class="question-copy"><h4>题目</h4><p>{{ item.stem || item.title }}</p><div v-if="item.options?.length" class="options"><span v-for="(option,optionIndex) in item.options" :key="optionIndex">{{ option }}</span></div></div>
          <div class="answer-grid"><div><h4>标准答案</h4><pre>{{ formatAnswer(item.standardAnswer || item.referenceAnswer) }}</pre></div><div><h4>题目解析</h4><p>{{ item.explanation || '暂无解析' }}</p></div></div>
          <div class="attempt-block"><h4>完整作答轨迹</h4><div v-if="!item.attemptHistory?.length" class="attempt-empty">学生尚未作答。</div><ol v-else class="attempt-list"><li v-for="(attempt,attemptIndex) in item.attemptHistory" :key="attempt.attemptId"><span class="attempt-index">{{ attemptIndex + 1 }}</span><div><div class="attempt-meta"><strong :class="attempt.isCorrect ? 'text-correct' : 'text-incorrect'">{{ attempt.isCorrect ? '回答正确' : '回答错误' }} · {{ attempt.score }} 分</strong><small>{{ formatTime(attempt.submittedAt) }}<template v-if="attempt.costTime"> · 用时 {{ attempt.costTime }} 秒</template></small></div><pre>{{ formatAnswer(attempt.answer) }}</pre></div></li></ol></div>
        </div>
      </article>
      <button
        v-if="hiddenCount || showAll"
        type="button"
        class="records-toggle"
        @click="showAll = !showAll"
      >
        <template v-if="!showAll">展开全部（还有 {{ hiddenCount }} 条）<i class="fas fa-chevron-down"></i></template>
        <template v-else>收起，只看前 {{ COLLAPSED_COUNT }} 条<i class="fas fa-chevron-up"></i></template>
      </button>
    </div>
  </section>
</template>

<style scoped>
.course-records{padding:20px}.records-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:16px}.records-head h2{margin:0;color:oklch(var(--bc));font-size:17px}.records-head p{margin:6px 0 0;color:oklch(var(--bc) / .6);font-size:12px}.records-empty{display:grid;gap:7px;place-items:center;padding:48px;color:oklch(var(--bc) / .6);font-size:13px}.records-empty strong{color:oklch(var(--bc));font-size:15px}.question-list{display:grid;gap:10px}.records-toggle{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:2px;padding:11px;border:1px dashed oklch(var(--bc) / .25);border-radius:8px;background:oklch(var(--b2));color:oklch(var(--p));font-size:12px;font-weight:650;cursor:pointer;transition:border-color .15s ease,background .15s ease}.records-toggle:hover,.records-toggle:focus-visible{border-color:oklch(var(--p));background:oklch(var(--b1));outline:none}.records-toggle i{font-size:10px}.question-card{border:1px solid oklch(var(--bc) / .12);border-radius:8px;overflow:hidden;background:oklch(var(--b1))}.question-card.open{border-color:oklch(var(--p));box-shadow:0 4px 14px oklch(var(--p) / .12)}.question-summary{display:grid;width:100%;grid-template-columns:28px minmax(0,1fr) 72px 76px 44px;gap:11px;align-items:center;padding:13px 14px;border:0;background:oklch(var(--b1));color:oklch(var(--bc));text-align:left;cursor:pointer}.question-summary:hover{background:oklch(var(--b2))}.question-no{display:grid;width:25px;height:25px;place-items:center;border-radius:6px;background:oklch(var(--b2));color:oklch(var(--p));font-size:11px;font-weight:700}.question-main strong,.question-main small{display:block}.question-main strong{color:oklch(var(--bc));font-size:13px}.question-main small{margin-top:5px;color:oklch(var(--bc) / .6);font-size:11px}.question-score{text-align:right;color:oklch(var(--bc));font-size:12px;font-weight:650}.result-badge{padding:4px 7px;border-radius:999px;text-align:center;font-size:10px}.result-badge.correct{background:oklch(var(--su) / .16);color:oklch(var(--su))}.result-badge.incorrect{background:oklch(var(--er) / .16);color:oklch(var(--er))}.result-badge.empty{background:oklch(var(--bc) / .1);color:oklch(var(--bc) / .6)}.chevron{color:oklch(var(--p));font-size:11px}.question-detail{padding:18px 20px;border-top:1px solid oklch(var(--bc) / .12);background:oklch(var(--b1))}.question-detail h4{margin:0 0 8px;color:oklch(var(--bc) / .6);font-size:11px}.question-copy p,.answer-grid p{margin:0;color:oklch(var(--bc));font-size:13px;line-height:1.7}.options{display:grid;gap:6px;margin-top:10px}.options span{padding:7px 9px;border:1px solid oklch(var(--bc) / .12);border-radius:5px;background:oklch(var(--b1));color:oklch(var(--bc));font-size:12px}.answer-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}.answer-grid>div{padding:13px;border:1px solid oklch(var(--bc) / .12);border-radius:7px;background:oklch(var(--b1))}.question-detail pre{margin:0;white-space:pre-wrap;word-break:break-word;color:oklch(var(--bc));font:12px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace}.attempt-block{margin-top:17px}.attempt-list{display:grid;gap:0;margin:0;padding:0;list-style:none}.attempt-list li{display:grid;grid-template-columns:26px 1fr;gap:10px;padding:12px 0;border-top:1px solid oklch(var(--bc) / .12)}.attempt-index{display:grid;width:23px;height:23px;place-items:center;border-radius:50%;background:oklch(var(--bc) / .12);color:oklch(var(--p));font-size:10px;font-weight:700}.attempt-meta{display:flex;justify-content:space-between;margin-bottom:7px}.attempt-meta strong,.attempt-meta small{font-size:11px}.attempt-meta small{color:oklch(var(--bc) / .6)}.text-correct{color:oklch(var(--su))}.text-incorrect{color:oklch(var(--er))}.attempt-empty{color:oklch(var(--bc) / .6);font-size:12px}@media(max-width:800px){.records-head{display:grid}.question-summary{grid-template-columns:28px 1fr 70px}.question-score,.chevron{display:none}.answer-grid{grid-template-columns:1fr}}
</style>
