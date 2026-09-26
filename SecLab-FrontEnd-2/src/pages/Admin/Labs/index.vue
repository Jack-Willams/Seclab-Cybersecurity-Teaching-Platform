<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Experiment } from '../../../types/experiment'
import {
  createTeacherLab,
  deleteTeacherLab,
  getApiErrorMessage,
  getTeacherLabList,
  updateTeacherLab,
} from '../../../api'
import { showToast } from '../../../common'

const experiments = ref<Experiment[]>([])

// 搜索和筛选条件
const filters = ref({
  search: '',
  difficulty: '',
  status: '',
  courseId: ''
})

// 获取难度星级显示
const getDifficultyStars = (difficulty: number) => '★'.repeat(difficulty) + '☆'.repeat(5 - difficulty)

// 获取状态标签样式
const getStatusBadgeClass = (status: Experiment['status']) => ({
  'badge-success': status === 'published',
  'badge-warning': status === 'draft',
  'badge-error': status === 'archived'
})

// 获取状态文本
const getStatusText = (status: Experiment['status']) => ({
  published: '已发布',
  draft: '草稿',
  archived: '已归档'
}[status])

// 过滤后的实验列表
const filteredExperiments = computed(() => {
  return experiments.value.filter(exp => {
    if (filters.value.search && 
        !exp.name.toLowerCase().includes(filters.value.search.toLowerCase())) {
      return false
    }
    if (filters.value.difficulty && exp.difficulty !== parseInt(filters.value.difficulty)) {
      return false
    }
    if (filters.value.status && exp.status !== filters.value.status) {
      return false
    }
    return true
  })
})

const labSummaryStats = computed(() => {
  const publishedCount = experiments.value.filter((experiment) => experiment.status === 'published').length
  const totalStudents = experiments.value.reduce((sum, experiment) => sum + Number(experiment.studentCount || 0), 0)
  const averageCompletion = experiments.value.length
    ? Math.round(
        experiments.value.reduce((sum, experiment) => sum + Number(experiment.completionRate || 0), 0) / experiments.value.length
      )
    : 0

  return [
    { label: '实验总数', value: experiments.value.length, desc: '可用于课堂与靶场展示', icon: 'fa-flask', tone: 'text-primary' },
    { label: '已发布实验', value: publishedCount, desc: '当前可直接进入训练流程', icon: 'fa-rocket', tone: 'text-success' },
    { label: '累计参训人次', value: totalStudents, desc: '按实验维度统计的学生参与总量', icon: 'fa-users', tone: 'text-info' },
    { label: '平均完成率', value: `${averageCompletion}%`, desc: '课堂整体推进情况', icon: 'fa-chart-simple', tone: 'text-secondary' },
  ]
})

const pageLoading = ref(false)
const pageError = ref<string | null>(null)
const pageNotice = ref<string | null>(null)

const hasExperiments = computed(() => experiments.value.length > 0)
const isEmpty = computed(() => !pageLoading.value && !hasExperiments.value)
const hasNoFilteredExperiments = computed(() => !pageLoading.value && hasExperiments.value && filteredExperiments.value.length === 0)
const showEditorModal = ref(false)
const showTaskPointModal = ref(false)
const showEnvironmentModal = ref(false)
const isSubmitting = ref(false)
const editingExperimentId = ref<number | null>(null)
const editorError = ref('')
const activeExperiment = ref<Experiment | null>(null)
const experimentForm = ref({
  name: '',
  description: '',
  difficulty: 3,
  type: '',
})

const fetchExperiments = async () => {
  try {
    pageLoading.value = true
    pageError.value = null
    pageNotice.value = null

    experiments.value = await getTeacherLabList()
  } catch (error) {
    console.error('获取教师端实验列表失败:', error)
    experiments.value = []
    pageError.value = getApiErrorMessage(error, '实验数据加载失败，请重新加载。')
  } finally {
    pageLoading.value = false
  }
}

onMounted(() => {
  void fetchExperiments()
})

// 处理实验操作
const resetExperimentForm = () => {
  experimentForm.value = {
    name: '',
    description: '',
    difficulty: 3,
    type: '',
  }
  editingExperimentId.value = null
  editorError.value = ''
}

const openCreateModal = () => {
  resetExperimentForm()
  showEditorModal.value = true
}

const handleEdit = (experiment: Experiment) => {
  experimentForm.value = {
    name: experiment.name,
    description: experiment.description,
    difficulty: experiment.difficulty,
    type: experiment.courseName || '',
  }
  editingExperimentId.value = experiment.id
  editorError.value = ''
  showEditorModal.value = true
}

const handleDelete = async (experiment: Experiment) => {
  const confirmed = window.confirm(`确定要删除实验“${experiment.name}”吗？`)
  if (!confirmed) {
    return
  }

  try {
    await deleteTeacherLab(experiment.id)
    showToast('实验删除成功')
    await fetchExperiments()
  } catch (error) {
    console.error('删除实验失败:', error)
    showToast('实验删除失败，请稍后重试')
  }
}

const handleTaskPoints = (experiment: Experiment) => {
  activeExperiment.value = experiment
  showTaskPointModal.value = true
}

const handleEnvironment = (experiment: Experiment) => {
  activeExperiment.value = experiment
  showEnvironmentModal.value = true
}

const submitExperimentForm = async () => {
  if (!experimentForm.value.name.trim()) {
    editorError.value = '实验名称不能为空'
    return
  }

  if (!experimentForm.value.description.trim()) {
    editorError.value = '实验描述不能为空'
    return
  }

  try {
    isSubmitting.value = true
    editorError.value = ''

    const payload = {
      name: experimentForm.value.name.trim(),
      description: experimentForm.value.description.trim(),
      difficulty: experimentForm.value.difficulty,
      type: experimentForm.value.type.trim(),
    }

    if (editingExperimentId.value) {
      await updateTeacherLab(editingExperimentId.value, payload)
      showToast('实验更新成功')
    } else {
      await createTeacherLab(payload)
      showToast('实验创建成功')
    }

    showEditorModal.value = false
    await fetchExperiments()
  } catch (error) {
    console.error('保存实验失败:', error)
    showToast(editingExperimentId.value ? '实验更新失败，请稍后重试' : '实验创建失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="container-fluid px-4 py-6 overflow-x-hidden">
    <!-- 页面标题 -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">实验管理</h1>
      <button class="btn btn-primary" @click="openCreateModal">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        创建实验
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
      <div v-for="item in labSummaryStats" :key="item.label" class="card bg-base-100 shadow-lg">
        <div class="card-body">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="text-sm text-base-content/60">{{ item.label }}</div>
              <div class="mt-2 text-3xl font-bold" :class="item.tone">{{ item.value }}</div>
              <div class="mt-1 text-xs text-base-content/50">{{ item.desc }}</div>
            </div>
            <i :class="['fas', item.icon, item.tone, 'text-2xl']"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <div class="card bg-base-100 shadow-xl mb-6">
      <div class="card-body">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="form-control">
            <label class="label">
              <span class="label-text">搜索</span>
            </label>
            <input 
              type="text" 
              class="input input-bordered" 
              placeholder="搜索实验名称"
              v-model="filters.search"
            >
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">难度</span>
            </label>
            <select class="select select-bordered" v-model="filters.difficulty">
              <option value="">全部</option>
              <option v-for="n in 5" :key="n" :value="n">{{ n }} 星</option>
            </select>
          </div>

          <div class="form-control">
            <label class="label">
              <span class="label-text">状态</span>
            </label>
            <select class="select select-bordered" v-model="filters.status">
              <option value="">全部</option>
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="archived">已归档</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pageLoading" class="flex justify-center py-8">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>
    <div v-else-if="pageError" class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
      <span>{{ pageError }}</span>
      <button class="btn btn-sm" @click="fetchExperiments">重新加载</button>
    </div>
    <div v-else-if="pageNotice" class="alert alert-warning mb-6">
      <span>{{ pageNotice }}</span>
    </div>
    <!-- 实验列表 -->
    <div v-if="isEmpty" class="card bg-base-100 shadow-xl">
      <div class="card-body text-center py-10 text-base-content/60">
        暂无可展示的实验数据
      </div>
    </div>
    <div v-else-if="hasNoFilteredExperiments" class="card bg-base-100 shadow-xl">
      <div class="card-body text-center py-10 text-base-content/60">
        当前筛选条件下没有匹配的实验
      </div>
    </div>
    <div v-else class="grid grid-cols-1 gap-4">
      <div v-for="experiment in filteredExperiments" :key="experiment.id" 
           class="card bg-base-100 shadow-xl compact-card">
        <div class="card-body p-4">
          <!-- 实验标题和状态 -->
          <div class="flex justify-between items-start">
            <div>
              <h2 class="card-title text-base">
                {{ experiment.name }}
                <div class="badge" :class="getStatusBadgeClass(experiment.status)">
                  {{ getStatusText(experiment.status) }}
                </div>
              </h2>
              <div class="text-xs text-base-content/60">
                所属课程: {{ experiment.courseName }}
              </div>
            </div>
            <div class="text-yellow-500 text-sm">
              难度: {{ getDifficultyStars(experiment.difficulty) }}
            </div>
          </div>

          <!-- 实验描述 -->
          <p class="text-sm text-base-content/70 my-1">{{ experiment.description }}</p>

          <!-- 任务点列表 -->
          <div class="mt-2">
            <details class="cursor-pointer">
              <summary class="font-semibold text-sm mb-1">任务点</summary>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                <div v-for="task in experiment.taskPoints" :key="task.id" 
                    class="card bg-base-200">
                  <div class="card-body p-2">
                    <div class="flex justify-between items-center">
                      <h4 class="font-medium text-sm">{{ task.name }}</h4>
                      <span class="badge badge-primary text-xs">{{ task.score }}分</span>
                    </div>
                    <p class="text-xs text-base-content/70">{{ task.description }}</p>
                  </div>
                </div>
              </div>
            </details>
          </div>

          <!-- 环境配置 -->
          <div class="mt-2">
            <details class="cursor-pointer">
              <summary class="font-semibold text-sm mb-1">实验环境</summary>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                <div v-if="experiment.environment.targetMachine" class="card bg-base-200">
                  <div class="card-body p-2">
                    <h4 class="font-medium text-sm">靶机环境</h4>
                    <div class="text-xs">
                      <div>镜像: {{ experiment.environment.targetMachine.image }}</div>
                      <div>端口: {{ experiment.environment.targetMachine.port }}</div>
                      <div>内存: {{ experiment.environment.targetMachine.memory }}</div>
                    </div>
                  </div>
                </div>
                <div v-if="experiment.environment.operationMachine" class="card bg-base-200">
                  <div class="card-body p-2">
                    <h4 class="font-medium text-sm">操作环境</h4>
                    <div class="text-xs">
                      <div>镜像: {{ experiment.environment.operationMachine.image }}</div>
                      <div>端口: {{ experiment.environment.operationMachine.port }}</div>
                      <div>内存: {{ experiment.environment.operationMachine.memory }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </details>
          </div>

          <!-- 统计信息 -->
          <div class="flex gap-4 mt-2 text-xs text-base-content/60">
            <div class="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <span>{{ experiment.studentCount }} 名学生</span>
            </div>
            <div class="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span>完成率 {{ experiment.completionRate }}%</span>
            </div>
            <div class="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
              <span>平均分 {{ experiment.averageScore }}</span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions justify-end mt-2">
            <button 
              class="btn btn-xs btn-ghost"
              @click="handleTaskPoints(experiment)"
            >
              任务点
            </button>
            <button 
              class="btn btn-xs btn-ghost"
              @click="handleEnvironment(experiment)"
            >
              环境配置
            </button>
            <button 
              class="btn btn-xs btn-ghost"
              @click="handleEdit(experiment)"
            >
              编辑
            </button>
            <button 
              class="btn btn-xs btn-ghost text-error"
              @click="handleDelete(experiment)"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <dialog :open="showTaskPointModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-lg">{{ activeExperiment?.name }} - 任务点管理</h3>
          <button class="btn btn-sm btn-circle btn-ghost" @click="showTaskPointModal = false">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div class="alert alert-info mb-4">
          <span>这里展示该实验的任务点结构和分值配置，可直接用于课堂汇报与复盘说明。</span>
        </div>

        <div class="space-y-3">
          <div v-for="task in activeExperiment?.taskPoints || []" :key="task.id" class="rounded-xl border border-base-200 bg-base-200/40 p-4">
            <div class="flex items-center justify-between gap-4">
              <div>
                <div class="font-semibold">{{ task.name }}</div>
                <div class="text-sm text-base-content/60 mt-1">{{ task.description }}</div>
              </div>
              <span class="badge badge-primary">{{ task.score }} 分</span>
            </div>
          </div>
        </div>

        <div class="modal-action">
          <button class="btn" @click="showTaskPointModal = false">关闭</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showTaskPointModal = false">关闭</button>
      </form>
    </dialog>

    <dialog :open="showEnvironmentModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-lg">{{ activeExperiment?.name }} - 环境配置</h3>
          <button class="btn btn-sm btn-circle btn-ghost" @click="showEnvironmentModal = false">
            <i class="fas fa-times"></i>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="rounded-xl border border-base-200 bg-base-200/40 p-4">
            <div class="font-semibold mb-3">靶机环境</div>
            <div class="text-sm space-y-2 text-base-content/70">
              <div>镜像：{{ activeExperiment?.environment.targetMachine?.image || '未配置' }}</div>
              <div>端口：{{ activeExperiment?.environment.targetMachine?.port || '--' }}</div>
              <div>内存：{{ activeExperiment?.environment.targetMachine?.memory || '--' }}</div>
            </div>
          </div>
          <div class="rounded-xl border border-base-200 bg-base-200/40 p-4">
            <div class="font-semibold mb-3">操作环境</div>
            <div class="text-sm space-y-2 text-base-content/70">
              <div>镜像：{{ activeExperiment?.environment.operationMachine?.image || '未配置' }}</div>
              <div>端口：{{ activeExperiment?.environment.operationMachine?.port || '--' }}</div>
              <div>内存：{{ activeExperiment?.environment.operationMachine?.memory || '--' }}</div>
            </div>
          </div>
        </div>

        <div class="alert alert-info mt-4">
          <span>该区域当前用于查看实验环境与配置效果，可直接用于课堂汇报说明。</span>
        </div>

        <div class="modal-action">
          <button class="btn" @click="showEnvironmentModal = false">关闭</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showEnvironmentModal = false">关闭</button>
      </form>
    </dialog>

    <dialog :open="showEditorModal" class="modal modal-bottom sm:modal-middle">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">{{ editingExperimentId ? '编辑实验' : '创建实验' }}</h3>

        <div v-if="editorError" class="alert alert-error mb-4">
          <span>{{ editorError }}</span>
        </div>

        <div class="space-y-4">
          <label class="form-control">
            <span class="label-text mb-2">实验名称</span>
            <input v-model="experimentForm.name" type="text" class="input input-bordered" placeholder="请输入实验名称">
          </label>

          <label class="form-control">
            <span class="label-text mb-2">实验描述</span>
            <textarea v-model="experimentForm.description" class="textarea textarea-bordered h-28" placeholder="请输入实验描述"></textarea>
          </label>

          <label class="form-control">
            <span class="label-text mb-2">实验难度</span>
            <select v-model="experimentForm.difficulty" class="select select-bordered">
              <option v-for="n in 5" :key="n" :value="n">{{ n }} 星</option>
            </select>
          </label>

          <label class="form-control">
            <span class="label-text mb-2">实验分类</span>
            <input v-model="experimentForm.type" type="text" class="input input-bordered" placeholder="例如：Web安全 / 系统安全">
          </label>
        </div>

        <div class="modal-action">
          <button class="btn btn-ghost" @click="showEditorModal = false">取消</button>
          <button class="btn btn-primary" :disabled="isSubmitting" @click="submitExperimentForm">
            {{ isSubmitting ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop">
        <button @click="showEditorModal = false">关闭</button>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.container-fluid {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

html, body {
  overflow-x: hidden;
  margin: 0;
  padding: 0;
  width: 100%;
}

/* 压缩卡片样式 */
.compact-card {
  margin-bottom: 0.5rem;
}

.compact-card .card-body {
  padding: 1rem;
}

.compact-card details summary {
  list-style: none;
  display: flex;
  align-items: center;
}

.compact-card details summary::after {
  content: '▼';
  font-size: 0.7rem;
  margin-left: 0.5rem;
}

.compact-card details[open] summary::after {
  content: '▲';
}
</style> 
