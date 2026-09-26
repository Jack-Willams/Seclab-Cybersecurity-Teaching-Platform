<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  deleteTeachingClass,
  confirmTeachingClassImport,
  createTeachingClass,
  getApiErrorMessage,
  getTeacherCourseList,
  getTeachingClassCourses,
  getTeachingClasses,
  getTeachingClassStudents,
  previewTeachingClassImport,
  removeTeachingClassStudent,
  replaceTeachingClassCourses,
  updateTeachingClassCourseContent,
  updateTeachingClass,
  type TeachingClassCourseDto,
  type TeachingClassDto,
  type TeachingClassImportPreviewDto,
  type TeachingClassSavePayload,
  type TeachingClassStudentDto,
} from '../../../api'
import type { Course } from '../../../types/course'

type CoursePlan = { courseId: number; teachingOrder: number; plannedStartDate: string; plannedEndDate: string }

const classes = ref<TeachingClassDto[]>([])
const selected = ref<TeachingClassDto | null>(null)
const students = ref<TeachingClassStudentDto[]>([])
const arrangedCourses = ref<TeachingClassCourseDto[]>([])
const courseLibrary = ref<Course[]>([])
const tab = ref<'students' | 'courses'>('students')
const loading = ref(true)
// 首屏渲染后再放动画，避免刷新时元素闪一下
const isLoaded = ref(false)
const detailLoading = ref(false)
const error = ref('')
const notice = ref('')
const showClassModal = ref(false)
const editingClass = ref<TeachingClassDto | null>(null)
const savingClass = ref(false)
const classForm = ref<TeachingClassSavePayload>({ className: '', academicYear: '2026-2027', semester: 1, startDate: null, endDate: null })
const showImportModal = ref(false)
const importPreview = ref<TeachingClassImportPreviewDto | null>(null)
const importFile = ref<File | null>(null)
const importing = ref(false)
const showCourseModal = ref(false)
const coursePlans = ref<CoursePlan[]>([])
const savingCourses = ref(false)
const showTeachingContentModal = ref(false)
const editingCourseContent = ref<TeachingClassCourseDto | null>(null)
const teachingContentForm = ref('')
const savingTeachingContent = ref(false)

const activeClasses = computed(() => classes.value.filter((item) => item.status !== 'ARCHIVED'))
const selectedCourseIds = computed(() => new Set(coursePlans.value.map((item) => item.courseId)))
const availableCourses = computed(() => courseLibrary.value.filter((item) => !selectedCourseIds.value.has(item.id)))
const courseName = (courseId: number) => courseLibrary.value.find((item) => item.id === courseId)?.name || `课程 ${courseId}`
const semesterLabel = (item: TeachingClassDto) => `${item.academicYear}学年 · 第${item.semester}学期`
const formatDateTime = (value?: string | null) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '暂无记录'

const loadClassDetail = async (item: TeachingClassDto) => {
  selected.value = item
  detailLoading.value = true
  notice.value = ''
  const [studentResult, courseResult] = await Promise.allSettled([
    getTeachingClassStudents(item.teachingClassId),
    getTeachingClassCourses(item.teachingClassId),
  ])
  if (selected.value?.teachingClassId !== item.teachingClassId) return
  students.value = studentResult.status === 'fulfilled' ? studentResult.value : []
  arrangedCourses.value = courseResult.status === 'fulfilled' ? courseResult.value : []
  if (studentResult.status === 'rejected' || courseResult.status === 'rejected') notice.value = '部分教学班数据暂时未能加载，请稍后重试。'
  detailLoading.value = false
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [classData, courses] = await Promise.all([getTeachingClasses(), getTeacherCourseList()])
    classes.value = classData
    courseLibrary.value = courses
    const current = selected.value
      ? classData.find((item) => item.teachingClassId === selected.value?.teachingClassId)
      : activeClasses.value[0]
    if (current) await loadClassDetail(current)
  } catch (err) {
    error.value = getApiErrorMessage(err, '教学班加载失败，请稍后重试。')
  } finally {
    loading.value = false
    setTimeout(() => { isLoaded.value = true }, 100)
  }
}

const openCreate = () => {
  editingClass.value = null
  classForm.value = { className: '', academicYear: '2026-2027', semester: 1, startDate: null, endDate: null }
  showClassModal.value = true
}

const openEdit = () => {
  if (!selected.value?.canManage) return
  editingClass.value = selected.value
  classForm.value = {
    className: selected.value.className,
    academicYear: selected.value.academicYear,
    semester: selected.value.semester,
    startDate: selected.value.startDate || null,
    endDate: selected.value.endDate || null,
  }
  showClassModal.value = true
}

const saveClass = async () => {
  if (!classForm.value.className.trim() || !/^\d{4}-\d{4}$/.test(classForm.value.academicYear)) return
  savingClass.value = true
  try {
    const payload = { ...classForm.value, className: classForm.value.className.trim() }
    const saved = editingClass.value
      ? await updateTeachingClass(editingClass.value.teachingClassId, payload)
      : await createTeachingClass(payload)
    showClassModal.value = false
    await load()
    const refreshed = classes.value.find((item) => item.teachingClassId === saved.teachingClassId)
    if (refreshed) await loadClassDetail(refreshed)
  } catch (err) {
    notice.value = getApiErrorMessage(err, '教学班保存失败，请检查填写内容。')
  } finally {
    savingClass.value = false
  }
}

const deleteCurrent = async () => {
  if (!selected.value?.canManage) return
  const target = selected.value
  const warning = [
    `确定删除“${target.className}”吗？`,
    '',
    '将同时永久删除：',
    `· 本班 ${target.studentCount} 名学生中，只属于本班的学生账号及其全部学习记录`,
    '· 本班的课程安排、导入批次、教学分析与干预记录',
    '',
    '同时还在其他教学班的学生只会退出本班，账号保留。',
    '此操作不可恢复。',
  ].join('\n')
  if (!window.confirm(warning)) return
  try {
    const result = await deleteTeachingClass(target.teachingClassId)
    notice.value = result.keptStudentCount > 0
      ? `教学班已删除，同时删除 ${result.deletedStudentCount} 名学生；${result.keptStudentCount} 名学生因还在其他教学班而保留。`
      : `教学班已删除，同时删除 ${result.deletedStudentCount} 名学生。`
    selected.value = null
    await load()
  } catch (err) {
    notice.value = getApiErrorMessage(err, '教学班删除失败，请稍后重试。')
  }
}

const openImport = () => {
  importFile.value = null
  importPreview.value = null
  showImportModal.value = true
}

const chooseFile = (event: Event) => {
  importFile.value = (event.target as HTMLInputElement).files?.[0] || null
  importPreview.value = null
}

const previewImport = async () => {
  if (!selected.value || !importFile.value) return
  importing.value = true
  try { importPreview.value = await previewTeachingClassImport(selected.value.teachingClassId, importFile.value) }
  catch (err) { notice.value = getApiErrorMessage(err, '名单校验失败，请检查 Excel 格式。') }
  finally { importing.value = false }
}

const confirmImport = async () => {
  if (!selected.value || !importPreview.value || importPreview.value.errorRows.length) return
  importing.value = true
  try {
    const result = await confirmTeachingClassImport(selected.value.teachingClassId, importPreview.value.batchId)
    notice.value = `导入完成：新增账号 ${result.createdAccountCount} 个，加入教学班 ${result.addedMemberCount} 人。`
    showImportModal.value = false
    await loadClassDetail(selected.value)
    await load()
  } catch (err) { notice.value = getApiErrorMessage(err, '名单导入失败，请重新校验。') }
  finally { importing.value = false }
}

const removeStudent = async (student: TeachingClassStudentDto) => {
  if (!selected.value?.canManage) return
  const name = student.studentName || student.studentNumber
  if (!window.confirm(`确定删除学生“${name}”吗？\n\n账号、答题记录、训练记录、AI 会话等全部学习数据都会被永久删除，此操作不可恢复。`)) return
  try {
    await removeTeachingClassStudent(selected.value.teachingClassId, student.studentId)
    notice.value = `学生“${name}”已删除，账号和全部学习记录已一并清除。`
    await loadClassDetail(selected.value)
    await load()
  } catch (err) {
    notice.value = getApiErrorMessage(err, '学生删除失败，请稍后重试。')
  }
}

const openCoursePlan = () => {
  if (!selected.value?.canManage) return
  coursePlans.value = arrangedCourses.value.map((item) => ({
    courseId: item.courseId,
    teachingOrder: item.teachingOrder,
    plannedStartDate: item.plannedStartDate || '',
    plannedEndDate: item.plannedEndDate || '',
  }))
  showCourseModal.value = true
}

const addCourse = (event: Event) => {
  const courseId = Number((event.target as HTMLSelectElement).value)
  if (!courseId) return
  coursePlans.value.push({ courseId, teachingOrder: coursePlans.value.length + 1, plannedStartDate: '', plannedEndDate: '' })
  ;(event.target as HTMLSelectElement).value = ''
}

const moveCourse = (index: number, direction: -1 | 1) => {
  const target = index + direction
  if (target < 0 || target >= coursePlans.value.length) return
  const next = [...coursePlans.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  coursePlans.value = next.map((item, order) => ({ ...item, teachingOrder: order + 1 }))
}

const removeCourse = (index: number) => { coursePlans.value.splice(index, 1); coursePlans.value = coursePlans.value.map((item, order) => ({ ...item, teachingOrder: order + 1 })) }

const saveCoursePlan = async () => {
  if (!selected.value) return
  savingCourses.value = true
  try {
    arrangedCourses.value = await replaceTeachingClassCourses(selected.value.teachingClassId, coursePlans.value.map((item, order) => ({
      ...item,
      teachingOrder: order + 1,
      plannedStartDate: item.plannedStartDate || null,
      plannedEndDate: item.plannedEndDate || null,
    })))
    showCourseModal.value = false
    await load()
  } catch (err) { notice.value = getApiErrorMessage(err, '教学安排保存失败。') }
  finally { savingCourses.value = false }
}

const openTeachingContentEditor = (course: TeachingClassCourseDto) => {
  if (!selected.value?.canManage) return
  editingCourseContent.value = course
  teachingContentForm.value = course.teachingContent || ''
  showTeachingContentModal.value = true
}

const saveTeachingContent = async () => {
  if (!selected.value || !editingCourseContent.value) return
  savingTeachingContent.value = true
  try {
    const saved = await updateTeachingClassCourseContent(
      selected.value.teachingClassId,
      editingCourseContent.value.courseId,
      teachingContentForm.value.trim() || null,
    )
    const index = arrangedCourses.value.findIndex((item) => item.courseId === saved.courseId)
    if (index >= 0) arrangedCourses.value[index] = saved
    showTeachingContentModal.value = false
    notice.value = '教学内容已保存，只影响当前教学班。'
  } catch (err) {
    notice.value = getApiErrorMessage(err, '教学内容保存失败，请稍后重试。')
  } finally {
    savingTeachingContent.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="mx-auto min-h-full max-w-[1540px] px-5 pb-14 pt-8 lg:px-10">
    <header
      class="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between"
      :class="{ 'animate-fade-in': isLoaded }"
    >
      <div>
        <h1 class="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-3xl font-bold text-transparent">
          教学班
        </h1>
        <p class="mt-1.5 text-sm text-base-content/70">按学期组织学生和课程。所有教师可查看，创建人负责维护。</p>
      </div>
      <button class="btn btn-primary btn-sm gap-2 self-start" @click="openCreate">
        <i class="fas fa-plus"></i>创建教学班
      </button>
    </header>

    <div v-if="notice" class="alert alert-info mb-4">
      <i class="fas fa-circle-info"></i>
      <span>{{ notice }}</span>
      <button class="btn btn-ghost btn-xs" @click="notice = ''">知道了</button>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <div v-else-if="error" class="alert alert-error">
      <i class="fas fa-circle-exclamation"></i>
      <span>{{ error }}</span>
      <button class="btn btn-sm" @click="load">重新加载</button>
    </div>

    <div v-else class="grid items-start gap-4 lg:grid-cols-[292px_minmax(0,1fr)]" :class="{ 'animate-slide-up': isLoaded }">
      <aside class="card overflow-hidden bg-base-100 shadow-lg">
        <div class="flex items-center justify-between border-b border-base-200 px-4 py-3.5 text-xs font-bold text-base-content/60">
          当前教学班<span class="badge badge-ghost badge-sm">{{ activeClasses.length }}</span>
        </div>
        <button
          v-for="item in activeClasses"
          :key="item.teachingClassId"
          type="button"
          class="grid w-full gap-1.5 border-b border-l-[3px] border-base-200 px-4 py-3.5 text-left transition-colors"
          :class="selected?.teachingClassId === item.teachingClassId
            ? 'border-l-primary bg-primary/10'
            : 'border-l-transparent hover:bg-base-200'"
          @click="loadClassDetail(item)"
        >
          <span class="flex items-center justify-between gap-2">
            <strong class="truncate text-sm">{{ item.className }}</strong>
            <span v-if="item.canManage" class="badge badge-primary badge-xs shrink-0">我创建</span>
          </span>
          <span class="text-[11px] text-base-content/60">{{ semesterLabel(item) }}</span>
          <small class="text-[11px] text-base-content/60">{{ item.studentCount }} 名学生 · {{ item.courseCount }} 门课程</small>
        </button>
        <div v-if="!activeClasses.length" class="flex min-h-[120px] items-center justify-center text-sm text-base-content/60">
          暂无教学班
        </div>
      </aside>

      <section v-if="selected" class="card overflow-hidden bg-base-100 shadow-lg">
        <div class="flex flex-col items-start justify-between gap-4 p-6 md:flex-row">
          <div class="min-w-0">
            <span class="text-xs text-base-content/60">{{ semesterLabel(selected) }}</span>
            <h2 class="my-1 text-xl font-bold">{{ selected.className }}</h2>
            <p class="text-xs text-base-content/60">
              任课教师：{{ selected.teacherName || '未填写' }} · 最近活动：{{ formatDateTime(selected.lastActiveAt) }}
            </p>
          </div>
          <div v-if="selected.canManage" class="flex shrink-0 gap-2">
            <button class="btn btn-outline btn-sm gap-1.5" @click="openEdit"><i class="fas fa-pen text-xs"></i>编辑信息</button>
            <button class="btn btn-outline btn-error btn-sm gap-1.5" @click="deleteCurrent"><i class="fas fa-trash text-xs"></i>删除教学班</button>
          </div>
          <span v-else class="badge badge-ghost">只读</span>
        </div>

        <div role="tablist" class="tabs tabs-bordered border-y border-base-200 px-5">
          <button role="tab" class="tab gap-1.5" :class="{ 'tab-active': tab === 'students' }" @click="tab = 'students'">
            学生名单<span class="badge badge-ghost badge-sm">{{ students.length }}</span>
          </button>
          <button role="tab" class="tab gap-1.5" :class="{ 'tab-active': tab === 'courses' }" @click="tab = 'courses'">
            教学安排<span class="badge badge-ghost badge-sm">{{ arrangedCourses.length }}</span>
          </button>
        </div>

        <div v-if="detailLoading" class="flex justify-center py-14">
          <span class="loading loading-spinner loading-md text-primary"></span>
        </div>

        <template v-else-if="tab === 'students'">
          <div class="flex flex-col items-start justify-between gap-3 p-5 md:flex-row md:items-center">
            <div>
              <strong class="block text-sm">学生名单</strong>
              <span class="mt-0.5 block text-[11px] text-base-content/60">账号不存在时将自动创建，初始密码为 123456</span>
            </div>
            <div v-if="selected.canManage" class="flex gap-2">
              <a class="btn btn-outline btn-sm gap-1.5" href="/templates/教学班学生导入模板.xlsx">
                <i class="fas fa-download text-xs"></i>下载模板
              </a>
              <button class="btn btn-primary btn-sm gap-1.5" @click="openImport">
                <i class="fas fa-file-excel text-xs"></i>导入 Excel
              </button>
            </div>
          </div>
          <div v-if="students.length" class="overflow-x-auto">
            <table class="table table-zebra">
              <thead class="bg-base-200/60">
                <tr>
                  <th>学号</th><th>姓名</th><th>行政班</th><th>加入时间</th><th>最近活动</th>
                  <th v-if="selected.canManage" class="text-center">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="student in students" :key="student.studentId">
                  <td class="whitespace-nowrap">{{ student.studentNumber }}</td>
                  <td class="font-semibold">{{ student.studentName || '未填写' }}</td>
                  <td>{{ student.administrativeClass || '—' }}</td>
                  <td class="whitespace-nowrap text-base-content/70">{{ formatDateTime(student.joinedAt) }}</td>
                  <td class="whitespace-nowrap text-base-content/70">{{ formatDateTime(student.recentActivityAt) }}</td>
                  <td v-if="selected.canManage" class="text-center">
                    <button class="btn btn-ghost btn-xs text-error" @click="removeStudent(student)">删除学生</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="flex min-h-[220px] flex-col items-center justify-center gap-2 p-6 text-center">
            <i class="fas fa-user-plus text-4xl text-base-content/25"></i>
            <h3 class="text-lg font-semibold">还没有学生</h3>
            <p class="text-sm text-base-content/70">下载模板填写名单后导入即可。</p>
          </div>
        </template>

        <template v-else>
          <div class="flex flex-col items-start justify-between gap-3 p-5 md:flex-row md:items-center">
            <div>
              <strong class="block text-sm">教学安排</strong>
              <span class="mt-0.5 block text-[11px] text-base-content/60">课程可跨学期复用，这里只安排本教学班的授课顺序</span>
            </div>
            <button v-if="selected.canManage" class="btn btn-primary btn-sm gap-1.5" @click="openCoursePlan">
              <i class="fas fa-list-ol text-xs"></i>调整课程
            </button>
          </div>
          <div v-if="arrangedCourses.length" class="px-5 pb-4">
            <div
              v-for="(course, index) in arrangedCourses"
              :key="course.courseId"
              class="flex gap-3.5 border-t border-base-200 py-4"
            >
              <span class="grid h-7 w-7 flex-none place-items-center rounded-full bg-primary/15 text-[11px] font-bold text-primary">
                {{ index + 1 }}
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2.5">
                  <strong class="text-sm">{{ course.courseName }}</strong>
                  <button
                    v-if="selected.canManage"
                    type="button"
                    class="btn btn-ghost btn-xs text-primary"
                    @click="openTeachingContentEditor(course)"
                  >
                    编辑内容
                  </button>
                </div>
                <p class="my-1 max-w-[700px] text-xs leading-relaxed text-base-content/60">
                  {{ course.teachingContent || course.courseDescription || '暂无教学内容' }}
                </p>
                <small class="text-xs text-primary">
                  {{ course.plannedStartDate || '未设置开始日期' }}
                  <template v-if="course.plannedEndDate"> 至 {{ course.plannedEndDate }}</template>
                </small>
              </div>
            </div>
          </div>
          <div v-else class="flex min-h-[220px] flex-col items-center justify-center gap-2 p-6 text-center">
            <i class="fas fa-list-ol text-4xl text-base-content/25"></i>
            <h3 class="text-lg font-semibold">还没有安排课程</h3>
            <p class="text-sm text-base-content/70">从课程库中选择本学期要讲授的课程。</p>
          </div>
        </template>
      </section>

      <section v-else class="card bg-base-100 shadow-lg">
        <div class="card-body items-center py-14 text-center">
          <i class="fas fa-hand-pointer mb-1 text-4xl text-base-content/25"></i>
          <h3 class="text-lg font-semibold">选择一个教学班</h3>
          <p class="text-sm text-base-content/70">查看学生名单和教学安排。</p>
        </div>
      </section>
    </div>

    <!-- 创建 / 编辑教学班 -->
    <div v-if="showClassModal" class="modal modal-open" @click.self="showClassModal = false">
      <div class="modal-box max-w-xl">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold">{{ editingClass ? '编辑教学班' : '创建教学班' }}</h2>
          <button class="btn btn-ghost btn-sm btn-circle" type="button" @click="showClassModal = false">✕</button>
        </div>
        <form class="space-y-4" @submit.prevent="saveClass">
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">教学班名称</span></div>
            <input v-model="classForm.className" class="input input-sm input-bordered" maxlength="120" required placeholder="例如：网络安全232班" />
          </label>
          <div class="grid gap-4 sm:grid-cols-2">
            <label class="form-control">
              <div class="label py-1"><span class="label-text text-xs font-semibold">学年</span></div>
              <input v-model="classForm.academicYear" class="input input-sm input-bordered" required pattern="\d{4}-\d{4}" placeholder="2026-2027" />
            </label>
            <label class="form-control">
              <div class="label py-1"><span class="label-text text-xs font-semibold">学期</span></div>
              <select v-model="classForm.semester" class="select select-sm select-bordered">
                <option :value="1">第1学期</option><option :value="2">第2学期</option>
              </select>
            </label>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <label class="form-control">
              <div class="label py-1"><span class="label-text text-xs font-semibold">开始日期（可选）</span></div>
              <input v-model="classForm.startDate" type="date" class="input input-sm input-bordered" />
            </label>
            <label class="form-control">
              <div class="label py-1"><span class="label-text text-xs font-semibold">结束日期（可选）</span></div>
              <input v-model="classForm.endDate" type="date" class="input input-sm input-bordered" />
            </label>
          </div>
          <div class="modal-action">
            <button type="button" class="btn btn-ghost btn-sm" @click="showClassModal = false">取消</button>
            <button class="btn btn-primary btn-sm" :disabled="savingClass">
              <span v-if="savingClass" class="loading loading-spinner loading-xs"></span>{{ savingClass ? '保存中…' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 导入学生名单 -->
    <div v-if="showImportModal" class="modal modal-open" @click.self="showImportModal = false">
      <div class="modal-box max-w-xl">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold">导入学生名单</h2>
          <button class="btn btn-ghost btn-sm btn-circle" type="button" @click="showImportModal = false">✕</button>
        </div>
        <div class="space-y-4">
          <div class="alert alert-info py-2.5 text-xs">
            <i class="fas fa-circle-info"></i>
            <span>Excel 表头须为“学号、姓名、行政班”。系统先校验，不会直接写入数据。</span>
          </div>
          <label class="form-control">
            <div class="label py-1"><span class="label-text text-xs font-semibold">选择 .xlsx 文件</span></div>
            <input type="file" accept=".xlsx" class="file-input file-input-sm file-input-bordered w-full" @change="chooseFile" />
          </label>
          <button
            v-if="!importPreview"
            class="btn btn-outline btn-sm"
            :disabled="!importFile || importing"
            @click="previewImport"
          >
            <span v-if="importing" class="loading loading-spinner loading-xs"></span>{{ importing ? '正在校验…' : '校验名单' }}
          </button>
          <template v-if="importPreview">
            <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <div class="rounded-lg bg-base-200 p-3 text-center">
                <strong class="block text-lg text-primary">{{ importPreview.newAccounts.length }}</strong>
                <span class="text-[10px] text-base-content/60">新建账号</span>
              </div>
              <div class="rounded-lg bg-base-200 p-3 text-center">
                <strong class="block text-lg text-primary">{{ importPreview.existingAccounts.length }}</strong>
                <span class="text-[10px] text-base-content/60">已有账号</span>
              </div>
              <div class="rounded-lg bg-base-200 p-3 text-center">
                <strong class="block text-lg text-primary">{{ importPreview.duplicateRows.length }}</strong>
                <span class="text-[10px] text-base-content/60">重复行</span>
              </div>
              <div class="rounded-lg p-3 text-center" :class="importPreview.errorRows.length ? 'bg-error/10' : 'bg-base-200'">
                <strong class="block text-lg" :class="importPreview.errorRows.length ? 'text-error' : 'text-primary'">
                  {{ importPreview.errorRows.length }}
                </strong>
                <span class="text-[10px] text-base-content/60">错误行</span>
              </div>
            </div>
            <div v-if="importPreview.errorRows.length" class="alert alert-error flex-col items-start gap-1 py-2.5 text-xs">
              <div v-for="item in importPreview.errorRows" :key="item.rowNumber">第 {{ item.rowNumber }} 行：{{ item.message }}</div>
            </div>
            <p class="text-xs text-base-content/60">确认后，新账号初始密码为 123456；不会强制学生首次登录修改密码。</p>
          </template>
        </div>
        <div class="modal-action">
          <button class="btn btn-ghost btn-sm" @click="showImportModal = false">取消</button>
          <button
            class="btn btn-primary btn-sm"
            :disabled="!importPreview || !!importPreview.errorRows.length || importing"
            @click="confirmImport"
          >
            <span v-if="importing" class="loading loading-spinner loading-xs"></span>{{ importing ? '导入中…' : '确认导入' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 安排教学课程 -->
    <div v-if="showCourseModal" class="modal modal-open" @click.self="showCourseModal = false">
      <div class="modal-box max-w-3xl">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold">安排教学课程</h2>
          <button class="btn btn-ghost btn-sm btn-circle" type="button" @click="showCourseModal = false">✕</button>
        </div>
        <div class="space-y-3">
          <div class="alert alert-info py-2.5 text-xs">
            <i class="fas fa-circle-info"></i><span>课程来自共享课程库；调整只影响当前教学班。</span>
          </div>
          <select class="select select-sm select-bordered w-full" @change="addCourse">
            <option value="">＋ 选择课程加入安排</option>
            <option v-for="course in availableCourses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <div v-for="(plan, index) in coursePlans" :key="plan.courseId" class="rounded-lg border border-base-300 p-3.5">
            <div class="mb-3 flex items-center gap-2.5">
              <span class="text-xs font-bold text-primary">{{ index + 1 }}</span>
              <strong class="flex-1 truncate text-sm">{{ courseName(plan.courseId) }}</strong>
              <div class="join">
                <button class="btn btn-ghost join-item btn-xs" :disabled="index === 0" @click="moveCourse(index, -1)">↑</button>
                <button class="btn btn-ghost join-item btn-xs" :disabled="index === coursePlans.length - 1" @click="moveCourse(index, 1)">↓</button>
              </div>
              <button class="btn btn-ghost btn-xs text-error" @click="removeCourse(index)">移除</button>
            </div>
            <div class="grid gap-3 sm:grid-cols-2">
              <label class="form-control">
                <div class="label py-1"><span class="label-text text-xs">计划开始</span></div>
                <input v-model="plan.plannedStartDate" type="date" class="input input-sm input-bordered" />
              </label>
              <label class="form-control">
                <div class="label py-1"><span class="label-text text-xs">计划结束</span></div>
                <input v-model="plan.plannedEndDate" type="date" class="input input-sm input-bordered" />
              </label>
            </div>
          </div>
          <div v-if="!coursePlans.length" class="py-8 text-center text-sm text-base-content/60">从上方选择课程</div>
        </div>
        <div class="modal-action">
          <button class="btn btn-ghost btn-sm" @click="showCourseModal = false">取消</button>
          <button class="btn btn-primary btn-sm" :disabled="savingCourses" @click="saveCoursePlan">
            <span v-if="savingCourses" class="loading loading-spinner loading-xs"></span>{{ savingCourses ? '保存中…' : '保存安排' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编写教学内容 -->
    <div v-if="showTeachingContentModal" class="modal modal-open" @click.self="showTeachingContentModal = false">
      <div class="modal-box max-w-xl">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-bold">编写教学内容</h2>
          <button class="btn btn-ghost btn-sm btn-circle" type="button" @click="showTeachingContentModal = false">✕</button>
        </div>
        <div class="mb-3.5 text-[15px] font-bold">{{ editingCourseContent?.courseName }}</div>
        <label class="form-control">
          <div class="label py-1"><span class="label-text text-xs font-semibold">本班教学内容</span></div>
          <textarea
            v-model="teachingContentForm"
            class="textarea textarea-bordered min-h-[150px] text-sm leading-relaxed"
            maxlength="2000"
            rows="7"
            placeholder="填写这节课在当前教学班要讲授的具体内容、重点或实践安排"
          ></textarea>
          <div class="label py-1">
            <span class="label-text-alt text-xs text-base-content/60">{{ teachingContentForm.length }} / 2000；留空将显示课程库简介</span>
          </div>
        </label>
        <div class="modal-action">
          <button type="button" class="btn btn-ghost btn-sm" @click="showTeachingContentModal = false">取消</button>
          <button type="button" class="btn btn-primary btn-sm" :disabled="savingTeachingContent" @click="saveTeachingContent">
            <span v-if="savingTeachingContent" class="loading loading-spinner loading-xs"></span>{{ savingTeachingContent ? '保存中…' : '保存内容' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 动画与学生端课程页保持一致 */
.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  opacity: 0;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
