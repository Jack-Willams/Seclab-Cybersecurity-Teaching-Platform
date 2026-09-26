<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast } from '../../../common'
import {
  awaitCourseCatalog,
  catalogSource,
  ensureCourseCatalog,
  remoteCourseList,
} from '../../../composables/useCourseCatalog'
import {
  findPresentationLab,
  getCourseLearning,
  getPresentationCourseVideos,
  resolvePresentationCourse,
  videoUrlOf,
  type PresentationCourseModuleSeed,
  type PresentationCourseSeed,
  type PresentationVideoSeed,
} from '../../../mock/catalogPresentation'

const route = useRoute()
const router = useRouter()

const errorMessage = ref('')

// 课程内容来自 catalogPresentation 的种子数据；后端在线时用远端数据覆盖描述/封面/标签
const seed = ref<PresentationCourseSeed | undefined>(undefined)
const remote = computed(() => remoteCourseList.value.find((item) => Number(item.id) === Number(route.params.id)))

// 学习进度暂无真实后端（接入 /api/users/{uid}/course-progress 后再换成真实值）
const learningProgress = ref(0)

/* ------------------------------- 视频 ------------------------------- */

const playlist = computed<PresentationVideoSeed[]>(() => getPresentationCourseVideos(seed.value))
const activeVideoFile = ref<string>('')
const activeVideo = computed(() => playlist.value.find((item) => item.file === activeVideoFile.value))
const activeVideoSrc = computed(() => (activeVideoFile.value ? encodeURI(videoUrlOf(activeVideoFile.value)) : ''))

// 播放器实际用的地址：挂 #t= 媒体片段让浏览器定位到该时刻并把这一帧画出来，
// 等于拿视频首帧当封面。取 0.1s 而不是 0，是因为不少视频第 0 帧是纯黑的。
// 下载链接仍用不带片段的 activeVideoSrc。
const playerSrc = computed(() => (activeVideoSrc.value ? `${activeVideoSrc.value}#t=0.1` : ''))

// 时长直接读文件元数据，不写死 —— 之前写死的 10:28 和实际 17:32 对不上
const durations = ref<Record<string, number>>({})
const videoSize = ref<number | null>(null)

const formatDuration = (seconds?: number) => {
  if (!seconds || !Number.isFinite(seconds)) return '--:--'
  const total = Math.round(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m)
  return `${h > 0 ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')}`
}

const formatSize = (bytes: number | null) => {
  if (!bytes) return ''
  const mb = bytes / (1024 * 1024)
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)}GB` : `${Math.round(mb)}MB`
}

const probeDuration = (file: string) => {
  if (durations.value[file] !== undefined) return
  const probe = document.createElement('video')
  probe.preload = 'metadata'
  probe.muted = true
  probe.addEventListener(
    'loadedmetadata',
    () => {
      if (Number.isFinite(probe.duration)) {
        durations.value = { ...durations.value, [file]: probe.duration }
      }
    },
    { once: true },
  )
  probe.addEventListener('error', () => console.warn('读取视频元数据失败:', file), { once: true })
  probe.src = encodeURI(videoUrlOf(file))
}

const probeSize = async (file: string) => {
  videoSize.value = null
  try {
    const response = await fetch(encodeURI(videoUrlOf(file)), { method: 'HEAD' })
    const length = Number(response.headers.get('content-length'))
    if (Number.isFinite(length) && length > 0) videoSize.value = length
  } catch (error) {
    console.warn('读取视频体积失败:', file, error)
  }
}

const selectVideo = (file: string) => {
  if (file === activeVideoFile.value) return
  activeVideoFile.value = file
  void probeSize(file)
}

/* ------------------------------- 模块与实验 ------------------------------- */

const modules = computed<PresentationCourseModuleSeed[]>(() => seed.value?.modules ?? [])

// 相关实验 = 课程模块里真正挂了实验环境的那些，保证「课程模块」和「实战实验推荐」不会各说各话
const relatedLabs = computed(() =>
  modules.value
    .map((module) => findPresentationLab(module.labId))
    .filter((lab): lab is NonNullable<typeof lab> => Boolean(lab)),
)

const goToLab = (labId?: number) => {
  if (!labId) return
  router.push(`/user/module/${labId}`)
}

/* ------------------------------- 课程资源 ------------------------------- */

type CourseResource = {
  key: string
  name: string
  icon: string
  size: string
  /** 有 href 的是真实文件，直接下载；没有的是资源位，后端接口尚未接入 */
  href?: string
  download?: string
  pendingHint?: string
}

const courseResources = computed<CourseResource[]>(() => {
  const list: CourseResource[] = [
    { key: 'ppt', name: '课程PPT', icon: 'file-powerpoint', size: '2.5MB', pendingHint: '课件资源正在整理中，敬请期待' },
    { key: 'manual', name: '实验手册', icon: 'file-word', size: '1.8MB', pendingHint: '实验手册正在整理中，敬请期待' },
    { key: 'refs', name: '参考资料', icon: 'link', size: '', pendingHint: '参考资料正在整理中，敬请期待' },
  ]

  // 课程视频是真实文件：体积实测、点击即下载
  if (activeVideo.value) {
    list.push({
      key: 'video',
      name: '课程视频',
      icon: 'video',
      size: formatSize(videoSize.value),
      href: activeVideoSrc.value,
      download: activeVideo.value.file,
    })
  } else {
    list.push({ key: 'video', name: '课程视频', icon: 'video', size: '', pendingHint: '本课程暂未上传视频' })
  }

  return list
})

const onResourceClick = (resource: CourseResource) => {
  if (resource.href) return
  showToast(resource.pendingHint || '资源正在整理中，敬请期待')
}

/** 学习目标与前置知识 */
const learning = computed(() => getCourseLearning(seed.value?.id))

/* ------------------------------- 课程字段 ------------------------------- */

const courseName = computed(() => remote.value?.name || seed.value?.name || '')
const courseDescription = computed(() => seed.value?.longDescription || remote.value?.description || '')
const courseTags = computed(() => (seed.value?.tags?.length ? seed.value.tags : remote.value?.tags || []))
const courseDifficulty = computed(() => seed.value?.difficulty ?? remote.value?.difficulty ?? null)
const courseCategory = computed(() => seed.value?.category || remote.value?.type || '')

const getDifficultyStars = (difficulty: number | null) =>
  difficulty === null ? '未知' : '★'.repeat(difficulty) + '☆'.repeat(5 - difficulty)

const getDifficultyText = (difficulty: number | null) => {
  if (difficulty === null) return '未知'
  const levels: Record<number, string> = { 1: '入门', 2: '基础', 3: '进阶', 4: '困难', 5: '专家' }
  return levels[difficulty] || '未知'
}

/* ------------------------------- 加载 ------------------------------- */

const isPageLoaded = ref(false)
const isContentVisible = ref(false)

const applySeed = (next: PresentationCourseSeed | undefined) => {
  if (!next || next === seed.value) return false
  seed.value = next
  activeVideoFile.value = next.videoFile ?? ''
  videoSize.value = null
  if (next.videoFile) void probeSize(next.videoFile)
  playlist.value.forEach((item) => probeDuration(item.file))
  return true
}

const loadCourse = async (rawId: unknown) => {
  const courseId = Number(rawId)
  errorMessage.value = ''
  seed.value = undefined
  activeVideoFile.value = ''
  videoSize.value = null

  if (!Number.isFinite(courseId)) {
    errorMessage.value = '课程编号无效。'
    return
  }

  // 乐观渲染：先用手上已有的数据把页面立刻渲染出来，不等网络
  applySeed(resolvePresentationCourse(courseId, remoteCourseList.value))
  ensureCourseCatalog()

  isPageLoaded.value = true
  isContentVisible.value = false
  setTimeout(() => {
    isContentVisible.value = true
  }, 100)

  // 只有本地种子里查不到这个 id 时才值得等远端（比如后台新加了一门课）
  if (!seed.value) {
    await awaitCourseCatalog()
    if (Number(route.params.id) !== courseId) return
    if (!applySeed(resolvePresentationCourse(courseId, remoteCourseList.value))) {
      errorMessage.value = `没有找到编号为 ${courseId} 的课程。`
    }
  }
}

watch(() => route.params.id, loadCourse, { immediate: true })

// 远端数据晚到时校准一次：id→课名的映射可能和本地种子不同
watch(remoteCourseList, (list) => {
  if (!list.length || errorMessage.value) return
  const courseId = Number(route.params.id)
  if (!Number.isFinite(courseId)) return
  applySeed(resolvePresentationCourse(courseId, list))
})
</script>

<template>
  <div class="container-fluid px-4 py-6 overflow-x-hidden" :class="{ 'fade-in': isPageLoaded }">
    <div class="mb-4 slide-in-top">
      <button @click="router.go(-1)" class="btn btn-sm btn-ghost gap-2 hover:bg-base-200">
        <i class="fas fa-arrow-left"></i>
        <span>返回</span>
      </button>
    </div>

    <div v-if="errorMessage" class="alert alert-error">
      <i class="fas fa-exclamation-circle"></i>
      <span>{{ errorMessage }}</span>
      <button class="btn btn-sm" @click="router.push('/user/courses')">返回课程列表</button>
    </div>

    <!-- 只有本地目录里没有这个 id 时才会短暂出现（等远端确认） -->
    <div v-else-if="!seed" class="flex justify-center py-20">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <template v-else>
      <!-- 页面顶部：课程标题和状态 -->
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8 slide-in-top">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
            <i class="fas fa-graduation-cap text-2xl text-primary"></i>
          </div>
          <div>
            <h1 class="text-3xl font-bold hover:scale-[1.02] transition-transform">{{ courseName }}</h1>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <div v-if="catalogSource === 'local'" class="badge badge-warning badge-outline gap-1" title="课程服务未连接，内容来自前端内置目录">
            <i class="fas fa-plug text-xs"></i>
            内置目录
          </div>
          <div class="badge badge-lg badge-success py-3 px-4 gap-2 transition-all">
            <span class="w-2 h-2 rounded-full bg-current"></span>
            <span class="font-medium">进行中</span>
          </div>
          <button class="btn btn-primary btn-sm gap-2 hidden md:flex">
            <i class="fas fa-bookmark"></i>
            收藏课程
          </button>
        </div>
      </div>

      <!-- 课程信息卡片 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <!-- 左侧：课程简介 -->
        <div class="lg:col-span-1">
          <div
            class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all duration-300 h-full"
            :class="{ 'slide-in-left': isContentVisible }"
          >
            <div class="card-body">
              <div class="mb-4">
                <div class="flex items-center gap-3 mb-3">
                  <div class="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <i class="fas fa-info-circle text-xl text-primary"></i>
                  </div>
                  <h2 class="text-xl font-semibold">课程简介</h2>
                </div>
                <div class="pl-2 space-y-2 text-base-content/80 text-sm">
                  <p class="whitespace-pre-line leading-relaxed">{{ courseDescription }}</p>
                </div>
              </div>

              <div v-if="courseTags.length" class="mb-4">
                <div class="flex items-center gap-2 mb-3">
                  <i class="fas fa-tags text-primary"></i>
                  <h3 class="font-medium">课程标签</h3>
                </div>
                <div class="flex flex-wrap gap-2 pl-2">
                  <span v-for="tag in courseTags" :key="tag" class="badge badge-outline">{{ tag }}</span>
                </div>
              </div>

              <div class="grid grid-cols-1 gap-2 mb-4">
                <div v-if="seed?.instructor" class="flex items-center gap-2">
                  <i class="fas fa-chalkboard-teacher w-5 text-center text-primary"></i>
                  <span class="text-sm">讲师：{{ seed.instructor }}</span>
                </div>
                <div v-if="courseDifficulty" class="flex items-center gap-2">
                  <i class="fas fa-signal w-5 text-center text-primary"></i>
                  <span class="text-sm">
                    难度：
                    <span class="text-warning">{{ getDifficultyStars(courseDifficulty) }}</span>
                    ({{ getDifficultyText(courseDifficulty) }})
                  </span>
                </div>
                <div v-if="seed?.costTime" class="flex items-center gap-2">
                  <i class="fas fa-clock w-5 text-center text-primary"></i>
                  <span class="text-sm">课时：{{ seed.costTime }}</span>
                </div>
                <div v-if="courseCategory" class="flex items-center gap-2">
                  <i class="fas fa-bookmark w-5 text-center text-primary"></i>
                  <span class="text-sm">类型：{{ courseCategory }}</span>
                </div>
                <div v-if="seed?.schedule" class="flex items-center gap-2">
                  <i class="fas fa-calendar-alt w-5 text-center text-primary"></i>
                  <span class="text-sm">课程安排：{{ seed.schedule }}</span>
                </div>
              </div>

              <!-- 课程资源 -->
              <div class="mb-4">
                <div class="flex items-center gap-2 mb-3">
                  <i class="fas fa-download text-primary"></i>
                  <h3 class="font-medium">课程资源</h3>
                </div>
                <div class="space-y-2 pl-2">
                  <component
                    :is="resource.href ? 'a' : 'button'"
                    v-for="resource in courseResources"
                    :key="resource.key"
                    :href="resource.href"
                    :download="resource.download"
                    :type="resource.href ? undefined : 'button'"
                    class="w-full bg-base-200 p-2 rounded-lg flex justify-between items-center gap-2 hover:bg-base-300 transition-colors text-left"
                    @click="onResourceClick(resource)"
                  >
                    <div class="flex items-center gap-2 min-w-0">
                      <i :class="`fas fa-${resource.icon} text-primary w-4 text-center`"></i>
                      <span class="text-sm truncate">{{ resource.name }}</span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <span v-if="resource.size" class="text-xs text-base-content/60">{{ resource.size }}</span>
                      <span class="btn btn-xs btn-ghost btn-circle">
                        <i class="fas fa-download text-xs"></i>
                      </span>
                    </div>
                  </component>
                </div>
              </div>

              <!-- 学习目标 -->
              <div v-if="learning?.objectives.length" class="mb-4">
                <div class="flex items-center gap-2 mb-3">
                  <i class="fas fa-bullseye text-primary"></i>
                  <h3 class="font-medium">学习目标</h3>
                </div>
                <ul class="space-y-2 pl-2">
                  <li
                    v-for="(objective, index) in learning.objectives"
                    :key="index"
                    class="flex items-start gap-2 text-sm text-base-content/80"
                  >
                    <i class="fas fa-check-circle text-success text-xs mt-1 shrink-0"></i>
                    <span class="leading-relaxed">{{ objective }}</span>
                  </li>
                </ul>
              </div>

              <!-- 前置知识 -->
              <div v-if="learning?.prerequisites.length" class="mb-4">
                <div class="flex items-center gap-2 mb-3">
                  <i class="fas fa-book-reader text-primary"></i>
                  <h3 class="font-medium">前置知识</h3>
                </div>
                <div class="space-y-2 pl-2">
                  <div
                    v-for="(item, index) in learning.prerequisites"
                    :key="index"
                    class="flex items-start gap-2 text-sm text-base-content/70"
                  >
                    <i class="fas fa-angle-right text-primary text-xs mt-1 shrink-0"></i>
                    <span class="leading-relaxed">{{ item }}</span>
                  </div>
                </div>
              </div>

              <div class="mt-auto pt-2">
                <div class="flex items-center justify-between mb-2">
                  <span class="text-sm font-medium">学习进度</span>
                  <span class="text-sm font-bold text-primary">{{ learningProgress }}%</span>
                </div>
                <div class="w-full bg-base-200 rounded-full h-2.5">
                  <div class="bg-primary h-2.5 rounded-full" :style="{ width: `${learningProgress}%` }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：视频区域 -->
        <div class="lg:col-span-2">
          <div
            class="card bg-base-100 shadow-xl hover:shadow-2xl transition-all duration-300 h-full"
            :class="{ 'slide-in-right': isContentVisible }"
          >
            <div class="card-body p-4">
              <div class="flex items-center gap-2 mb-3">
                <i class="fas fa-video text-xl text-primary"></i>
                <h2 class="text-xl font-semibold">课程视频</h2>
                <span v-if="seed?.videoChapter" class="badge badge-primary badge-sm ml-2">{{ seed.videoChapter }}</span>
              </div>

              <div class="bg-base-200 rounded-xl overflow-hidden shadow-lg">
                <div class="aspect-video w-full bg-black">
                  <!-- ⑧ 不设 poster：靠 src 上的 #t=0.1 让浏览器解出视频首帧当封面，
                       封面永远跟着视频走，换视频不用另外维护封面图 -->
                  <video
                    v-if="activeVideoSrc"
                    :key="activeVideoSrc"
                    class="w-full h-full"
                    controls
                    preload="metadata"
                  >
                    <source :src="playerSrc" type="video/mp4" />
                    您的浏览器不支持 HTML5 视频播放。
                  </video>
                  <div v-else class="w-full h-full flex items-center justify-center bg-base-300">
                    <div class="text-center p-6">
                      <i class="fas fa-video-slash text-4xl text-base-content/50 mb-3"></i>
                      <p class="text-base-content/70">
                        {{ playlist.length ? '本课程暂无主讲视频，可从下方选集中选择章节视频观看' : '该课程暂无视频' }}
                      </p>
                    </div>
                  </div>
                </div>

                <div v-if="activeVideo" class="p-4">
                  <h3 class="font-medium text-lg mb-2">{{ courseName }} - {{ activeVideo.title }}</h3>
                  <div class="flex items-center gap-3 text-sm text-base-content/80 mb-3">
                    <span><i class="fas fa-clock mr-1"></i> {{ formatDuration(durations[activeVideo.file]) }}</span>
                    <span v-if="videoSize"><i class="fas fa-hdd mr-1"></i> {{ formatSize(videoSize) }}</span>
                  </div>
                  <p class="text-sm text-base-content/70">{{ activeVideo.description }}</p>
                </div>
              </div>

              <!-- 视频选集：同章节的真实视频，点哪个播哪个 -->
              <div class="mt-5 mb-3">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2">
                    <i class="fas fa-list text-primary"></i>
                    <h3 class="font-medium text-lg">视频选集</h3>
                  </div>
                  <span class="badge badge-sm">{{ playlist.length ? `${playlist.length}个视频` : '暂无视频' }}</span>
                </div>

                <div v-if="playlist.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  <button
                    v-for="video in playlist"
                    :key="video.file"
                    type="button"
                    class="text-left bg-base-200 p-3 rounded-lg cursor-pointer hover:bg-base-300 transition-colors"
                    :class="video.file === activeVideoFile ? 'border-l-4 border-primary' : ''"
                    @click="selectVideo(video.file)"
                  >
                    <div class="flex items-center gap-2 mb-2">
                      <div
                        class="w-10 h-10 shrink-0 rounded-lg flex items-center justify-center"
                        :class="video.file === activeVideoFile ? 'bg-primary/20' : 'bg-base-300'"
                      >
                        <i
                          class="fas fa-play-circle"
                          :class="video.file === activeVideoFile ? 'text-primary' : 'text-base-content/60'"
                        ></i>
                      </div>
                      <div class="min-w-0">
                        <h4 class="font-medium truncate">{{ video.title }}</h4>
                        <span class="text-xs text-base-content/60">{{ formatDuration(durations[video.file]) }}</span>
                      </div>
                    </div>
                    <p class="text-xs text-base-content/70 line-clamp-2">{{ video.description }}</p>
                  </button>
                </div>
                <div v-else class="bg-base-200 p-6 rounded-lg text-center">
                  <i class="fas fa-film text-4xl text-base-content/30 mb-3"></i>
                  <p class="text-base-content/70">该课程暂无视频选集</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 模块列表 -->
      <div
        class="card bg-base-100 shadow-xl hover:shadow-2xl transition-shadow duration-300"
        :class="{ 'slide-in-right': isContentVisible }"
      >
        <div class="card-body">
          <div class="flex items-center gap-2 mb-4">
            <i class="fas fa-flask text-xl text-primary"></i>
            <h2 class="text-xl font-semibold">课程模块</h2>
            <span class="badge badge-primary">{{ modules.length }}个</span>
          </div>

          <div class="grid gap-4">
            <div
              v-for="(module, index) in modules"
              :key="module.id"
              class="card bg-base-200 hover:bg-base-300 transition-all duration-200 fade-in-row"
              :style="{ animationDelay: `${index * 0.1}s` }"
            >
              <div class="card-body p-4">
                <div class="flex flex-col md:flex-row md:justify-between md:items-start gap-3">
                  <div class="space-y-2">
                    <h3 class="text-lg font-medium flex items-center gap-2 flex-wrap">
                      <i class="fas fa-terminal text-primary"></i>
                      {{ module.name }}
                      <span class="badge badge-sm" :class="index === 0 ? 'badge-accent' : ''">
                        {{ index === 0 ? '推荐开始' : `模块 ${index + 1}` }}
                      </span>
                      <span class="badge badge-sm" :class="module.labId ? 'badge-success' : 'badge-outline'">
                        {{ module.labId ? '含实验环境' : '理论模块' }}
                      </span>
                    </h3>
                    <p class="text-sm text-base-content/70 leading-relaxed">{{ module.introduction }}</p>
                    <div class="flex items-center gap-4 text-sm flex-wrap">
                      <div v-if="module.type.length" class="flex items-center gap-1">
                        <i class="fas fa-bookmark text-primary"></i>
                        <span>{{ module.type.join(', ') }}</span>
                      </div>
                      <div class="flex items-center gap-1" :title="getDifficultyText(module.difficulty)">
                        <i class="fas fa-signal text-primary"></i>
                        <span class="text-warning">{{ getDifficultyStars(module.difficulty) }}</span>
                      </div>
                      <div v-if="findPresentationLab(module.labId)" class="flex items-center gap-1">
                        <i class="fas fa-clock text-primary"></i>
                        <span>预计 {{ findPresentationLab(module.labId)?.estimatedTime }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="flex flex-col gap-2 md:items-end shrink-0">
                    <!-- 只有真实挂了实验环境的模块才给跳转，否则会跳进完全不相干的实验 -->
                    <button
                      v-if="module.labId"
                      @click="goToLab(module.labId)"
                      class="btn btn-primary btn-sm gap-2 hover:scale-105 transition-transform duration-200"
                    >
                      <i class="fas fa-arrow-right text-sm"></i>
                      进入实验
                    </button>
                    <div v-else class="tooltip tooltip-left" data-tip="本模块为理论内容，暂未配套实验环境">
                      <button class="btn btn-sm btn-outline gap-2" disabled>
                        <i class="fas fa-book text-sm"></i>
                        理论学习
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="!modules.length" class="text-center py-8 text-base-content/60">
              <i class="fas fa-layer-group text-4xl mb-3 block text-base-content/30"></i>
              该课程暂未拆分模块
            </div>
          </div>

          <div class="divider my-8">
            <div class="flex items-center gap-2">
              <i class="fas fa-fire-alt text-warning"></i>
              <span class="text-lg">实战实验推荐</span>
            </div>
          </div>

          <div class="bg-gradient-to-r from-primary/5 to-secondary/5 p-4 rounded-lg mb-6 border border-primary/20">
            <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <i class="fas fa-flask text-primary"></i>
                <h3 class="font-medium text-lg">{{ courseName }} 相关实验</h3>
                <span v-if="relatedLabs.length" class="badge badge-sm badge-primary">可直接跳转</span>
              </div>
              <button class="btn btn-sm btn-outline btn-primary" @click="router.push('/user/modules')">
                <i class="fas fa-th-list mr-1"></i>
                查看全部
              </button>
            </div>

            <template v-if="relatedLabs.length">
              <p class="text-sm text-base-content/70 mb-3">
                以下是与《{{ courseName }}》配套的实战实验，点击即可直接进入实验环境
              </p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                <div
                  v-for="lab in relatedLabs"
                  :key="lab.id"
                  class="card bg-base-200/90 hover:bg-base-200 transition-all duration-300 hover:shadow-md border-l-4"
                  :class="{
                    'border-error': lab.difficulty >= 4,
                    'border-warning': lab.difficulty === 3,
                    'border-success': lab.difficulty <= 2,
                  }"
                >
                  <div class="card-body p-3">
                    <div class="flex items-center justify-between gap-3">
                      <div class="min-w-0">
                        <h4 class="font-medium truncate">{{ lab.name }}</h4>
                        <div class="flex items-center gap-2 mt-1 flex-wrap">
                          <span class="text-xs text-base-content/60">
                            <i class="fas fa-signal mr-1"></i>
                            {{ getDifficultyText(lab.difficulty) }}
                          </span>
                          <span class="text-xs text-base-content/60">
                            <i class="fas fa-clock mr-1"></i>
                            {{ lab.estimatedTime }}
                          </span>
                        </div>
                      </div>
                      <button @click="goToLab(lab.id)" class="btn btn-xs btn-primary shrink-0">开始实验</button>
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <div v-else class="text-sm text-base-content/70 py-2">
              <i class="fas fa-info-circle mr-1 text-primary"></i>
              本课程以理论讲授为主，平台暂未为它配套实验环境。你可以先到
              <button class="link link-primary" @click="router.push('/user/modules')">实验列表</button>
              里选择其它已开放的实验。
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.container-fluid {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

/* 基础淡入动画 */
.fade-in {
  animation: fadeIn 0.5s ease-out;
}

/* 从左滑入动画 */
.slide-in-left {
  animation: slideInLeft 0.5s ease-out;
}

/* 从右滑入动画 */
.slide-in-right {
  animation: slideInRight 0.5s ease-out;
}

/* 表格行淡入动画 */
.fade-in-row {
  opacity: 0;
  animation: fadeIn 0.5s ease-out forwards;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 从顶部滑入 */
.slide-in-top {
  animation: slideInTop 0.7s ease-out;
}

@keyframes slideInTop {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes slideInLeft {
  from {
    transform: translateX(-20px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideInRight {
  from {
    transform: translateX(20px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 调整卡片过渡效果 */
.card {
  transition: all 0.3s ease;
}
</style>
