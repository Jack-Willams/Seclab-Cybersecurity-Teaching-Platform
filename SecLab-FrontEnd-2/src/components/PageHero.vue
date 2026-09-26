<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'

/**
 * 列表页页头（课程 / 实验共用）。
 *
 * 原来两页各写一份 `<h1 class="text-3xl font-bold text-base-content">`，纯实色、
 * 除了字号没有任何身份感。这里给它一套统一的处理：
 *   单行等宽 eyebrow（两侧渐隐横线） + 渐变主标题 + 副标题。
 * eyebrow 的等宽字 + 大字距和教师端仪表台是同一套语汇，整站读起来像一个系统。
 *
 * 抽成组件而不是各页复制：两页页头必须长得一模一样，复制迟早会走样。
 */
defineProps<{
  /** 等宽小字，全大写效果由 CSS 给，传中文也可以 */
  kicker: string
  title: string
  subtitle: string
}>()

/**
 * 暗色分支不用 `:global([data-theme='night']) .page-hero`：
 * scoped 块里 `:global(X) Y` 会被 Vue 的编译器压成光秃秃的 X，后半截选择器直接丢掉
 * （CourseOverView.vue 里记过同一个坑）。自己打个 class 最稳。
 */
const { currentTheme } = useTheme()
const isNight = computed(() => currentTheme.value === 'night')
</script>

<template>
  <header class="page-hero" :class="{ 'is-night': isNight }">
    <div class="hero-kicker">
      <span class="kicker-rule kicker-rule--l" aria-hidden="true"></span>
      <span class="kicker-text">{{ kicker }}</span>
      <span class="kicker-rule kicker-rule--r" aria-hidden="true"></span>
    </div>

    <h1 class="hero-title">{{ title }}</h1>

    <p class="hero-sub">
      <!-- 渐变只加在 .sub-text 上，不加在 <p> 上：
           background-clip:text 会把 -webkit-text-fill-color:transparent 传给后代，
           插槽里那个「正在同步…」的 spinner 文字会跟着一起变透明 -->
      <span class="sub-text">{{ subtitle }}</span>
      <!-- 给「正在同步最新课程…」这类页内状态留的位置 -->
      <slot name="status" />
    </p>
  </header>
</template>

<style scoped>
.page-hero {
  position: relative;
  margin-bottom: 1.5rem;
  text-align: center;

  /* ── 两套渐变，分工固定 ────────────────────────────────
     标题走主色（浅色下是蓝紫 -> 天蓝，暗色下是紫 -> 蓝 -> 青）；
     上下小字走中性银灰。两者必须是不同色系，否则整块糊成一片。

     浅色主题的调色板里没有紫色（--p 是蓝色 #2563eb），所以这里直接写死一条真紫
     渐变，不走 token。用 --p -> --s 试过，secondary #0ea5e9 在浅底上只有 2.25:1，
     连大字号的 3:1 都过不了；violet-600 -> blue-600 实测 4.62 / 4.19:1。 */
  --hero-title-grad: linear-gradient(100deg, #7c3aed 0%, #2563eb 100%);

  /* 小字的银灰。两端压暗、中间提亮，还是那道金属高光，只是搬到了小字上。
     11px 小字按正文标准要 4.5:1，所以两端不敢压太狠。 */
  --hero-sub-grad: linear-gradient(
    100deg,
    oklch(var(--bc) / 0.72) 0%,
    oklch(var(--bc) / 0.95) 42%,
    oklch(var(--bc) / 0.68) 100%
  );
}

/* 暗色底下三个主色都够亮（实测 p 8.8 / s 6.32 / a 7.07:1），标题可以放开用完整的 p-s-a */
.page-hero.is-night {
  --hero-title-grad: linear-gradient(
    100deg,
    oklch(var(--p)) 0%,
    oklch(var(--s)) 48%,
    oklch(var(--a)) 100%
  );
}

.kicker-text,
.sub-text {
  background: var(--hero-sub-grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

/* 标题背后的一团柔光。跟着标题回到主色 —— 紫色标题配中性白晕会显得发灰。
   只在暗色下开；白底上这团光是看不见的脏印子。
   用 radial-gradient 不用 blur：滤镜要多一遍离屏渲染，渐变本身就是软的。 */
.page-hero::before {
  content: '';
  position: absolute;
  top: 6px;
  left: 50%;
  width: min(560px, 90%);
  height: 120px;
  transform: translateX(-50%);
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(closest-side, oklch(var(--p) / 0.2), transparent 72%);
}

.page-hero.is-night::before {
  opacity: 1;
}

/* ---------- eyebrow ---------- */
.hero-kicker {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 6px;
}

.kicker-rule {
  width: clamp(24px, 6vw, 56px);
  height: 1px;
}

/* 横线跟 eyebrow 走银灰，别用主色 —— 主色横线会和主色标题连成一块，
   eyebrow 那一行就不再是独立的一层了 */
.kicker-rule--l {
  background: linear-gradient(90deg, transparent, oklch(var(--bc) / 0.45));
}

.kicker-rule--r {
  background: linear-gradient(90deg, oklch(var(--bc) / 0.45), transparent);
}

.kicker-text {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.26em;
  /* 中文不受影响，只把混在里面的拉丁字母抬成大写 */
  text-transform: uppercase;
}

/* ---------- 主标题 ---------- */
.hero-title {
  position: relative;
  margin-bottom: 4px;
  font-size: clamp(1.75rem, 2.4vw, 2.125rem);
  font-weight: 800;
  letter-spacing: 0.06em;
  line-height: 1.2;

  background: var(--hero-title-grad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}

/* background-clip:text 挂了的话，透明填充会把字变没。给个实色兜底 */
@supports not ((-webkit-background-clip: text) or (background-clip: text)) {
  .hero-title {
    background: none;
    color: oklch(var(--p));
    -webkit-text-fill-color: currentColor;
  }
}

.hero-sub {
  position: relative;
  font-size: 0.875rem;
}
</style>
