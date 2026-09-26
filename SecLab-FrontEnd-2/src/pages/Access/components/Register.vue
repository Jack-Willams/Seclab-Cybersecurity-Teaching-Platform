<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { getApiErrorMessage, getRegisterClassOptions, isImageServiceUnreachable, uploadImageFile } from '../../../api'
import type { RegisterClassOption } from '../../../api'
import type { RegisterForm } from '../../../types/auth'

defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'register', form: RegisterForm): void
}>()

// 学院是院系建制，与教师排课无关，保持静态；班级则完全由教师端的教学班决定。
const academyOptions = [
  '网络空间安全学院',
  '计算机科学与技术学院',
  '软件工程学院',
  '人工智能学院',
]

const registerForm = ref<RegisterForm>({
  userStudentNumber: '',
  userPassword: '',
  userName: '',
  userEmail: '',
  userTel: '',
  userGender: 1,
  userAcademy: academyOptions[0],
  userClass: '',
  userImage: '',
})

const confirmPassword = ref('')
const avatarFile = ref<File | null>(null)
const avatarPreview = ref('')
const avatarError = ref('')
const isUploadingAvatar = ref(false)

const classOptions = ref<RegisterClassOption[]>([])
const classOptionsLoading = ref(false)
const classOptionsError = ref('')

const errors = reactive({
  userStudentNumber: '',
  userPassword: '',
  confirmPassword: '',
  userName: '',
  userEmail: '',
  userTel: '',
  userClass: '',
})

const hasClassOptions = computed(() => classOptions.value.length > 0)
const classSelectDisabled = computed(() => classOptionsLoading.value || !hasClassOptions.value)
const classPlaceholder = computed(() => {
  if (classOptionsLoading.value) return '正在加载可选班级…'
  if (classOptionsError.value) return '班级加载失败'
  if (!hasClassOptions.value) return '暂无可选班级'
  return '请选择班级'
})
const classLabel = (option: RegisterClassOption) =>
  `${option.className}（${option.academicYear}学年 第${option.semester}学期）`

const loadClassOptions = async () => {
  classOptionsLoading.value = true
  classOptionsError.value = ''
  try {
    classOptions.value = await getRegisterClassOptions()
    // 教师归档了原来的班级时，把已选但不再可选的值清掉，避免提交被后端拒绝
    if (!classOptions.value.some((item) => item.className === registerForm.value.userClass)) {
      registerForm.value.userClass = ''
    }
  } catch (error) {
    classOptions.value = []
    classOptionsError.value = getApiErrorMessage(error, '可选班级加载失败，请稍后重试。')
    console.error('可选班级加载失败:', error)
  } finally {
    classOptionsLoading.value = false
  }
}

onMounted(loadClassOptions)

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const handleAvatarChange = (event: Event) => {
  avatarError.value = ''
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] || null

  if (!file) {
    avatarFile.value = null
    avatarPreview.value = ''
    registerForm.value.userImage = ''
    return
  }

  if (!file.type.startsWith('image/')) {
    avatarError.value = '请选择图片文件。'
    input.value = ''
    return
  }

  if (file.size > 2 * 1024 * 1024) {
    avatarError.value = '头像图片不能超过 2MB。'
    input.value = ''
    return
  }

  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
  registerForm.value.userImage = ''
}

const clearAvatar = () => {
  avatarFile.value = null
  avatarPreview.value = ''
  avatarError.value = ''
  registerForm.value.userImage = ''
}

const handleSubmit = async () => {
  errors.userStudentNumber = ''
  errors.userPassword = ''
  errors.confirmPassword = ''
  errors.userName = ''
  errors.userEmail = ''
  errors.userTel = ''
  errors.userClass = ''

  const studentNumber = registerForm.value.userStudentNumber.trim()
  const userName = registerForm.value.userName.trim()
  const userEmail = registerForm.value.userEmail.trim()
  const userTel = registerForm.value.userTel?.trim() || ''

  if (!userName) {
    errors.userName = '请输入姓名。'
  }
  if (!studentNumber) {
    errors.userStudentNumber = '请输入学号。'
  } else if (studentNumber.length > 13) {
    errors.userStudentNumber = '学号不能超过 13 个字符。'
  }
  if (!userEmail) {
    errors.userEmail = '请输入邮箱。'
  } else if (!emailPattern.test(userEmail)) {
    errors.userEmail = '请输入有效的邮箱地址。'
  }
  if (userTel && (!/^\d+$/.test(userTel) || userTel.length > 11)) {
    errors.userTel = '手机号需为不超过 11 位的数字。'
  }
  if (!registerForm.value.userPassword) {
    errors.userPassword = '请输入密码。'
  } else if (registerForm.value.userPassword.length < 6) {
    errors.userPassword = '密码至少需要 6 个字符。'
  }
  if (confirmPassword.value !== registerForm.value.userPassword) {
    errors.confirmPassword = '两次输入的密码不一致。'
  }
  if (!registerForm.value.userClass) {
    errors.userClass = hasClassOptions.value
      ? '请选择班级。'
      : '当前没有可选班级，请先联系任课教师创建教学班。'
  }

  if (Object.values(errors).some(Boolean)) {
    return
  }

  if (avatarFile.value) {
    try {
      isUploadingAvatar.value = true
      const uploadResult = await uploadImageFile(avatarFile.value)
      // 只存文件名，显示时由 avatarUrl() 按当前图片服务地址拼完整 URL
      const uploadedName = uploadResult.filename || uploadResult.url || ''
      if (!uploadedName) {
        avatarError.value = '头像上传失败，您可以注册后在个人资料页补传。'
      } else {
        registerForm.value.userImage = uploadedName
      }
    } catch (error) {
      console.error('头像上传失败:', error)
      // 之前这里只说"上传失败"，图片服务没启动时看不出是环境问题，白白排查半天
      avatarError.value = isImageServiceUnreachable(error)
        ? '图片服务（8086）没有启动，头像暂时传不了。可以先注册，之后在个人资料页补传。'
        : getApiErrorMessage(error, '头像上传失败，您可以注册后在个人资料页补传。')
    } finally {
      isUploadingAvatar.value = false
    }
  }

  emit('register', {
    ...registerForm.value,
    userStudentNumber: studentNumber,
    userName,
    userEmail,
    userTel,
  })
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <div class="form-control">
      <label class="label">
        <span class="label-text font-medium">头像</span>
        <span class="label-text-alt text-base-content/50">可选</span>
      </label>
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 rounded-full border border-base-300 bg-base-200 flex items-center justify-center overflow-hidden">
          <img
            v-if="avatarPreview"
            :src="avatarPreview"
            alt="头像预览"
            class="w-full h-full object-cover"
          />
          <i v-else class="fas fa-user text-2xl text-base-content/30"></i>
        </div>
        <div class="flex-1">
          <input
            type="file"
            accept="image/*"
            class="file-input file-input-bordered file-input-sm w-full"
            @change="handleAvatarChange"
          />
          <div class="mt-2 flex items-center gap-2">
            <button
              v-if="avatarPreview"
              type="button"
              class="btn btn-xs btn-ghost"
              @click="clearAvatar"
            >
              清除头像
            </button>
            <span class="text-xs text-base-content/50">未上传时头像保持空白</span>
          </div>
        </div>
      </div>
      <label v-if="avatarError" class="label">
        <span class="label-text-alt text-error">{{ avatarError }}</span>
      </label>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">姓名</span>
        </label>
        <input
          v-model="registerForm.userName"
          type="text"
          placeholder="请输入姓名"
          class="input input-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.userName }"
        />
        <label v-if="errors.userName" class="label">
          <span class="label-text-alt text-error">{{ errors.userName }}</span>
        </label>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">学号</span>
        </label>
        <input
          v-model="registerForm.userStudentNumber"
          type="text"
          maxlength="13"
          placeholder="请输入学号"
          class="input input-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.userStudentNumber }"
        />
        <label v-if="errors.userStudentNumber" class="label">
          <span class="label-text-alt text-error">{{ errors.userStudentNumber }}</span>
        </label>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">邮箱</span>
        </label>
        <input
          v-model="registerForm.userEmail"
          type="email"
          placeholder="请输入邮箱"
          class="input input-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.userEmail }"
        />
        <label v-if="errors.userEmail" class="label">
          <span class="label-text-alt text-error">{{ errors.userEmail }}</span>
        </label>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">手机号</span>
        </label>
        <input
          v-model="registerForm.userTel"
          type="tel"
          maxlength="11"
          placeholder="可选，请输入手机号"
          class="input input-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.userTel }"
        />
        <label v-if="errors.userTel" class="label">
          <span class="label-text-alt text-error">{{ errors.userTel }}</span>
        </label>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">学院</span>
        </label>
        <select
          v-model="registerForm.userAcademy"
          class="select select-bordered bg-base-200/60 focus:bg-base-100"
        >
          <option
            v-for="academy in academyOptions"
            :key="academy"
            :value="academy"
          >
            {{ academy }}
          </option>
        </select>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">班级</span>
          <span class="label-text-alt text-base-content/50">来自教师已创建的教学班</span>
        </label>
        <select
          v-model="registerForm.userClass"
          class="select select-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'select-error': errors.userClass }"
          :disabled="classSelectDisabled"
        >
          <option value="" disabled>{{ classPlaceholder }}</option>
          <option
            v-for="option in classOptions"
            :key="option.teachingClassId"
            :value="option.className"
          >
            {{ classLabel(option) }}
          </option>
        </select>
        <label v-if="errors.userClass" class="label">
          <span class="label-text-alt text-error">{{ errors.userClass }}</span>
        </label>
        <label v-else-if="classOptionsError" class="label">
          <span class="label-text-alt text-error">
            {{ classOptionsError }}
            <button type="button" class="link link-primary ml-1" @click="loadClassOptions">重试</button>
          </span>
        </label>
        <label v-else-if="!classOptionsLoading && !hasClassOptions" class="label">
          <span class="label-text-alt text-warning">教师端还没有创建教学班，暂时无法注册。</span>
        </label>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">性别</span>
        </label>
        <select
          v-model="registerForm.userGender"
          class="select select-bordered bg-base-200/60 focus:bg-base-100"
        >
          <option :value="1">男</option>
          <option :value="0">女</option>
          <option :value="2">暂不填写</option>
        </select>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">密码</span>
        </label>
        <input
          v-model="registerForm.userPassword"
          type="password"
          placeholder="至少 6 个字符"
          class="input input-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.userPassword }"
        />
        <label v-if="errors.userPassword" class="label">
          <span class="label-text-alt text-error">{{ errors.userPassword }}</span>
        </label>
      </div>

      <div class="form-control">
        <label class="label">
          <span class="label-text font-medium">确认密码</span>
        </label>
        <input
          v-model="confirmPassword"
          type="password"
          placeholder="请再次输入密码"
          class="input input-bordered bg-base-200/60 focus:bg-base-100"
          :class="{ 'input-error': errors.confirmPassword }"
        />
        <label v-if="errors.confirmPassword" class="label">
          <span class="label-text-alt text-error">{{ errors.confirmPassword }}</span>
        </label>
      </div>
    </div>

    <button
      type="submit"
      class="btn btn-primary w-full"
      :disabled="loading || isUploadingAvatar || classSelectDisabled"
    >
      <span v-if="loading || isUploadingAvatar" class="loading loading-spinner loading-sm"></span>
      <i v-else class="fas fa-user-plus mr-2"></i>
      {{ isUploadingAvatar ? '上传头像中...' : loading ? '注册中...' : '注册' }}
    </button>
  </form>
</template>
