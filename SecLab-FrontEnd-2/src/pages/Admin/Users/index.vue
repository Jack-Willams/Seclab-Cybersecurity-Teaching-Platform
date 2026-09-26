<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getApiErrorMessage, getTeacherUserPage, getTeacherUserFilterOptions, createTeacherUser, updateTeacherUser, deleteTeacherUser, resetTeacherUserPassword } from '../../../api'
import type { User } from '../../../types/user'

const users = ref<User[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// 搜索和筛选条件
const filters = ref({
  search: '',
  academy: '',
  class: '',
  gender: '',
  status: 'active'
})

// 分页
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0
})

// 计算页数
const totalPages = computed(() => {
  if (pagination.value.pageSize <= 0) return 0;
  return Math.ceil(pagination.value.total / pagination.value.pageSize)
})

// 当前页显示的用户(因为后端分页，直接返回 users)
const currentPageUsers = computed(() => users.value)

// 获取用户
let debounceTimer: any = null;
let requestVersion = 0;
const fetchUsers = async () => {
  const version = ++requestVersion;
  try {
    loading.value = true;
    error.value = null;
    const res = await getTeacherUserPage(
      pagination.value.current, 
      pagination.value.pageSize,
      filters.value.search || undefined,
      filters.value.academy || undefined,
      filters.value.class || undefined,
      filters.value.status || undefined,
      filters.value.gender || undefined
    );
    if (version !== requestVersion) return;
    users.value = res.list.map(u => ({
      userId: u.userId,
      userStudentNumber: u.userStudentNumber,
      userName: u.userName || '未填写',
      userEmail: u.userEmail,
      userTel: u.userTel,
      userAcademy: u.userAcademy,
      userClass: u.userClass,
      userGender: u.userGender,
      createTime: u.createTime,
      classId: u.classId,
      status: u.status
    }));
    pagination.value.total = res.total || 0;
  } catch (err: any) {
    if (version !== requestVersion) return;
    error.value = getApiErrorMessage(err, '用户数据加载失败，请重新加载。');
    console.error(err);
  } finally {
    if (version === requestVersion) loading.value = false;
  }
}

// 防抖过滤
const handleFilterChange = () => {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    pagination.value.current = 1;
    fetchUsers();
  }, 500);
}

// 页码数组
const pageNumbers = computed(() => {
  const current = pagination.value.current
  const total = totalPages.value
  const pages = []

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 2) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
  }
  return pages
})

const handlePageChange = (page: number | string) => {
  if (typeof page === 'number') {
    pagination.value.current = page;
    fetchUsers();
  }
}

const handlePageSizeChange = (event: Event) => {
  const target = event.target as HTMLSelectElement;
  pagination.value.pageSize = parseInt(target.value);
  pagination.value.current = 1;
  fetchUsers();
}



const handleDelete = async (user: User) => {
  if (confirm('确认删除用户 ' + user.userName + '？')) {
    try {
      await deleteTeacherUser(user.userId);
      fetchUsers();
    } catch (e: any) {
      alert(getApiErrorMessage(e, '删除失败'));
    }
  }
}

const handleResetPassword = async (user: User) => {
  if (confirm('确认重置用户 ' + user.userName + ' 的密码？')) {
    try {
      await resetTeacherUserPassword(user.userId);
      alert('重置密码成功');
    } catch (e: any) {
      alert(getApiErrorMessage(e, '重置失败'));
    }
  }
}

onMounted(() => {
  fetchUsers()
  fetchFilterOptions()
})

onUnmounted(() => {
  requestVersion++
  if (debounceTimer) clearTimeout(debounceTimer)
  users.value = []
  error.value = null
})

// 学院列表和班级列表 (可供筛选用)：从真实学生数据取，写死的名单和库里对不上，筛出来永远是空的
const academies = ref<string[]>([])
const classes = ref<string[]>([])

const fetchFilterOptions = async () => {
  try {
    const options = await getTeacherUserFilterOptions()
    academies.value = options.academies
    classes.value = options.classes
  } catch (err) {
    console.error('筛选项加载失败:', err)
  }
}

const isModalOpen = ref(false)
const modalType = ref<'add' | 'edit'>('add')
const saveLoading = ref(false)

const formData = ref<Partial<User>>({
  userStudentNumber: '',
  userName: '',
  userAcademy: '',
  userClass: '',
  userEmail: '',
  userTel: '',
  userGender: 1
})

const showAddModal = () => {
  modalType.value = 'add'
  formData.value = {
    userStudentNumber: '',
    userName: '',
    userAcademy: '',
    userClass: '',
    userEmail: '',
    userTel: '',
    userGender: 1
  }
  isModalOpen.value = true
}





const handleEdit = (user: User) => {
  modalType.value = 'edit'
  formData.value = {
    userId: user.userId,
    userStudentNumber: user.userStudentNumber,
    userName: user.userName,
    userAcademy: user.userAcademy,
    userClass: user.userClass,
    userEmail: user.userEmail,
    userTel: user.userTel,
    userGender: user.userGender
  }
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
}

const handleSaveUser = async () => {
  try {
    saveLoading.value = true
    const payload = {
      userStudentNumber: formData.value.userStudentNumber,
      userName: formData.value.userName || '',
      userAcademy: formData.value.userAcademy,
      userClass: formData.value.userClass,
      userEmail: formData.value.userEmail,
      userTel: formData.value.userTel,
      userGender: formData.value.userGender,
      classId: formData.value.classId
    }

    if (modalType.value === 'add') {
      await createTeacherUser(payload)
      alert('添加成功，初始密码为默认值，请留意后端设定')
    } else {
      if (!formData.value.userId) throw new Error('用户ID丢失')
      await updateTeacherUser(formData.value.userId, payload)
      alert('更新成功')
    }
    closeModal()
    fetchUsers()
  } catch (err: any) {
    alert(getApiErrorMessage(err, '保存失败'))
  } finally {
    saveLoading.value = false
  }
}

const genderText = (value?: number | null) => {
  if (value === 1) return '男'
  if (value === 0) return '女'
  if (value === 2) return '未知'
  return '未填写'
}

const genderClass = (value?: number | null) => {
  if (value === 1) return 'text-blue-600'
  if (value === 0) return 'text-sky-500'
  return 'text-base-content/50'
}

</script>

<template>
  <div class="min-h-screen bg-base-100">
    <div class="container mx-auto p-4">
      <!-- 页面标题 -->
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">用户管理</h1>
        <button class="btn btn-primary" @click="showAddModal">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          添加用户
        </button>
      </div>

      <!-- 搜索和筛选 -->
      <div class="card bg-base-100 shadow-xl mb-6">
        <div class="card-body">
          <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
            <!-- 搜索框 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">搜索</span>
              </label>
              <input type="text" class="input input-bordered" placeholder="搜索用户名或学号" v-model="filters.search" @input="handleFilterChange" />
            </div>

            <!-- 学院筛选 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">学院</span>
              </label>
              <select class="select select-bordered" v-model="filters.academy" @change="handleFilterChange">
                <option value="">全部</option>
                <option v-for="academy in academies" :key="academy" :value="academy">
                  {{ academy }}
                </option>
              </select>
            </div>

            <!-- 班级筛选 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">班级</span>
              </label>
              <select class="select select-bordered" v-model="filters.class" @change="handleFilterChange">
                <option value="">全部</option>
                <option v-for="class_ in classes" :key="class_" :value="class_">
                  {{ class_ }}
                </option>
              </select>
            </div>

            <!-- 性别筛选 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">性别</span>
              </label>
              <select class="select select-bordered" v-model="filters.gender" @change="handleFilterChange">
                <option value="">全部</option>
                <option value="1">男</option>
                <option value="0">女</option>
                <option value="2">未知</option>
              </select>
            </div>

            <!-- 状态筛选 -->
            <div class="form-control">
              <label class="label">
                <span class="label-text">状态</span>
              </label>
              <select class="select select-bordered" v-model="filters.status" @change="handleFilterChange">
                <option value="active">启用</option>
                <option value="disabled">禁用</option>
                <option value="all">全部</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- 添加加载和错误状态显示 -->
      <div v-if="loading" class="text-center py-4">
        <div class="loading loading-spinner loading-lg"></div>
      </div>
      <div v-else-if="error" class="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-warning/30 bg-warning/10 p-4" role="status">
        <span>{{ error }}</span>
        <button class="btn btn-sm" @click="fetchUsers">重新加载</button>
      </div>

      <!-- 优化后的用户列表表格 -->
      <div v-else class="card bg-base-100 shadow-xl">
        <div class="card-body p-0">
          <div class="overflow-x-auto">
            <table class="table table-zebra w-full">
              <thead class="bg-base-200">
                <tr>
                  <th class="whitespace-nowrap">学号</th>
                  <th class="whitespace-nowrap">姓名</th>
                  <th class="whitespace-nowrap">邮箱</th>
                  <th class="whitespace-nowrap">电话</th>
                  <th class="whitespace-nowrap">学院</th>
                  <th class="whitespace-nowrap">班级</th>
                  <th class="whitespace-nowrap">性别</th>
                  <th class="whitespace-nowrap">注册时间</th>
                  <th class="whitespace-nowrap text-center">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in currentPageUsers" :key="user.userId" class="hover">
                  <td class="whitespace-nowrap">{{ user.userStudentNumber }}</td>
                  <td class="whitespace-nowrap">{{ user.userName }}</td>
                  <td class="whitespace-nowrap">{{ user.userEmail }}</td>
                  <td class="whitespace-nowrap">{{ user.userTel }}</td>
                  <td class="whitespace-nowrap max-w-[200px] truncate" :title="user.userAcademy">
                    {{ user.userAcademy }}
                  </td>
                  <td class="whitespace-nowrap">{{ user.userClass }}</td>
                  <td class="whitespace-nowrap">
                    <span :class="genderClass(user.userGender)">
                      {{ genderText(user.userGender) }}
                    </span>
                  </td>
                  <td class="whitespace-nowrap">{{ user.createTime }}</td>
                  <td class="whitespace-nowrap">
                    <div class="flex justify-center gap-2">
                      <button class="btn btn-xs btn-ghost" @click="handleEdit(user)">编辑</button>
                      <button class="btn btn-xs btn-ghost text-warning" @click="handleResetPassword(user)">重置密码</button>
                      <button class="btn btn-xs btn-ghost text-error" @click="handleDelete(user)">删除</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 分页控件 -->
          <div class="flex flex-col sm:flex-row justify-between items-center p-4 bg-base-100 gap-4">
            <div class="text-sm text-base-content/60">
              共 {{ pagination.total }} 条记录，每页
              <select v-model="pagination.pageSize" class="select select-bordered select-sm mx-1" @change="handlePageSizeChange">
                <option :value="10">10</option>
                <option :value="20">20</option>
                <option :value="50">50</option>
                <option :value="100">100</option>
              </select>
              条
            </div>
            <div class="join">
              <button class="join-item btn btn-sm" :disabled="pagination.current === 1" @click="handlePageChange(pagination.current - 1)">«</button>
              <template v-for="page in pageNumbers" :key="page">
                <button v-if="page === '...'" class="join-item btn btn-sm btn-disabled">...</button>
                <button v-else class="join-item btn btn-sm" :class="{ 'btn-active': page === pagination.current }" @click="handlePageChange(Number(page))">
                  {{ page }}
                </button>
              </template>
              <button class="join-item btn btn-sm" :disabled="pagination.current === totalPages" @click="handlePageChange(pagination.current + 1)">»</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* 基础布局样式 */
.container {
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

/* 表格容器样式 */
.card {
  margin-bottom: 1.5rem;
  overflow: visible;
}

.card-body {
  overflow: visible;
}

.overflow-x-auto {
  overflow-x: none;
  overflow-y: visible;
  -webkit-overflow-scrolling: touch;
}

/* 表格样式优化 */
.table {
  font-size: 0.875rem;
  line-height: 1.25rem;
}

.table th {
  background-color: hsl(var(--b2));
  color: hsl(var(--bc) / 0.7);
  font-weight: 500;
  position: sticky;
  top: 0;
  z-index: 10;
}

.table td {
  font-size: 0.875rem;
  line-height: 1.25rem;
  transition: all 0.3s ease;
}

/* 动画效果 */
.table tr {
  transition: all 0.3s ease;
}

.table tr:hover td {
  background-color: hsl(var(--b2) / 0.5);
  transform: translateX(4px);
}

/* 按钮样式 */
.btn-xs {
  min-height: 0;
  height: 1.5rem;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}

/* 确保内容不换行 */
.whitespace-nowrap {
  white-space: nowrap;
}

/* 添加过渡效果 */
.hover {
  transition: all 0.3s ease;
}

/* 表格紧凑样式 */
.table-compact th,
.table-compact td {
  padding: 0.5rem;
}

/* 表格斑马纹 */
.table-zebra tbody tr:nth-child(even) {
  background-color: hsl(var(--b2) / 0.3);
}

/* 性别标记颜色 */
.gender-male {
  color: #3b82f6;
  transition: all 0.3s ease;
}

.gender-female {
  color: #ec4899;
  transition: all 0.3s ease;
}

/* 添加表格内容悬停效果 */
.table td > * {
  transition: all 0.3s ease;
}

.table tr:hover td > * {
  transform: scale(1.02);
}
</style>
