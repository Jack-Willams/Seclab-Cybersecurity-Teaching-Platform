<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import type { LoginForm, RegisterForm } from '../../types/auth'
import {
  clearStoredAuthSession,
  getHomeRouteForRole,
  normalizeCurrentUser,
  storeAuthSession,
} from '../../auth'
import { getUserInfo, login, register } from '../../api'
import { showToast } from '../../common'
import { forgetAccount, rememberAccount } from './savedAccounts'
import SideBrand from './components/SideBrand.vue'
import Login from './components/Login.vue'
import Register from './components/Register.vue'

const router = useRouter()
const isLogin = ref(true)
const isSubmitting = ref(false)

const toggleMode = () => {
  if (isSubmitting.value) return
  isLogin.value = !isLogin.value
}

const handleLogin = async (loginForm: LoginForm) => {
  if (isSubmitting.value) return
  isSubmitting.value = true

  try {
    const resp = await login(loginForm)
    if (!(resp.isSuccess === 1 || resp.status === 200)) {
      showToast(resp.message || '登录失败')
      return
    }

    const token = resp.data?.loginData?.token
    if (!token) {
      throw new Error('登录成功但缺少 token')
    }

    let currentUser =
      normalizeCurrentUser(resp.data?.loginData) ??
      normalizeCurrentUser(resp.data) ??
      normalizeCurrentUser(resp)

    try {
      const profileResponse = await getUserInfo(token)
      if (profileResponse?.data) {
        currentUser = normalizeCurrentUser(profileResponse.data) ?? currentUser
      }
    } catch (profileError) {
      console.warn('Profile fetch after login failed:', profileError)
    }

    if (!currentUser) {
      throw new Error('登录成功但缺少用户信息')
    }

    clearStoredAuthSession()
    storeAuthSession(token, currentUser)

    // 只在这里写账号本：登录真的成功了才记，密码错了不会留下一条错的
    if (loginForm.remember) {
      rememberAccount({
        studentNumber: loginForm.userStudentNumber,
        password: loginForm.userPassword,
        displayName: currentUser.realName || currentUser.username,
        role: currentUser.role,
      })
    } else {
      forgetAccount(loginForm.userStudentNumber)
    }

    showToast('登录成功')
    await router.push(getHomeRouteForRole(currentUser.role))
  } catch (error) {
    console.error('Login failed:', error)
    showToast('登录失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}

const handleRegister = async (registerForm: RegisterForm) => {
  if (isSubmitting.value) return
  isSubmitting.value = true

  try {
    const resp = await register(registerForm)
    if (resp.isSuccess === 1 || resp.status === 200) {
      showToast('注册成功，请登录')
      isLogin.value = true
      return
    }

    showToast(resp.message || '注册失败')
  } catch (error) {
    console.error('Registration failed:', error)
    showToast('注册失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex bg-gradient-to-br from-base-300 via-base-200 to-base-100 relative overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-secondary/10"></div>

    <SideBrand class="animate-slide-in-left" />

    <div class="flex-1 flex items-center justify-center p-4">
      <div class="card w-full max-w-2xl bg-base-100/95 shadow-2xl border border-base-200 backdrop-blur">
        <div class="card-body p-8 md:p-10">
          <div class="flex items-center justify-center gap-3 mb-6">
            <div class="w-14 h-14 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white shadow-lg">
              <i class="fas fa-shield-alt text-xl"></i>
            </div>
            <div class="text-center">
              <h1 class="text-3xl font-bold text-base-content">
                {{ isLogin ? '登录' : '注册账号' }}
              </h1>
              <p class="text-sm text-base-content/60">
                {{ isLogin ? '使用你的 SecLab 账号继续学习。' : '创建 SecLab 账号，进入安全实验平台。' }}
              </p>
            </div>
          </div>

          <Login
            v-if="isLogin"
            :loading="isSubmitting"
            @login="handleLogin"
          />
          <Register
            v-else
            :loading="isSubmitting"
            @register="handleRegister"
          />

          <div class="divider my-8"></div>

          <div class="text-center">
            <button
              class="btn btn-link text-primary"
              :disabled="isSubmitting"
              @click="toggleMode"
            >
              {{ isLogin ? '还没有账号？立即注册' : '已有账号？去登录' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
