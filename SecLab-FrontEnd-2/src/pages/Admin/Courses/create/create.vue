<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  createTeacherCourse,
  getApiErrorMessage,
  getTeacherCourseDetail,
  updateTeacherCourse,
} from '../../../../api'
import { showToast } from '../../../../common'

const router = useRouter()
const route = useRoute()
const isLoaded = ref(false)
const pageLoading = ref(false)
const pageError = ref('')
const pageNotice = ref('')
const isSubmitting = ref(false)
const editingCourseId = computed(() => Number(route.params.id || 0))
const isEditMode = computed(() => editingCourseId.value > 0)
let loadRequestVersion = 0

type CourseTemplate = {
  name: string
  description: string
  cover: string
  difficulty: number
  category: string
  status: 'draft' | 'published' | 'archived'
  tags: string[]
  prerequisites: string[]
  objectives: string[]
  targetAudience: string
  duration: string
  maxStudents: number
}

const courseTemplates: CourseTemplate[] = [
  {
    name: 'Web安全综合实训',
    description: '围绕 SQL 注入、XSS、CSRF、文件上传和命令执行搭建完整攻防实验链路，适合作为课程主线展示与阶段考核使用。',
    cover: '/default-course-image.png',
    difficulty: 3,
    category: 'Web安全',
    status: 'published',
    tags: ['实战', '入门', '漏洞分析'],
    prerequisites: ['了解 HTTP 协议基础', '掌握基本 Linux 命令', '具备数据库基础操作能力'],
    objectives: ['识别常见 Web 漏洞成因', '完成靶场实验与 Flag 提交', '输出规范化实验报告与修复建议'],
    targetAudience: '网络安全、信息安全相关专业本科生',
    duration: '32课时',
    maxStudents: 120
  },
  {
    name: '内网渗透与域环境攻防',
    description: '覆盖信息收集、权限提升、横向移动、Kerberos 票据攻击与应急溯源，适合作为进阶训练课程。',
    cover: '/default-course-image.png',
    difficulty: 4,
    category: '网络攻防',
    status: 'draft',
    tags: ['进阶', '渗透测试', '竞赛'],
    prerequisites: ['熟悉 Windows 与 Linux 权限模型', '掌握基础抓包和协议分析', '完成 Web 安全入门训练'],
    objectives: ['理解域环境核心认证流程', '掌握常见内网横向移动思路', '能根据事件链输出排障与加固方案'],
    targetAudience: '具备基础攻防能力的高年级学生',
    duration: '40课时',
    maxStudents: 80
  },
  {
    name: 'AI辅助安全分析方法课',
    description: '聚焦如何用 AI 做报错定位、上下文补全、复盘总结和提示工程，提高学习效率与协同表达能力。',
    cover: '/default-course-image.png',
    difficulty: 2,
    category: '系统安全',
    status: 'draft',
    tags: ['工具使用', '实战', '认证'],
    prerequisites: ['完成至少一个靶场模块', '有基本实验报告书写经验'],
    objectives: ['建立高质量 AI 提问习惯', '形成结构化实验复盘模板', '提升问题定位与表达效率'],
    targetAudience: '所有已参与实验课程的学生',
    duration: '16课时',
    maxStudents: 150
  }
]

const buildInitialFormData = (): CourseTemplate => ({
  ...courseTemplates[0],
  tags: [...courseTemplates[0].tags],
  prerequisites: [...courseTemplates[0].prerequisites],
  objectives: [...courseTemplates[0].objectives],
})

// 表单数据
const formData = ref(buildInitialFormData())

// 课程分类选项
const categories = ['Web安全', '系统安全', '密码学', '网络攻防', '移动安全']

// 标签选项
const tagOptions = ['实战', '入门', '进阶', '认证', '竞赛', '工具使用', '漏洞分析', '渗透测试']

// 表单验证
const errors = ref({
  name: '',
  description: '',
  category: '',
  targetAudience: '',
  duration: '',
  maxStudents: ''
})

const applyCourseTemplate = (template: CourseTemplate) => {
  formData.value = {
    ...formData.value,
    ...template,
    tags: [...template.tags],
    prerequisites: [...template.prerequisites],
    objectives: [...template.objectives],
  }
}

// 添加标签
const addTag = (tag: string) => {
  if (!formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag)
  }
}

// 移除标签
const removeTag = (tag: string) => {
  formData.value.tags = formData.value.tags.filter((t) => t !== tag)
}

// 添加学习目标
const addObjective = () => {
  formData.value.objectives.push('')
}

// 移除学习目标
const removeObjective = (index: number) => {
  formData.value.objectives.splice(index, 1)
}

// 添加前置要求
const addPrerequisite = () => {
  formData.value.prerequisites.push('')
}

// 移除前置要求
const removePrerequisite = (index: number) => {
  formData.value.prerequisites.splice(index, 1)
}

// 验证表单
const validateForm = () => {
  errors.value = {
    name: '',
    description: '',
    category: '',
    targetAudience: '',
    duration: '',
    maxStudents: ''
  }

  let isValid = true

  if (!formData.value.name.trim()) {
    errors.value.name = '课程名称不能为空'
    isValid = false
  }

  if (!formData.value.description.trim()) {
    errors.value.description = '课程描述不能为空'
    isValid = false
  }

  if (!formData.value.category) {
    errors.value.category = '请选择课程分类'
    isValid = false
  }

  if (!formData.value.targetAudience.trim()) {
    errors.value.targetAudience = '请填写目标受众'
    isValid = false
  }

  if (!formData.value.duration.trim()) {
    errors.value.duration = '请填写课程时长'
    isValid = false
  }

  if (!formData.value.maxStudents || formData.value.maxStudents < 1) {
    errors.value.maxStudents = '请填写有效的最大学生数'
    isValid = false
  }

  return isValid
}

const loadCourseForEdit = async () => {
  const requestVersion = ++loadRequestVersion
  const courseId = editingCourseId.value
  pageError.value = ''
  pageNotice.value = ''
  formData.value = buildInitialFormData()
  if (!isEditMode.value) {
    pageLoading.value = false
    return
  }

  try {
    pageLoading.value = true
    const course = await getTeacherCourseDetail(courseId)
    if (requestVersion !== loadRequestVersion || courseId !== editingCourseId.value) return
    formData.value = {
      ...formData.value,
      name: course.name,
      description: course.description,
      cover: course.cover || '',
      difficulty: course.difficulty,
      category: course.category,
      status: course.status,
    }
  } catch (error) {
    if (requestVersion !== loadRequestVersion || courseId !== editingCourseId.value) return
    console.error('获取课程详情失败:', error)
    pageError.value = getApiErrorMessage(error, '课程详情加载失败，请重新加载。')
  } finally {
    if (requestVersion === loadRequestVersion && courseId === editingCourseId.value) {
      pageLoading.value = false
    }
  }
}

// 处理表单提交
const handleSubmit = async () => {
  if (!validateForm()) return

  try {
    isSubmitting.value = true
    pageNotice.value = ''
    const payload = {
      name: formData.value.name.trim(),
      description: formData.value.description.trim(),
      cover: formData.value.cover.trim(),
      difficulty: formData.value.difficulty,
      category: formData.value.category,
      tags: formData.value.tags,
      status: formData.value.status as 'draft' | 'published' | 'archived',
    }

    if (isEditMode.value) {
      await updateTeacherCourse(editingCourseId.value, payload)
      showToast('课程更新成功')
    } else {
      await createTeacherCourse(payload)
      showToast('课程创建成功')
    }

    router.push('/admin/course')
  } catch (error) {
    console.error('保存课程失败:', error)
    pageNotice.value = '课程保存失败，请根据接口返回结果修正后重试。'
    showToast('课程保存失败')
  } finally {
    isSubmitting.value = false
  }
}

// 处理取消
const handleCancel = () => {
  const isConfirmed = window.confirm('你确定要取消吗？所有未保存的更改将会丢失。')
  if (isConfirmed) {
    router.back()
  }
}

onMounted(() => {
  setTimeout(() => {
    isLoaded.value = true
  }, 100)

})

watch(editingCourseId, () => void loadCourseForEdit(), { immediate: true })
</script>

<template>
  <div class="container mx-auto p-4 min-h-screen">
    <!-- 页面标题 -->
    <div class="flex justify-between items-center mb-6" :class="{ 'animate-fade-in': isLoaded }">
      <h1 class="text-2xl font-bold flex items-center gap-2">
        <i class="fas fa-book text-primary"></i>
        {{ isEditMode ? '编辑课程' : '创建课程' }}
      </h1>
      <button class="btn btn-ghost" @click="handleCancel">
        <i class="fas fa-arrow-left mr-2"></i>
        返回
      </button>
    </div>

    <div v-if="pageLoading" class="flex justify-center py-8">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>
    <div v-else-if="pageError" class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ pageError }}</span>
      <button class="btn btn-sm" @click="loadCourseForEdit">重新加载</button>
    </div>

    <!-- 创建课程表单 -->
    <div v-else class="card bg-base-100 shadow-xl" :class="{ 'animate-slide-up': isLoaded }">
      <div class="card-body">
        <div v-if="pageNotice" class="alert alert-warning mb-6">
          <span>{{ pageNotice }}</span>
        </div>

        <form @submit.prevent="handleSubmit" class="space-y-6">
          <div class="rounded-2xl border border-primary/15 bg-primary/5 p-4">
            <div class="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div class="text-sm font-semibold text-primary">快速套用静态课程模板</div>
                <div class="text-xs text-base-content/60 mt-1">先把课程展示内容铺满，后续再平滑替换成真实编辑链路。</div>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  v-for="template in courseTemplates"
                  :key="template.name"
                  type="button"
                  class="btn btn-sm btn-outline btn-primary"
                  @click="applyCourseTemplate(template)"
                >
                  {{ template.name }}
                </button>
              </div>
            </div>
          </div>

          <!-- 基本信息部分 -->
          <div class="divider text-lg font-semibold">基本信息</div>

          <!-- 课程名称 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程名称</span>
            </label>
            <input type="text" class="input input-bordered" v-model="formData.name" :class="{ 'input-error': errors.name }" placeholder="请输入课程名称" />
            <label class="label" v-if="errors.name">
              <span class="label-text-alt text-error">{{ errors.name }}</span>
            </label>
          </div>

          <!-- 课程描述 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程描述</span>
            </label>
            <textarea class="textarea textarea-bordered h-32" v-model="formData.description" :class="{ 'textarea-error': errors.description }" placeholder="请输入课程描述"></textarea>
            <label class="label" v-if="errors.description">
              <span class="label-text-alt text-error">{{ errors.description }}</span>
            </label>
          </div>

          <!-- 课程封面 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程封面</span>
            </label>
            <div class="flex items-center gap-4">
              <div class="w-48 h-32 border-2 border-dashed rounded-lg flex items-center justify-center hover:border-primary transition-colors cursor-pointer">
                <i class="fas fa-image text-4xl text-base-content/30"></i>
              </div>
              <button type="button" class="btn btn-outline">
                <i class="fas fa-upload mr-2"></i>
                上传封面
              </button>
            </div>
          </div>

          <!-- 课程分类 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程分类</span>
            </label>
            <select class="select select-bordered" v-model="formData.category" :class="{ 'select-error': errors.category }">
              <option value="">请选择分类</option>
              <option v-for="category in categories" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <label class="label" v-if="errors.category">
              <span class="label-text-alt text-error">{{ errors.category }}</span>
            </label>
          </div>

          <!-- 课程难度 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程难度</span>
            </label>
            <div class="flex items-center gap-2">
              <div class="rating rating-md">
                <input v-for="n in 5" :key="n" type="radio" name="rating-8" class="mask mask-star-2 bg-yellow-400" :checked="formData.difficulty === n" @change="formData.difficulty = n" />
              </div>
              <span class="text-sm text-base-content/70">{{ formData.difficulty }} 星</span>
            </div>
          </div>

          <!-- 课程标签 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程标签</span>
            </label>
            <div class="flex flex-wrap gap-2">
              <button v-for="tag in tagOptions" :key="tag" type="button" class="btn btn-sm" :class="formData.tags.includes(tag) ? 'btn-primary' : 'btn-ghost'" @click="formData.tags.includes(tag) ? removeTag(tag) : addTag(tag)">
                {{ tag }}
              </button>
            </div>
          </div>

          <!-- 课程状态 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程状态</span>
            </label>
            <select class="select select-bordered" v-model="formData.status">
              <option value="draft">草稿</option>
              <option value="published">发布</option>
              <option value="archived">归档</option>
            </select>
          </div>

          <!-- 课程设置部分 -->
          <div class="divider text-lg font-semibold">课程设置</div>

          <!-- 目标受众 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">目标受众</span>
            </label>
            <input type="text" class="input input-bordered" v-model="formData.targetAudience" :class="{ 'input-error': errors.targetAudience }" placeholder="例如：安全工程师、在校学生等" />
            <label class="label" v-if="errors.targetAudience">
              <span class="label-text-alt text-error">{{ errors.targetAudience }}</span>
            </label>
          </div>

          <!-- 课程时长 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">课程时长</span>
            </label>
            <input type="text" class="input input-bordered" v-model="formData.duration" :class="{ 'input-error': errors.duration }" placeholder="例如：40课时" />
            <label class="label" v-if="errors.duration">
              <span class="label-text-alt text-error">{{ errors.duration }}</span>
            </label>
          </div>

          <!-- 最大学生数 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">最大学生数</span>
            </label>
            <input type="number" class="input input-bordered" v-model="formData.maxStudents" :class="{ 'input-error': errors.maxStudents }" min="1" />
            <label class="label" v-if="errors.maxStudents">
              <span class="label-text-alt text-error">{{ errors.maxStudents }}</span>
            </label>
          </div>

          <!-- 学习目标 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">学习目标</span>
            </label>
            <div class="space-y-2">
              <div v-for="(objective, index) in formData.objectives" :key="index" class="flex gap-2">
                <input type="text" class="input input-bordered flex-1" v-model="formData.objectives[index]" placeholder="请输入学习目标" />
                <button type="button" class="btn btn-square btn-ghost text-error" @click="removeObjective(index)">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
              <button type="button" class="btn btn-ghost btn-sm gap-2" @click="addObjective">
                <i class="fas fa-plus"></i>
                添加学习目标
              </button>
            </div>
          </div>

          <!-- 前置要求 -->
          <div class="form-control">
            <label class="label">
              <span class="label-text">前置要求</span>
            </label>
            <div class="space-y-2">
              <div v-for="(prerequisite, index) in formData.prerequisites" :key="index" class="flex gap-2">
                <input type="text" class="input input-bordered flex-1" v-model="formData.prerequisites[index]" placeholder="请输入前置要求" />
                <button type="button" class="btn btn-square btn-ghost text-error" @click="removePrerequisite(index)">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
              <button type="button" class="btn btn-ghost btn-sm gap-2" @click="addPrerequisite">
                <i class="fas fa-plus"></i>
                添加前置要求
              </button>
            </div>
          </div>

          <!-- 提交按钮 -->
          <div class="flex justify-end gap-4 mt-8">
            <button type="button" class="btn btn-ghost" @click="handleCancel">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
              <i class="fas fa-save mr-2"></i>
              {{ isSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  max-width: 1400px;
  height: 100%;
  overflow-y: auto;
}

.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 表单样式优化 */
.form-control {
  transition: all 0.3s ease;
}

.form-control:hover {
  transform: translateX(4px);
}

/* 标签按钮样式 */
.btn-sm {
  transition: all 0.3s ease;
}

.btn-sm:hover {
  transform: translateY(-2px);
}

/* 输入框焦点效果 */
.input:focus,
.textarea:focus,
.select:focus {
  box-shadow: 0 0 0 2px oklch(var(--p) / 0.2);
}

/* 分割线样式 */
.divider {
  position: relative;
  margin: 2rem 0;
  padding: 0 1rem;
}

.divider::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, oklch(var(--p) / 0.2), transparent);
}

.divider::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  padding: 0 1rem;
  background: oklch(var(--b1));
}
</style>
