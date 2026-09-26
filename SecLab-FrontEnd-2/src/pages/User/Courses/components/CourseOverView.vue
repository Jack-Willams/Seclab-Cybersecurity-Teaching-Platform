<script setup lang="ts">
import type { CourseOverViewType } from './CourseOverView';
import { useRouter } from 'vue-router';

const props = defineProps<{
  course: CourseOverViewType;
}>();

const router = useRouter();

const handleViewDetails = () => {
  router.push(`/user/course/${props.course.id}`);
};
</script>

<template>
  <div class="card bg-base-100 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden">
    <!-- 课程图片：固定 16:9，原图完整显示、不压暗不加 scrim（见 style.css 的 ②） -->
    <div class="cover relative aspect-[16/9] overflow-hidden">
      <img
        :src="course.image"
        :alt="course.name"
        class="w-full h-full object-cover transition-transform duration-500"
      />
      <!-- 状态标签：「可开始」用明黄 badge-warning。
           曾经把它改成过半透明描边（想着默认态信息量低、别抢彩色），
           但 badge-ghost 在 night 主题下就是一块近黑底 + 8 成透明度的文字，
           压在深色封面上几乎读不出来，投影更糟。还原成实心明黄。 -->
      <div class="absolute top-2 right-2 z-10">
        <span
          class="badge"
          :class="{
            'badge-warning': course.status === 'available',
            'badge-info': course.status === 'in-progress',
            'badge-success': course.status === 'completed'
          }"
        >
          {{ course.status === 'available' ? '可开始' : course.status === 'in-progress' ? '进行中' : '已完成' }}
        </span>
      </div>
    </div>
    
    <!-- 课程内容 -->
    <div class="card-body p-4">
      <!-- 课程标题 -->
      <h3 class="card-title text-lg font-semibold mb-2 line-clamp-2">{{ course.name }}</h3>
      
      <!-- 课程描述 -->
      <p class="text-sm text-base-content/70 mb-4 line-clamp-3">{{ course.description }}</p>
      
      <!-- 课程信息 -->
      <div class="grid grid-cols-2 gap-2 mb-4">
        <!-- 难度 -->
        <div class="flex items-center gap-1">
          <i class="fas fa-signal text-primary text-xs"></i>
          <span class="text-xs">{{ '★'.repeat(course.difficulty) }}{{ '☆'.repeat(5 - course.difficulty) }}</span>
        </div>
        
        <!-- 预计用时 -->
        <div class="flex items-center gap-1">
          <i class="fas fa-clock text-primary text-xs"></i>
          <span class="text-xs">{{ course.estimatedHours }}小时</span>
        </div>
      </div>
      
      <!-- 标签 -->
      <div class="flex flex-wrap gap-1 mb-4">
        <span 
          v-for="tag in course.tags" 
          :key="tag" 
          class="text-xs px-2 py-1 bg-primary/10 text-primary rounded-full"
        >
          {{ tag }}
        </span>
      </div>
      
      <!-- 操作按钮 -->
      <div class="card-actions justify-end">
        <button class="btn btn-primary btn-sm" @click="handleViewDetails">
          查看详情
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

/* .cover 的样式统一放在 src/style.css 里，别搬回 scoped 块。
   踩过的坑：`:global([data-theme='night']) .cover img` 会被 Vue 的 scoped 编译器
   压成光秃秃的 `[data-theme="night"]`，后半截选择器直接丢掉 ——
   当时那条 filter 就这么加到了 <html> 上，把整页都压暗了。 */

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>