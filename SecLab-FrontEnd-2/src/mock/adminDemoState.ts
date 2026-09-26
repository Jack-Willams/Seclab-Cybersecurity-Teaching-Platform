import type { Course } from '../types/course'
import type { Experiment } from '../types/experiment'
import type { User } from '../types/user'

type CourseDemoState = {
  deletedIds: number[]
  upserts: Course[]
}

type UserDemoState = {
  deletedIds: number[]
  upserts: User[]
}

type ExperimentDemoState = {
  deletedIds: number[]
  upserts: Experiment[]
}

const COURSE_DEMO_STORAGE_KEY = 'seclab-admin-demo-courses'
const USER_DEMO_STORAGE_KEY = 'seclab-admin-demo-users'
const EXPERIMENT_DEMO_STORAGE_KEY = 'seclab-admin-demo-experiments'

const emptyCourseDemoState = (): CourseDemoState => ({
  deletedIds: [],
  upserts: [],
})

const emptyUserDemoState = (): UserDemoState => ({
  deletedIds: [],
  upserts: [],
})

const emptyExperimentDemoState = (): ExperimentDemoState => ({
  deletedIds: [],
  upserts: [],
})

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

function readCourseDemoState(): CourseDemoState {
  if (!canUseStorage()) {
    return emptyCourseDemoState()
  }

  try {
    const raw = window.localStorage.getItem(COURSE_DEMO_STORAGE_KEY)
    if (!raw) {
      return emptyCourseDemoState()
    }

    const parsed = JSON.parse(raw) as Partial<CourseDemoState>
    return {
      deletedIds: Array.isArray(parsed.deletedIds) ? parsed.deletedIds.filter((id): id is number => typeof id === 'number') : [],
      upserts: Array.isArray(parsed.upserts) ? parsed.upserts as Course[] : [],
    }
  } catch (error) {
    console.warn('读取本地课程演示态失败，已忽略本地缓存:', error)
    return emptyCourseDemoState()
  }
}

function writeCourseDemoState(state: CourseDemoState) {
  if (!canUseStorage()) {
    return
  }

  window.localStorage.setItem(COURSE_DEMO_STORAGE_KEY, JSON.stringify(state))
}

function readUserDemoState(): UserDemoState {
  if (!canUseStorage()) {
    return emptyUserDemoState()
  }

  try {
    const raw = window.localStorage.getItem(USER_DEMO_STORAGE_KEY)
    if (!raw) {
      return emptyUserDemoState()
    }

    const parsed = JSON.parse(raw) as Partial<UserDemoState>
    return {
      deletedIds: Array.isArray(parsed.deletedIds) ? parsed.deletedIds.filter((id): id is number => typeof id === 'number') : [],
      upserts: Array.isArray(parsed.upserts) ? parsed.upserts as User[] : [],
    }
  } catch (error) {
    console.warn('读取本地用户演示态失败，已忽略本地缓存:', error)
    return emptyUserDemoState()
  }
}

function writeUserDemoState(state: UserDemoState) {
  if (!canUseStorage()) {
    return
  }

  window.localStorage.setItem(USER_DEMO_STORAGE_KEY, JSON.stringify(state))
}

function readExperimentDemoState(): ExperimentDemoState {
  if (!canUseStorage()) {
    return emptyExperimentDemoState()
  }

  try {
    const raw = window.localStorage.getItem(EXPERIMENT_DEMO_STORAGE_KEY)
    if (!raw) {
      return emptyExperimentDemoState()
    }

    const parsed = JSON.parse(raw) as Partial<ExperimentDemoState>
    return {
      deletedIds: Array.isArray(parsed.deletedIds) ? parsed.deletedIds.filter((id): id is number => typeof id === 'number') : [],
      upserts: Array.isArray(parsed.upserts) ? parsed.upserts as Experiment[] : [],
    }
  } catch (error) {
    console.warn('读取本地实验演示态失败，已忽略本地缓存:', error)
    return emptyExperimentDemoState()
  }
}

function writeExperimentDemoState(state: ExperimentDemoState) {
  if (!canUseStorage()) {
    return
  }

  window.localStorage.setItem(EXPERIMENT_DEMO_STORAGE_KEY, JSON.stringify(state))
}

export function mergeCoursesWithDemoState(baseCourses: Course[]) {
  const state = readCourseDemoState()
  const deletedIds = new Set(state.deletedIds)
  const mergedMap = new Map<number, Course>()

  baseCourses
    .filter((course) => !deletedIds.has(course.id))
    .forEach((course) => {
      mergedMap.set(course.id, { ...course })
    })

  state.upserts.forEach((course) => {
    if (!deletedIds.has(course.id)) {
      mergedMap.set(course.id, { ...course })
    }
  })

  return Array.from(mergedMap.values()).sort((a, b) => b.id - a.id)
}

export function upsertDemoCourse(course: Course) {
  const state = readCourseDemoState()
  const nextUpserts = state.upserts.filter((item) => item.id !== course.id)
  nextUpserts.push({ ...course })

  writeCourseDemoState({
    deletedIds: state.deletedIds.filter((id) => id !== course.id),
    upserts: nextUpserts,
  })
}

export function markDemoCourseDeleted(courseId: number) {
  const state = readCourseDemoState()
  writeCourseDemoState({
    deletedIds: Array.from(new Set([...state.deletedIds, courseId])),
    upserts: state.upserts.filter((course) => course.id !== courseId),
  })
}

export function mergeUsersWithDemoState(baseUsers: User[]) {
  const state = readUserDemoState()
  const deletedIds = new Set(state.deletedIds)
  const mergedMap = new Map<number, User>()

  baseUsers
    .filter((user) => !deletedIds.has(user.userId))
    .forEach((user) => {
      mergedMap.set(user.userId, { ...user })
    })

  state.upserts.forEach((user) => {
    if (!deletedIds.has(user.userId)) {
      mergedMap.set(user.userId, { ...user })
    }
  })

  return Array.from(mergedMap.values()).sort((a, b) => b.userId - a.userId)
}

export function upsertDemoUser(user: User) {
  const state = readUserDemoState()
  const nextUpserts = state.upserts.filter((item) => item.userId !== user.userId)
  nextUpserts.push({ ...user })

  writeUserDemoState({
    deletedIds: state.deletedIds.filter((id) => id !== user.userId),
    upserts: nextUpserts,
  })
}

export function markDemoUserDeleted(userId: number) {
  const state = readUserDemoState()
  writeUserDemoState({
    deletedIds: Array.from(new Set([...state.deletedIds, userId])),
    upserts: state.upserts.filter((user) => user.userId !== userId),
  })
}

export function mergeExperimentsWithDemoState(baseExperiments: Experiment[]) {
  const state = readExperimentDemoState()
  const deletedIds = new Set(state.deletedIds)
  const mergedMap = new Map<number, Experiment>()

  baseExperiments
    .filter((experiment) => !deletedIds.has(experiment.id))
    .forEach((experiment) => {
      mergedMap.set(experiment.id, { ...experiment })
    })

  state.upserts.forEach((experiment) => {
    if (!deletedIds.has(experiment.id)) {
      mergedMap.set(experiment.id, { ...experiment })
    }
  })

  return Array.from(mergedMap.values()).sort((a, b) => b.id - a.id)
}

export function upsertDemoExperiment(experiment: Experiment) {
  const state = readExperimentDemoState()
  const nextUpserts = state.upserts.filter((item) => item.id !== experiment.id)
  nextUpserts.push({ ...experiment })

  writeExperimentDemoState({
    deletedIds: state.deletedIds.filter((id) => id !== experiment.id),
    upserts: nextUpserts,
  })
}

export function markDemoExperimentDeleted(experimentId: number) {
  const state = readExperimentDemoState()
  writeExperimentDemoState({
    deletedIds: Array.from(new Set([...state.deletedIds, experimentId])),
    upserts: state.upserts.filter((experiment) => experiment.id !== experimentId),
  })
}
