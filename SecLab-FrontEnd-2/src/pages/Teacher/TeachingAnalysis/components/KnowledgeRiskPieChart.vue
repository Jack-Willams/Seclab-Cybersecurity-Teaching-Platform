<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArcElement, Chart, DoughnutController, Tooltip } from 'chart.js'
import type { KnowledgeRiskItemDto } from '../../../../api'
import { buildKnowledgeRiskPie, classifyKnowledgeRisk, formatRiskRatePercent } from '../analysisPresentation'
import { useTheme } from '../../../../composables/useTheme'

Chart.register(DoughnutController, ArcElement, Tooltip)

const { currentTheme } = useTheme()

/**
 * 读 daisyUI 的语义色 token，拼成 canvas 能用的颜色字符串。
 *
 * 圆环是画在 canvas 上的，吃不到 CSS 变量，所以扇区之间那圈描边原来直接写死 '#ffffff' ——
 * 亮色下正好和卡面同色、看着像"留白"，暗色下就变成一圈刺眼的白线。
 * 这里改成运行时读 --b1（卡面色），两个主题下都自动等于卡片背景。
 *
 * daisyUI 4 里 token 存的是 `L C H` 三元组（如 `--b1: 100% 0 0`），拼上 oklch() 即可。
 */
const tokenColor = (token: string) => {
  if (typeof window === 'undefined') return '#ffffff'
  const raw = getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  return raw ? `oklch(${raw})` : '#ffffff'
}

const props = defineProps<{
  items: KnowledgeRiskItemDto[]
  selectedCourseId: number
}>()
const emit = defineEmits<{ select: [item: KnowledgeRiskItemDto] }>()

const canvas = ref<HTMLCanvasElement | null>(null)
const model = computed(() => buildKnowledgeRiskPie(props.items, props.selectedCourseId))

/**
 * 圆环的图例。
 *
 * 原来只是右上角一排 11px 色块，写着"严重错误 / 重点关注 / 需要巩固 / 掌握良好"——
 * 光有名字，不说这四档是按什么分的，教师看了圆环也不知道红色到底红在哪。
 * 这里补上判定阈值和每档命中的知识点数，圆环才自己解释得清楚。
 *
 * 阈值取自 classifyKnowledgeRisk：≥.6 / ≥.4 / ≥.2 / 其余。这里用每档的代表值
 * 反查颜色，保证和扇区、左边框用的是同一套色，不会两处各写一份。
 */
const legendBands = computed(() => ([
  { tone: 'high', range: '错题率 ≥ 60%', probe: 0.7 },
  { tone: 'medium', range: '40% – 60%', probe: 0.5 },
  { tone: 'attention', range: '20% – 40%', probe: 0.3 },
  { tone: 'good', range: '低于 20%', probe: 0 },
] as const).map((band) => {
  const presentation = classifyKnowledgeRisk(band.probe)
  const hit = model.value.slices.filter((slice) => slice.tone === band.tone)
  return {
    tone: band.tone,
    range: band.range,
    label: presentation.label,
    color: presentation.color,
    // 「掌握良好」这一档还要算上完全没错的知识点（它们不进圆环，单独列在下面）
    count: hit.length + (band.tone === 'good' ? model.value.mastered.length : 0),
    incorrect: hit.reduce((total, slice) => total + slice.item.incorrectCount, 0),
  }
}))
let chart: Chart<'doughnut'> | null = null

function select(item: KnowledgeRiskItemDto) {
  emit('select', item)
}

function drawChart() {
  if (!canvas.value || typeof window === 'undefined') return
  chart?.destroy()
  if (!model.value.slices.length) {
    chart = null
    return
  }
  chart = new Chart(canvas.value, {
    type: 'doughnut',
    data: {
      labels: model.value.slices.map((slice) => slice.item.knowledgePointName),
      datasets: [{
        data: model.value.slices.map((slice) => Math.max(0, slice.item.incorrectCount)),
        backgroundColor: model.value.slices.map((slice) => slice.color),
        // 扇区之间那圈描边取卡面色 —— 写死 '#ffffff' 的话暗色下会变成一圈刺眼白线
        borderColor: tokenColor('--b1'),
        borderWidth: 3,
        spacing: 2,
        hoverBorderWidth: 4,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '56%',
      animation: { duration: 280 },
      onClick: (_event, elements) => {
        const index = elements[0]?.index
        if (typeof index === 'number') select(model.value.slices[index].item)
      },
      plugins: {
        // 关掉 Chart.js 自带图例：知识点名字较长，7 个以上会占掉三行把圆环挤扁，
        // 而右侧的知识点清单已经给出了名称、人数和占比，图例是重复信息。
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => {
              const slice = model.value.slices[context.dataIndex]
              return `${slice.item.knowledgePointName}：错误占比 ${slice.sharePercent}%，知识点错题率 ${slice.incorrectRatePercent}%`
            },
          },
        },
      },
    },
  })
}

onMounted(() => void nextTick(drawChart))
watch(model, () => void nextTick(drawChart), { deep: true })
// 切主题要重画：扇区描边取的是 --b1，canvas 不会跟着 CSS 变量自动更新
watch(currentTheme, () => void nextTick(drawChart))
onBeforeUnmount(() => chart?.destroy())
</script>

<template>
  <section class="risk-pie-block">
    <div class="section-heading">
      <div>
        <h2>本实验知识点错误分布</h2>
      </div>
      <div class="pie-summary"><strong>{{ model.slices.length + model.mastered.length }}</strong><span>个知识点</span><i></i><strong>{{ model.totalIncorrect }}</strong><span>次错误</span></div>
    </div>

    <div v-if="model.slices.length" class="pie-layout">
      <div class="chart-col">
        <div class="chart-wrap">
          <canvas ref="canvas" aria-label="当前实验知识点错误占比饼图"></canvas>
          <div class="chart-center"><strong>{{ model.totalIncorrect }}</strong><span>错误记录</span></div>
        </div>

        <ul class="risk-legend" aria-label="知识点错题率分档说明">
          <li v-for="band in legendBands" :key="band.tone" :class="{ vacant: !band.count }">
            <i :style="{ background: band.color }" aria-hidden="true"></i>
            <span>
              <strong>{{ band.label }}</strong>
              <small>{{ band.range }}</small>
            </span>
            <em>{{ band.count }}<b>个知识点</b></em>
          </li>
        </ul>
      </div>
      <div class="slice-list" aria-label="可查看的知识点扇区">
        <button
          v-for="slice in model.slices"
          :key="slice.key"
          type="button"
          class="slice-button"
          :data-risk-key="slice.key"
          :data-tone="slice.tone"
          :style="{ '--risk-color': slice.color }"
          :aria-label="`${slice.item.knowledgePointName}，错误占比 ${slice.sharePercent}%，知识点错题率 ${slice.incorrectRatePercent}%，点击查看详情`"
          @click="select(slice.item)"
        >
          <i></i>
          <span><strong>{{ slice.item.knowledgePointName }}</strong><small>{{ slice.item.incorrectStudentCount }} 人出错 · {{ slice.item.incorrectCount }} 次错误</small></span>
          <em>{{ slice.sharePercent }}%</em>
        </button>
      </div>
    </div>

    <div v-else class="all-mastered"><strong>当前实验暂未发现错误知识点</strong></div>

    <section v-if="model.mastered.length" class="mastered-block">
      <header><h3>掌握良好</h3><strong>{{ model.mastered.length }} 项</strong></header>
      <div class="mastered-list">
        <button
          v-for="item in model.mastered"
          :key="`${item.knowledgePointId}-${item.knowledgePointName}`"
          type="button"
          :data-mastered-key="`${item.knowledgePointId}-${item.knowledgePointName}`"
          @click="select(item)"
        ><span>{{ item.knowledgePointName }}</span><small>{{ item.attemptedStudentCount }} 人作答 · 错题率 {{ formatRiskRatePercent(item.incorrectRate) }}%</small></button>
      </div>
    </section>

    <div v-if="!model.slices.length && !model.mastered.length" class="empty-inline">本实验暂无知识点数据</div>
  </section>
</template>

<style scoped>
.risk-pie-block{padding:2px}.section-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}.section-heading h2{margin:0;color:oklch(var(--bc));font-size:17px}.section-heading p{max-width:720px;margin:6px 0 0;color:oklch(var(--bc) / .6);font-size:12px;line-height:1.6}.pie-summary{display:flex;align-items:baseline;gap:5px;color:oklch(var(--bc) / .6);font-size:11px;white-space:nowrap}.pie-summary strong{color:oklch(var(--p));font-size:19px}.pie-summary i{width:1px;height:16px;margin:0 7px;background:oklch(var(--bc) / .12)}/* 图例：从右上角那排 11px 小色块，改成圆环下方的说明块。
   每档给出「名称 + 判定阈值 + 命中的知识点数」，圆环才自己解释得清楚；
   顺带填上图表栏因为圆环缩小而空出来的竖向空间。 */
.risk-legend{display:grid;gap:4px;margin:16px 0 0;padding:0;list-style:none}
.risk-legend li{display:grid;grid-template-columns:10px minmax(0,1fr) auto;gap:10px;align-items:center;padding:7px 10px;border-radius:7px;background:oklch(var(--b2) / .55)}
.risk-legend li.vacant{opacity:.45}
.risk-legend i{width:10px;height:10px;border-radius:3px}
.risk-legend span{display:flex;align-items:baseline;gap:8px;min-width:0}
.risk-legend strong{color:oklch(var(--bc) / .85);font-size:12px;font-weight:650;white-space:nowrap}
.risk-legend small{color:oklch(var(--bc) / .6);font-size:10px;white-space:nowrap}
.risk-legend em{display:flex;align-items:baseline;gap:3px;color:oklch(var(--bc));font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:13px;font-style:normal;font-weight:700;font-variant-numeric:tabular-nums}
.risk-legend em b{color:oklch(var(--bc) / .6);font-size:10px;font-weight:500}/* 原来是 50/50 + 圆环 420px：圆的直径受高度限制只有 420，却被塞进 652px 宽的格子里，
   左右各空掉 ~116px，这就是"比例难看"的来源。改成 38/62 —— 图这一栏收窄到刚好包住圆，
   多出来的宽度给右侧排行榜，7 条正好放得下，不必再为 61px 挤一根滚动条。 */
/* 原来是 50/50 + 圆环 420px：圆的直径受高度限制只有 420，却被塞进 652px 宽的格子里，
   左右各空掉 ~116px，这就是"比例难看"的来源。改成 40/60 —— 图这一栏收窄，
   多出来的宽度给右侧排行榜，7 条正好放得下，不必再为 61px 挤一根滚动条。 */
.pie-layout{display:grid;grid-template-columns:minmax(260px,40fr) minmax(340px,60fr);gap:26px;align-items:start}.chart-col{min-width:0}.chart-wrap{position:relative;height:250px;min-width:0}.chart-center{position:absolute;inset:50% auto auto 50%;display:grid;transform:translate(-50%,-50%);text-align:center;pointer-events:none}.chart-center strong{color:oklch(var(--bc));font-size:27px}.chart-center span{color:oklch(var(--bc) / .6);font-size:11px}.slice-list{display:grid;gap:6px;max-height:none;padding-right:2px;align-content:start}.slice-button{--risk-color:oklch(var(--bc) / .6);display:grid;width:100%;grid-template-columns:12px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 12px;border:1px solid oklch(var(--bc) / .12);border-left:4px solid var(--risk-color);border-radius:8px;background:oklch(var(--b1));color:oklch(var(--bc));text-align:left;cursor:pointer;transition:transform .15s ease,border-color .15s ease,box-shadow .15s ease}.slice-button:hover,.slice-button:focus-visible{transform:translateX(3px);border-color:var(--risk-color);box-shadow:0 5px 15px oklch(var(--bc) / .12);outline:none}.slice-button>i{width:9px;height:9px;border:2px solid oklch(var(--b1));border-radius:50%;background:var(--risk-color);box-shadow:0 0 0 1px var(--risk-color)}/* 名称和元信息原来上下两行堆叠，7 行就要 427px、比左边的圆环还高，整块高度全被它顶起来。
   榜单栏现在有 810px 宽，横排完全放得下 —— 压成一行后每行 ~36px，7 行 ~290px，
   正好和圆环等高，整块少掉 100 多像素。 */
.slice-button span{display:flex;align-items:baseline;gap:9px;min-width:0}.slice-button span strong{flex:0 1 auto;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.slice-button span small{flex:0 0 auto;margin-top:0;color:oklch(var(--bc) / .6);font-size:10px;white-space:nowrap}.slice-button em{color:var(--risk-color);font-size:18px;font-style:normal;font-weight:750}.mastered-block{margin-top:18px;padding:15px;border:1px solid oklch(var(--bc) / .12);border-radius:9px;background:oklch(var(--b2))}.mastered-block header{display:flex;justify-content:space-between;gap:12px}.mastered-block h3{margin:0;color:oklch(var(--su));font-size:14px}.mastered-block p{margin:4px 0 0;color:oklch(var(--bc) / .6);font-size:10px}.mastered-block header>strong{color:oklch(var(--su));font-size:13px}.mastered-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:11px}.mastered-list button{display:grid;gap:3px;padding:8px 10px;border:1px solid oklch(var(--bc) / .18);border-radius:7px;background:oklch(var(--b1));color:oklch(var(--su));text-align:left;cursor:pointer}.mastered-list button:hover,.mastered-list button:focus-visible{border-color:oklch(var(--su));outline:none}.mastered-list span{font-size:11px;font-weight:700}.mastered-list small{color:oklch(var(--bc) / .6);font-size:9px}.all-mastered{display:grid;gap:5px;place-items:center;padding:34px;border-radius:9px;background:oklch(var(--b2));color:oklch(var(--bc) / .6);font-size:11px}.all-mastered strong{color:oklch(var(--su));font-size:15px}.empty-inline{padding:34px;color:oklch(var(--bc) / .6);font-size:12px;text-align:center}@media(max-width:900px){.pie-layout{grid-template-columns:1fr}.chart-wrap{height:340px}.slice-list{max-height:none}.risk-legend{justify-content:flex-start;flex-wrap:wrap}}@media(max-width:600px){.section-heading{display:grid}.pie-summary{justify-self:start}.chart-wrap{height:250px}.slice-list{max-height:none}.slice-button{grid-template-columns:10px minmax(0,1fr) auto}.risk-legend{gap:9px}}
</style>
