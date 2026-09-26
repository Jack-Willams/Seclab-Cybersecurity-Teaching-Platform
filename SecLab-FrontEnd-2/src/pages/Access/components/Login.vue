<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import type { LoginForm } from '../../../types/auth'
import { clearSavedAccounts, forgetAccount, loadSavedAccounts, type SavedAccount } from '../savedAccounts'

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'login', form: LoginForm): void
}>()

const loginForm = ref<LoginForm>({
  userStudentNumber: '',
  userPassword: '',
  // 演示场景默认记住，省得每次还要先勾一下
  remember: true,
})

const errors = reactive({
  userStudentNumber: '',
  userPassword: '',
})

const savedAccounts = ref<SavedAccount[]>([])
const pickerOpen = ref(false)
const pickerRef = ref<HTMLElement | null>(null)

const hasSavedAccounts = computed(() => savedAccounts.value.length > 0)

const roleLabel = (role: SavedAccount['role']) => {
  if (role === 'admin') return '管理员'
  if (role === 'teacher') return '教师'
  if (role === 'student') return '学生'
  return ''
}

const accountSubtitle = (account: SavedAccount) =>
  [account.displayName, roleLabel(account.role)].filter(Boolean).join(' · ')

const applyAccount = (account: SavedAccount) => {
  loginForm.value.userStudentNumber = account.studentNumber
  loginForm.value.userPassword = account.password
  errors.userStudentNumber = ''
  errors.userPassword = ''
  pickerOpen.value = false
}

const removeAccount = (studentNumber: string) => {
  forgetAccount(studentNumber)
  savedAccounts.value = loadSavedAccounts()
  if (!hasSavedAccounts.value) {
    pickerOpen.value = false
  }
}

const clearAll = () => {
  clearSavedAccounts()
  savedAccounts.value = []
  pickerOpen.value = false
}

const handleClickOutside = (event: MouseEvent) => {
  if (!pickerOpen.value) return
  if (pickerRef.value && !pickerRef.value.contains(event.target as Node)) {
    pickerOpen.value = false
  }
}

onMounted(() => {
  savedAccounts.value = loadSavedAccounts()
  // 最近用过的那个直接填好，答辩时点「登录」就能进
  const [latest] = savedAccounts.value
  if (latest) {
    loginForm.value.userStudentNumber = latest.studentNumber
    loginForm.value.userPassword = latest.password
  }
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

const handleSubmit = () => {
  errors.userStudentNumber = ''
  errors.userPassword = ''

  if (!loginForm.value.userStudentNumber.trim()) {
    errors.userStudentNumber = '请输入学号。'
  }
  if (!loginForm.value.userPassword) {
    errors.userPassword = '请输入密码。'
  }

  if (errors.userStudentNumber || errors.userPassword) {
    return
  }

  emit('login', {
    ...loginForm.value,
    userStudentNumber: loginForm.value.userStudentNumber.trim(),
  })
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <div class="form-control">
      <label class="label">
        <span class="label-text font-medium">学号</span>
        <button
          v-if="hasSavedAccounts"
          type="button"
          class="label-text-alt btn btn-ghost btn-xs gap-1 text-primary"
          :aria-expanded="pickerOpen"
          @click.stop="pickerOpen = !pickerOpen"
        >
          <i class="fas fa-address-book"></i>
          已存 {{ savedAccounts.length }} 个
          <i :class="['fas', 'text-[10px]', pickerOpen ? 'fa-caret-up' : 'fa-caret-down']"></i>
        </button>
      </label>

      <div ref="pickerRef" class="relative">
        <input
          v-model="loginForm.userStudentNumber"
          type="text"
          maxlength="13"
          placeholder="请输入学号"
          autocomplete="off"
          class="input input-bordered w-full bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.userStudentNumber }"
          @focus="pickerOpen = hasSavedAccounts"
        />

        <ul
          v-if="pickerOpen && hasSavedAccounts"
          class="absolute left-0 right-0 top-full z-30 mt-1 max-h-64 overflow-y-auto rounded-box border border-base-200 bg-base-100 p-1 shadow-xl"
        >
          <li v-for="account in savedAccounts" :key="account.studentNumber">
            <div
              class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-base-200"
              @click="applyAccount(account)"
            >
              <i class="fas fa-user-circle text-lg text-base-content/40"></i>
              <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium">{{ account.studentNumber }}</div>
                <div v-if="accountSubtitle(account)" class="truncate text-xs text-base-content/60">
                  {{ accountSubtitle(account) }}
                </div>
              </div>
              <span v-if="account.preset" class="badge badge-ghost badge-sm shrink-0">预置</span>
              <button
                type="button"
                class="btn btn-ghost btn-xs shrink-0 text-base-content/40 hover:text-error"
                :title="`忘记 ${account.studentNumber}`"
                :aria-label="`忘记 ${account.studentNumber}`"
                @click.stop="removeAccount(account.studentNumber)"
              >
                <i class="fas fa-times"></i>
              </button>
            </div>
          </li>

          <li class="border-t border-base-200 mt-1 pt-1">
            <button
              type="button"
              class="btn btn-ghost btn-xs w-full justify-start text-base-content/50 hover:text-error"
              @click="clearAll"
            >
              <i class="fas fa-trash-can mr-1"></i>
              清空全部记住的账号
            </button>
          </li>
        </ul>
      </div>

      <label v-if="errors.userStudentNumber" class="label">
        <span class="label-text-alt text-error">{{ errors.userStudentNumber }}</span>
      </label>
    </div>

    <div class="form-control">
      <label class="label">
        <span class="label-text font-medium">密码</span>
      </label>
      <input
        v-model="loginForm.userPassword"
        type="password"
        placeholder="请输入密码"
        class="input input-bordered bg-base-200/60 focus:bg-base-100"
        :class="{ 'input-error': errors.userPassword }"
      />
      <label v-if="errors.userPassword" class="label">
        <span class="label-text-alt text-error">{{ errors.userPassword }}</span>
      </label>
    </div>

    <label class="label cursor-pointer justify-start gap-3">
      <input
        v-model="loginForm.remember"
        type="checkbox"
        class="checkbox checkbox-primary checkbox-sm"
      />
      <span class="label-text">在此设备上记住这个账号</span>
    </label>

    <button
      type="submit"
      class="btn btn-primary w-full"
      :disabled="loading"
    >
      <span v-if="loading" class="loading loading-spinner loading-sm"></span>
      <i v-else class="fas fa-sign-in-alt mr-2"></i>
      {{ loading ? '登录中...' : '登录' }}
    </button>
  </form>
</template>
