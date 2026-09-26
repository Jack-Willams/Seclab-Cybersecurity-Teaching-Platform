<script setup lang="ts">
import Header from "./Header.vue";
import AmbientBackdrop from "../../components/AmbientBackdrop.vue";
import { useRoute } from "vue-router";
import { computed, onBeforeUnmount, ref } from "vue";

const route = useRoute();
const isChatPage = computed(() => route.path === '/user/chat' || route.path === '/user/chat/');

/* 快速滚动时的「屏幕轻微缩放」抖动
   ------------------------------------------------------------------
   鼠标停在页面上不动、滚轮快速滚动时，卡片是从静止的光标底下一张张扫过去的，
   每张都会被瞬间命中一次 :hover，触发 style.css 里
   `.card:hover .cover img { transform: scale(1.06) }` 那条 0.5s 过渡 ——
   放大刚起步光标就离开了，又反向动画回 1.0，看上去就是「抖一下再弹回原比例」。

   治本的办法不是去掉 hover 效果，而是让滚动期间 :hover 压根匹配不上：
   给滚动容器挂 .is-scrolling，把子树的指针事件关掉（见 style.css）。
   停止滚动 120ms 后恢复，正常的鼠标悬停体验不受影响。 */
const isScrolling = ref(false);
let scrollIdleTimer: ReturnType<typeof setTimeout> | undefined;

const handleScroll = () => {
  isScrolling.value = true;
  if (scrollIdleTimer) clearTimeout(scrollIdleTimer);
  scrollIdleTimer = setTimeout(() => {
    isScrolling.value = false;
  }, 120);
};

onBeforeUnmount(() => {
  if (scrollIdleTimer) clearTimeout(scrollIdleTimer);
});
</script>

<template>
    <!-- ① 页面底色降到 base-300，卡片留在 base-100 —— 暗色下靠亮度差表达层级 -->
    <div class="fixed w-full h-full flex flex-col bg-base-300">
        <!-- 暗色主题下的星点/柔光背景，铺在所有学生端页面之下 -->
        <AmbientBackdrop />

        <!-- Header 自己是 fixed z-50，本来就在背景层之上；这里不能再加 relative，
             Tailwind 的 .relative 排在 .fixed 之后，会把定位方式覆盖掉 -->
        <Header></Header>
        <div
          class="w-full relative z-10 flex-1 min-h-0"
          :class="{ 'overflow-y-auto': !isChatPage, 'px-8 pt-8': !isChatPage, 'is-scrolling': isScrolling }"
          @scroll.passive="handleScroll"
        >
          <RouterView v-slot="{ Component }">
            <transition name="page" mode="out-in" appear>
              <!-- key 用 path：/user/module/1 → /user/module/2 这种只换参数的跳转
                   命中的是同一个路由记录，不加 key 组件会被复用，onMounted 不再执行，
                   页面就会停在上一个实验/课程的内容上 -->
              <component :is="Component" :key="route.path" />
            </transition>
          </RouterView>
        </div>
    </div>
</template>

<style scoped>
/* 页面切换动画：旧页面先淡出，新页面再淡入（mode="out-in"）。
   关键是只过渡 opacity/transform 两个合成器属性 —— 原来写的是 `transition: all`，
   而 .page-leave-active 会把元素改成 position:absolute，于是 width/height/top/left
   这些布局属性也被纳入过渡，一次切页要串行跑好几轮，实测要 2.2s。
   现在是老老实实的 0.26s 淡出 + 0.34s 淡入 = 0.6s。 */
.page-leave-active {
  transition: opacity 0.26s cubic-bezier(0.4, 0, 1, 1), transform 0.26s cubic-bezier(0.4, 0, 1, 1);
}

.page-enter-active {
  transition: opacity 0.34s cubic-bezier(0, 0, 0.2, 1), transform 0.34s cubic-bezier(0, 0, 0.2, 1);
}

.page-enter-from {
  opacity: 0;
  transform: scale(0.97) translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: scale(0.98);
}

/* 确保动画期间内容不会溢出 */


/* 防止页面闪烁 */
.page-leave-active {
  position: absolute;
}
</style>
