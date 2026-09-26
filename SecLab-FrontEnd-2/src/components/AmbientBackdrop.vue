<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'

/**
 * 学生端全局背景氛围层（只在暗色主题下出现）。
 *
 * 思路和主页那套粒子不同：主页是 50 个 DOM 节点各自跑动画，这里整层只有 6 个节点 ——
 * 星点全部用 radial-gradient 画进一张 background-image，靠 transform 平移做视差漂移。
 * transform / opacity 都是合成器属性，不触发重排重绘，所以放在每一页都不会掉帧。
 *
 * 无缝循环的原理：图案以 tile 为周期平铺，元素比视口多留一个 tile 的余量，
 * 每轮正好平移一个 tile，接回原点时图案完全对齐。
 */

const { currentTheme } = useTheme()
const isNight = computed(() => currentTheme.value === 'night')

type StarLayer = {
  key: string
  image: string
  tile: number
  duration: number
  twinkle: boolean
}

/** 生成一层星点。位置在模块加载时算一次，之后不再变化 */
const buildStarImage = (count: number, radius: number, alpha: number, token: string) => {
  const dots: string[] = []
  for (let i = 0; i < count; i += 1) {
    const x = (Math.random() * 100).toFixed(2)
    const y = (Math.random() * 100).toFixed(2)
    dots.push(
      `radial-gradient(${radius}px ${radius}px at ${x}% ${y}%, oklch(var(${token}) / ${alpha}) 0%, transparent 65%)`,
    )
  }
  return dots.join(', ')
}

/**
 * 三层不同疏密/速度，叠出视差纵深感。
 *
 * 2026-08-08 为答辩投影再提一档。投影仪对暗部压缩极重，原来 1px / .42 透明度的远景星点
 * 在幕布上基本会被吃掉。这一版把三层的**数量、半径、透明度**一起提：
 *   far  84 -> 128 颗，1   -> 1.5px，.42 -> .66
 *   mid  40 ->  58 颗，1.5 -> 2.2px，.62 -> .88
 *   near 16 ->  24 颗，2.2 -> 3.0px，.92 -> 1
 * 半径比透明度更管用 —— 星点是 radial-gradient 画的，1px 的点在投影上是亚像素，
 * 提透明度也救不回来，得先让它有面积。
 *
 * 注意不要动地板色：地板 base-300 是 rgb(10,17,32)，比卡面 base-100 的 rgb(15,23,42)
 * 还暗；把地板提亮会让卡片边界糊掉，反而更难看。要"整体不那么暗"靠下面的柔光去托。
 */
const starLayers: StarLayer[] = [
  { key: 'far', image: buildStarImage(128, 1.5, 0.66, '--bc'), tile: 260, duration: 210, twinkle: false },
  { key: 'mid', image: buildStarImage(58, 2.2, 0.88, '--bc'), tile: 340, duration: 145, twinkle: false },
  { key: 'near', image: buildStarImage(24, 3, 1, '--p'), tile: 420, duration: 100, twinkle: true },
]

// 大面积柔光。用 radial-gradient 而不是 blur-3xl —— 滤镜模糊要额外一遍离屏渲染，渐变本身就是软的。
// 这是"整体提亮"的主力：它铺的面积大、边缘软，能把大片死黑托起来，又不会像提地板那样吃掉卡片边界。
// alpha 各提约 70%，size 一并放大，让相邻两团有重叠、不留黑带。
const glows = [
  { key: 'p', token: '--p', alpha: 0.34, size: 820, left: '10%', top: '4%', duration: 26 },
  { key: 's', token: '--s', alpha: 0.3, size: 900, left: '60%', top: '26%', duration: 32 },
  { key: 'a', token: '--a', alpha: 0.26, size: 760, left: '34%', top: '66%', duration: 22 },
]
</script>

<template>
  <div v-if="isNight" class="ambient-backdrop" aria-hidden="true">
    <!-- ⑦ 极淡网格：星点读作「太空」，网格读作「网络 / 控制台」，更贴安全平台的语境。
         顶部渐隐，避免和顶栏抢注意力 -->
    <div class="ambient-grid"></div>

    <div
      v-for="(glow, index) in glows"
      :key="glow.key"
      class="ambient-glow"
      :style="{
        width: `${glow.size}px`,
        height: `${glow.size}px`,
        left: glow.left,
        top: glow.top,
        background: `radial-gradient(circle, oklch(var(${glow.token}) / ${glow.alpha}) 0%, transparent 70%)`,
        animationDuration: `${glow.duration}s`,
        animationDelay: `${index * -6}s`,
      }"
    ></div>

    <div
      v-for="layer in starLayers"
      :key="layer.key"
      class="ambient-stars"
      :class="{ 'ambient-stars--twinkle': layer.twinkle }"
      :style="{
        '--tile': `${layer.tile}px`,
        backgroundImage: layer.image,
        backgroundSize: `${layer.tile}px ${layer.tile}px`,
        width: `calc(100% + ${layer.tile}px)`,
        height: `calc(100% + ${layer.tile}px)`,
        animationDuration: `${layer.duration}s`,
      }"
    ></div>
  </div>
</template>

<style scoped>
.ambient-backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

/* ⑦ 44px 网格，线色只有 base-content 的 3.5%，几乎看不见，
   但能让大片空白显得「有结构」而不是「空」 */
.ambient-grid {
  position: absolute;
  inset: 0;
  /* .035 在投影上等于没有，提到 .055；遮罩范围也放宽一点，让网格铺得更远 */
  background-image:
    linear-gradient(oklch(var(--bc) / 0.055) 1px, transparent 1px),
    linear-gradient(90deg, oklch(var(--bc) / 0.055) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(ellipse 140% 100% at 50% 0%, #000 34%, transparent 88%);
  mask-image: radial-gradient(ellipse 140% 100% at 50% 0%, #000 34%, transparent 88%);
}

.ambient-stars {
  position: absolute;
  top: 0;
  left: 0;
  background-repeat: repeat;
  will-change: transform;
  animation-name: ambientDrift;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

.ambient-stars--twinkle {
  animation-name: ambientDrift, ambientTwinkle;
  animation-duration: inherit, 7s;
  animation-timing-function: linear, ease-in-out;
  animation-iteration-count: infinite, infinite;
  animation-direction: normal, alternate;
}

.ambient-glow {
  position: absolute;
  border-radius: 9999px;
  will-change: transform;
  animation-name: ambientFloat;
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}

/* 每轮正好平移一个 tile，图案周期对齐，接回原点无缝 */
@keyframes ambientDrift {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(calc(var(--tile) * -1), calc(var(--tile) * -1), 0);
  }
}

@keyframes ambientTwinkle {
  from {
    opacity: 0.55;
  }
  to {
    opacity: 1;
  }
}

@keyframes ambientFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }
  50% {
    transform: translate3d(24px, -32px, 0);
  }
}

/* 尊重系统的「减少动态效果」设置：星点保留，漂移停掉 */
@media (prefers-reduced-motion: reduce) {
  .ambient-stars,
  .ambient-glow {
    animation: none;
  }
}
</style>
