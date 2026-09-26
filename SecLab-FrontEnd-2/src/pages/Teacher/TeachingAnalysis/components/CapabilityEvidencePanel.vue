<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CapabilityEvidenceResponseDto } from '../../../../api'
import { getTimelineEventPresentation } from '../analysisPresentation'

const props = defineProps<{ data: CapabilityEvidenceResponseDto | null }>()
const activeDimension = ref('troubleshooting')

watch(() => props.data, (value) => {
  if (value?.dimensions.length && !value.dimensions.some((item) => item.key === activeDimension.value)) {
    activeDimension.value = value.dimensions[0].key
  }
}, { immediate: true })

const selected = computed(() => props.data?.dimensions.find((item) => item.key === activeDimension.value) || null)
const score = (value?: number | null) => typeof value === 'number' ? value.toFixed(1) : '—'
</script>

<template>
  <section class="evidence-block">
    <div class="section-heading">
      <h3>能力分数与证据</h3>
      <small v-if="data?.computedAt">画像更新于 {{ new Date(data.computedAt).toLocaleString('zh-CN') }}</small>
    </div>
    <div v-if="data" class="dimension-tabs">
      <button
        v-for="dimension in data.dimensions"
        :key="dimension.key"
        :class="{ active: activeDimension === dimension.key }"
        @click="activeDimension = dimension.key"
      >
        <span>{{ dimension.label }}</span><strong>{{ score(dimension.score) }}</strong>
      </button>
    </div>
    <div v-if="selected" class="evidence-content">
      <p class="dimension-summary">{{ selected.summary }}</p>
      <div v-if="selected.evidence.length" class="evidence-list">
        <article v-for="item in selected.evidence" :key="`${item.kind}-${item.sourceId}`">
          <span :class="`event-badge tone-${getTimelineEventPresentation(item.kind, item.retryOutcome || item.status).tone}`">
            {{ getTimelineEventPresentation(item.kind, item.retryOutcome || item.status).label }}
          </span>
          <div>
            <strong>{{ item.title }}</strong>
            <small>{{ item.occurredAt ? new Date(item.occurredAt).toLocaleString('zh-CN') : '时间未记录' }}</small>
            <code v-if="item.command">{{ item.command }}</code>
            <p v-if="item.detail">{{ item.detail }}</p>
          </div>
        </article>
      </div>
      <div v-else class="empty-inline">当前维度还没有可展开的学习证据。</div>
    </div>
    <div v-else class="empty-inline">暂无能力画像</div>
  </section>
</template>

<style scoped>
.section-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:20px; margin-bottom:14px; }
h3 { margin:0; color:oklch(var(--bc)); font-size:16px; } p { margin:5px 0 0; color:oklch(var(--bc) / .6); font-size:12px; line-height:1.6; }
.section-heading small { color:oklch(var(--bc) / .6); font-size:11px; white-space:nowrap; }
.dimension-tabs { display:grid; grid-template-columns:repeat(5,1fr); border:1px solid oklch(var(--bc) / .12); border-radius:8px; overflow:hidden; }
.dimension-tabs button { display:grid; gap:5px; padding:13px; border:0; border-right:1px solid oklch(var(--bc) / .12); background:oklch(var(--b1)); text-align:left; cursor:pointer; }
.dimension-tabs button:last-child { border-right:0; } .dimension-tabs button.active { background:oklch(var(--b2)); box-shadow:inset 0 -2px oklch(var(--p)); }
.dimension-tabs span { color:oklch(var(--bc) / .6); font-size:11px; } .dimension-tabs strong { color:oklch(var(--p)); font-size:19px; }
.evidence-content { margin-top:14px; padding:15px; border:1px solid oklch(var(--bc) / .12); border-radius:8px; background:oklch(var(--b1)); }
.dimension-summary { margin:0 0 12px; color:oklch(var(--bc)); }
.evidence-list { display:grid; gap:9px; }
.evidence-list article { display:grid; grid-template-columns:104px minmax(0,1fr); gap:12px; padding:11px 0; border-top:1px solid oklch(var(--bc) / .12); }
.evidence-list article:first-child { border-top:0; } .evidence-list strong,.evidence-list small { display:block; }
.evidence-list strong { color:oklch(var(--bc)); font-size:12px; } .evidence-list small { margin-top:3px; color:oklch(var(--bc) / .6); font-size:10px; }
.evidence-list code { display:block; margin-top:7px; padding:7px 9px; border-radius:5px; background:oklch(var(--bc)); color:oklch(var(--bc) / .12); font-size:11px; white-space:pre-wrap; word-break:break-all; }
.evidence-list p { margin-top:5px; color:oklch(var(--bc) / .6); }
.event-badge { align-self:start; padding:4px 7px; border-radius:999px; text-align:center; font-size:10px; font-weight:700; }
.tone-danger { background:oklch(var(--b2)); color:oklch(var(--er)); }.tone-warning { background:oklch(var(--bc) / .12); color:oklch(var(--wa));}.tone-success { background:oklch(var(--bc) / .12); color:oklch(var(--su));}.tone-info { background:oklch(var(--b2)); color:oklch(var(--p));}.tone-neutral { background:oklch(var(--bc) / .12); color:oklch(var(--bc) / .6);}
.empty-inline { padding:25px; color:oklch(var(--bc) / .6); font-size:12px; text-align:center; }
@media(max-width:900px){.dimension-tabs{grid-template-columns:repeat(2,1fr)}.dimension-tabs button{border-bottom:1px solid oklch(var(--bc) / .12)}.section-heading{display:block}.section-heading small{display:block;margin-top:6px}}
</style>
