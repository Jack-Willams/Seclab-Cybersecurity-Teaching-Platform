import { computed, readonly, ref } from 'vue'
import { getApiErrorMessage, getCourseList, type CourseSummaryDto } from '../api'
import { mergeCourseSummariesWithPresentation } from '../mock/catalogPresentation'

/**
 * 课程目录的会话级单例。
 *
 * 为什么要单独开一个文件：`<script setup>` 顶层的代码是**每个组件实例执行一次**的，
 * 写在里面的 `let cache = null` 根本不是模块级缓存，每次挂载都会重新请求。
 * 只有放在普通 .ts 模块里（ES 模块天然是单例）才真的只拉一次。
 *
 * 三件事：
 * 1. 乐观渲染 —— 页面永远先拿本地种子数据渲染，不等网络，首屏 0ms；
 * 2. 会话级缓存 + 并发去重 —— 远端成功一次后本会话不再请求，多个页面同时挂载也只发一个请求；
 * 3. 熔断 —— 失败后 60s 内不再碰 8084。本机连一个没监听的端口要 ~2s 才超时（SYN 被静默丢弃，
 *    不是立刻 RST），不熔断的话每进一个课程页都要白等 2.3s。
 */

/** 熔断冷却时间：失败后这段时间内直接用本地数据，不再发请求 */
const CIRCUIT_COOLDOWN_MS = 60_000
/** 单次请求的等待上限。超时只是「不再等」，请求本身还在跑，晚到的数据仍会被采纳 */
const REQUEST_TIMEOUT_MS = 4_000

const remoteCourses = ref<CourseSummaryDto[] | null>(null)
const isRefreshing = ref(false)
const lastError = ref('')

let inflight: Promise<CourseSummaryDto[] | null> | null = null
let circuitOpenUntil = 0

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

/** 本地种子 + 远端数据合并后的课程目录。远端没回来时就是纯本地种子 */
export const courseCatalog = computed(() => mergeCourseSummariesWithPresentation(remoteCourses.value ?? []))

/** 数据来源，用来在界面上如实标注「当前是本地目录」 */
export const catalogSource = computed<'remote' | 'local'>(() => (remoteCourses.value ? 'remote' : 'local'))

export const isCatalogRefreshing = readonly(isRefreshing)
export const catalogError = readonly(lastError)

const fetchRemote = (): Promise<CourseSummaryDto[] | null> => {
  if (inflight) return inflight

  isRefreshing.value = true
  inflight = getCourseList()
    .then((response) => {
      const data = response?.data ?? []
      if (!data.length) throw new Error('课程服务返回了空列表')
      remoteCourses.value = data
      circuitOpenUntil = 0
      lastError.value = ''
      return data
    })
    .catch((error) => {
      // 打开熔断：接下来 60s 直接走本地，不再为一个连不上的端口付超时
      circuitOpenUntil = Date.now() + CIRCUIT_COOLDOWN_MS
      lastError.value = getApiErrorMessage(error, '课程服务暂时连不上')
      console.warn('课程列表接口不可用，使用本地课程目录:', error)
      return null
    })
    .finally(() => {
      isRefreshing.value = false
      inflight = null
    })

  return inflight
}

/**
 * 触发一次后台刷新，**不阻塞渲染**。
 * 已有远端数据 / 熔断未冷却 / 已有请求在飞 —— 三种情况都不会重复发起。
 */
export const ensureCourseCatalog = (): void => {
  if (remoteCourses.value || inflight) return
  if (Date.now() < circuitOpenUntil) return
  void fetchRemote()
}

/**
 * 需要远端数据才能判断的场景（比如详情页在本地种子里查不到这个 id）才用它。
 * 最多等 REQUEST_TIMEOUT_MS，等不到就让调用方按本地数据继续。
 */
export const awaitCourseCatalog = async (): Promise<void> => {
  if (remoteCourses.value) return
  if (!inflight && Date.now() < circuitOpenUntil) return
  const pending = inflight ?? fetchRemote()
  await Promise.race([pending, sleep(REQUEST_TIMEOUT_MS)])
}

/** 用户手动重试：无视熔断冷却 */
export const refreshCourseCatalog = async (): Promise<void> => {
  circuitOpenUntil = 0
  await (inflight ?? fetchRemote())
}

/** 远端课程原始列表，详情页用它把路由上的 id 换成课程名 */
export const remoteCourseList = computed(() => remoteCourses.value ?? [])
