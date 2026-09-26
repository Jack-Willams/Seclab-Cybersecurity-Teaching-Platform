<script setup lang="ts">
import {computed} from 'vue'
import { useRoute } from 'vue-router'

interface Props {
  icon: any
  title: string
  to: string
  badge?: string | number | undefined
}

const props = defineProps<Props>()
const route = useRoute()

const isActive = computed(() => route.path === props.to)
</script>

<template>
  <router-link 
    :to="to" 
    class="flex items-center gap-3 px-4 py-3 hover:bg-base-200 rounded-lg transition-colors"
    :class="{ 'bg-base-200': isActive }"
  >
    <div class="w-5 h-5 flex-shrink-0">
      <component :is="icon"></component>
    </div>
    <span class="flex-grow">{{ title }}</span>
    <span 
      v-if="badge" 
      class="badge badge-sm"
      :class="{ 'badge-primary': isActive }"
    >
      {{ badge }}
    </span>
  </router-link>
</template> 