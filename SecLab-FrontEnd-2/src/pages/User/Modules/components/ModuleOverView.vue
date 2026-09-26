<script setup lang="ts">
import { useRouter } from 'vue-router';
import type { ModuleOverViewType } from './ModuleOverView';

const props = defineProps<{
  module: ModuleOverViewType;
}>();

const router = useRouter();

function handleStart(moduleId: number) {
  router.push(`/user/module/${moduleId}`);
}
</script>

<template>
  <div class="card h-full bg-base-100 shadow-xl hover:shadow-2xl transition-all duration-300 overflow-hidden">
    <!-- 封面图（固定 16:9 容器比例，彻底解决宽屏下固定高度导致的上下挤压压扁问题） -->
    <div v-if="module.image" class="cover relative aspect-[16/9] overflow-hidden">
      <img
        :src="encodeURI(module.image)"
        :alt="module.name"
        class="w-full h-full object-cover transition-transform duration-500"
      />
      <div class="absolute top-2 right-2 z-10">
        <!-- 「可开始」用明黄 badge-warning，和下面无封面时的行内徽章保持同一套语义。
             （原因见 CourseOverView.vue：badge-ghost 在暗色主题下压在封面上读不出来） -->
        <span
          class="badge"
          :class="{
            'badge-warning': module.status === 'available',
            'badge-error': module.status === 'locked',
            'badge-success': module.status === 'completed'
          }"
        >
          {{ module.status === 'available' ? '可开始' : module.status === 'locked' ? '未解锁' : '已完成' }}
        </span>
      </div>
    </div>

    <!-- 卡片头部。p-4 是对齐课程卡 (CourseOverView) 的内边距 ——
         daisyUI 的 .card-body 默认 padding 2rem，四列布局下卡片会比课程卡明显臃肿 -->
    <div class="card-body p-4">
      <!-- 状态标签（无图时回到原行内徽章，避免重复） -->
      <div class="flex justify-between items-start mb-2">
        <h3 class="card-title text-lg font-semibold">{{ module.name }}</h3>
        <span
          v-if="!module.image"
          class="badge"
          :class="{
            'badge-warning': module.status === 'available',
            'badge-error': module.status === 'locked',
            'badge-success': module.status === 'completed'
          }"
        >
          {{ module.status === 'available' ? '可开始' : module.status === 'locked' ? '未解锁' : '已完成' }}
        </span>
      </div>
      
      <!-- 描述 -->
      <p class="text-sm text-base-content/70 mb-3 line-clamp-3">{{ module.description }}</p>
      
      <!-- 信息行：字号跟课程卡一致（text-xs + text-xs 图标），四列下才排得开 -->
      <div class="grid grid-cols-2 gap-x-2 gap-y-1 mb-3">
        <!-- 类型 -->
        <div class="flex items-center gap-1">
          <i class="fas fa-tag text-primary text-xs"></i>
          <span class="text-xs truncate">{{ module.type }}</span>
        </div>

        <!-- 难度 -->
        <div class="flex items-center gap-1">
          <i class="fas fa-signal text-primary text-xs"></i>
          <span class="text-xs">{{ '★'.repeat(module.difficulty) }}{{ '☆'.repeat(5 - module.difficulty) }}</span>
        </div>

        <!-- 预计用时 -->
        <div class="flex items-center gap-1">
          <i class="fas fa-clock text-primary text-xs"></i>
          <span class="text-xs">{{ module.estimatedTime }}</span>
        </div>

        <!-- 分数 -->
        <div class="flex items-center gap-1">
          <i class="fas fa-scoreboard text-primary text-xs"></i>
          <span class="text-xs font-semibold">{{ module.score }}分</span>
        </div>
      </div>

      <!-- 前置要求 -->
      <div v-if="module.prerequisites && module.prerequisites.length > 0" class="mb-3">
        <div class="text-xs text-base-content/60 mb-1">前置要求：</div>
        <div class="flex flex-wrap gap-1">
          <span 
            v-for="prereq in module.prerequisites" 
            :key="prereq" 
            class="text-xs px-2 py-1 bg-base-200 rounded-full"
          >
            实验 {{ prereq }}
          </span>
        </div>
      </div>
      
      <!-- 操作按钮 -->
      <div class="card-actions justify-end">
        <button 
          class="btn btn-primary btn-sm"
          :disabled="module.status === 'locked'"
          @click="handleStart(module.id)"
        >
          {{ module.status === 'locked' ? '未解锁' : '开始实验' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  transition: all 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
}

/* .cover 的样式统一放在 src/style.css 里（原因见 CourseOverView.vue 的注释） */

/* 卡片内容长短不一（描述 1~3 行、有无前置要求），按钮统一贴底，
   四列并排时底边才是一条直线 */
.card-actions {
  margin-top: auto;
  padding-top: 0.5rem;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
