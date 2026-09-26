<script setup lang="ts">
import { useRouter } from 'vue-router'
import NavMenuItem from '../../components/NavMenuItem.vue'
import { clearStoredAuthSession } from '../../auth'
import {
  BookOpenIcon,
  ChartBarIcon,
  HomeIcon,
  ShieldCheckIcon,
  UsersIcon,
} from '../../components/icons'

const router = useRouter()

// 管理端同样缺退出入口。先跳转再清 session，避免导航被守卫中止后停在已登出的页面上
const handleLogout = async () => {
  const failure = await router.replace('/')
  if (failure) return
  clearStoredAuthSession()
}

const menuItems = [
  {
    icon: HomeIcon,
    title: '教师首页',
    to: '/admin/dashboard',
  },
  {
    icon: ChartBarIcon,
    title: '班级管理',
    to: '/admin/class-profile',
  },
  {
    icon: UsersIcon,
    title: '学生列表',
    to: '/admin/user',
  },
  {
    icon: ShieldCheckIcon,
    title: 'AI 生成题',
    to: '/admin/generated-questions',
  },
  {
    icon: BookOpenIcon,
    title: '课程管理',
    to: '/admin/course',
  },
  {
    icon: ShieldCheckIcon,
    title: '模块管理',
    to: '/admin/lab',
  },
]
</script>

<template>
  <div class="flex h-full w-64 flex-col border-r border-base-200 bg-base-100 shadow-sm">
    <div class="border-b border-base-200 px-6 py-5">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <i class="fas fa-shield-alt"></i>
        </div>
        <div>
          <div class="text-lg font-bold">SecLab Teacher</div>
          <div class="text-xs text-base-content/60">教学管理端</div>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-4">
      <div class="mb-3 px-4 text-xs font-semibold uppercase text-base-content/50">核心功能</div>
      <nav class="space-y-1">
        <NavMenuItem
          v-for="item in menuItems"
          :key="item.to"
          v-bind="item"
        />
      </nav>
    </div>

    <div class="border-t border-base-200 p-4">
      <div class="rounded-lg bg-base-200/70 px-4 py-3 text-sm text-base-content/70">
        <span class="mr-2 inline-block h-2 w-2 rounded-full bg-success"></span>
        真实数据模式
      </div>

      <button
        class="btn btn-ghost btn-sm mt-2 w-full justify-start gap-3 font-normal text-base-content/70 hover:bg-error/10 hover:text-error"
        type="button"
        title="退出登录"
        @click="handleLogout"
      >
        <i class="fas fa-sign-out-alt"></i>
        <span>退出登录</span>
      </button>
    </div>
  </div>
</template>
