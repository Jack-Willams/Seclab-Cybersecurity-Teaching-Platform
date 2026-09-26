<script setup lang="ts">
import type { CapabilityEvidenceItemDto } from '../../../../api'
import { getTimelineEventPresentation } from '../analysisPresentation'

defineProps<{ items: CapabilityEvidenceItemDto[] }>()
</script>

<template>
  <section class="replay-block">
    <div class="section-heading"><h3>安全实验学习回放</h3></div>
    <div v-if="items.length" class="timeline">
      <article v-for="item in items" :key="`${item.kind}-${item.sourceId}`" :class="`tone-${getTimelineEventPresentation(item.kind, item.retryOutcome || item.status).tone}`">
        <div class="time">{{ item.occurredAt ? new Date(item.occurredAt).toLocaleString('zh-CN') : '时间未记录' }}</div>
        <div class="event-card">
          <div class="event-head"><strong>{{ getTimelineEventPresentation(item.kind, item.retryOutcome || item.status).label }}</strong><span v-if="item.retryOutcome === 'recovered'">已恢复</span></div>
          <p>{{ item.title }}</p>
          <code v-if="item.command">{{ item.command }}</code>
          <small v-if="item.detail">{{ item.detail }}</small>
        </div>
      </article>
    </div>
    <div v-else class="empty-inline">当前学生还没有可回放的实验过程。</div>
  </section>
</template>

<style scoped>
.section-heading { margin-bottom:14px; } h3 { margin:0; color:oklch(var(--bc)); font-size:16px; }.section-heading p { margin:5px 0 0; color:oklch(var(--bc) / .6); font-size:12px; }
.timeline { position:relative; display:grid; gap:0; }.timeline article { display:grid; grid-template-columns:150px minmax(0,1fr); gap:22px; min-height:82px; }
.time { padding-top:14px; color:oklch(var(--bc) / .6); font-size:10px; text-align:right; }.event-card { position:relative; padding:12px 14px 15px; border-left:2px solid oklch(var(--bc) / .12); }
.event-card::before { position:absolute; top:17px; left:-6px; width:10px; height:10px; border-radius:50%; background:oklch(var(--bc) / .6); content:""; }
.tone-danger .event-card::before { background:oklch(var(--er)); }.tone-warning .event-card::before { background:oklch(var(--wa)); }.tone-success .event-card::before { background:oklch(var(--su)); }.tone-info .event-card::before { background:oklch(var(--p)); }
.event-head { display:flex; align-items:center; gap:8px; }.event-head strong { color:oklch(var(--bc)); font-size:12px; }.event-head span { padding:2px 6px; border-radius:999px; background:oklch(var(--bc) / .12); color:oklch(var(--su)); font-size:9px; }
.event-card p { margin:5px 0; color:oklch(var(--bc) / .6); font-size:12px; }.event-card small { display:block; margin-top:5px; color:oklch(var(--bc) / .6); font-size:10px; }.event-card code { display:block; margin-top:7px; padding:7px 9px; border-radius:5px; background:oklch(var(--bc)); color:oklch(var(--bc) / .12); font-size:11px; word-break:break-all; }
.empty-inline { padding:28px; color:oklch(var(--bc) / .6); font-size:12px; text-align:center; }
@media(max-width:700px){.timeline article{grid-template-columns:1fr;gap:0}.time{text-align:left;padding:8px 0 3px 14px}.event-card{margin-left:4px}}
</style>
