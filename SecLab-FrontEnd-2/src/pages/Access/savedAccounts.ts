// 登录页的「账号本」：把用过的账号连同密码存在本机，下次点一下就填好两个输入框。
//
// 明确一点：密码是明文存在 localStorage 里的，任何能打开这台机器浏览器控制台的人都能读到。
// 这是为本地演示/答辩场景做的取舍——演示账号密码统一是 123456，本来也没有保护价值。
// 真要上线给真实用户用，这个文件应该整个删掉，或者退化成只存学号不存密码。
import type { AuthRole } from '../../auth'

const STORAGE_KEY = 'seclab_login_accounts'
const MAX_ACCOUNTS = 8

export type SavedAccount = {
  studentNumber: string
  password: string
  /** 登录成功后回填的真实姓名，纯粹为了下拉里能认出是谁 */
  displayName: string
  role: AuthRole | null
  lastUsedAt: number
  /** 预置账号：代码里写死的，清了浏览器缓存也还在 */
  preset: boolean
}

type StoredShape = {
  accounts: Omit<SavedAccount, 'preset'>[]
  /** 被手动删掉的预置账号，记下来免得下次刷新又冒出来 */
  dismissedPresets: string[]
}

// 答辩兜底：即使换台机器、换个浏览器、清了缓存，这两个也一定在下拉里。
const PRESET_ACCOUNTS: SavedAccount[] = [
  {
    studentNumber: 'admin',
    password: '123456',
    displayName: 'Administrator',
    role: 'teacher',
    lastUsedAt: 0,
    preset: true,
  },
  {
    studentNumber: '202321040517',
    password: '123456',
    displayName: '学生演示账号',
    role: 'student',
    lastUsedAt: 0,
    preset: true,
  },
]

function readStore(): StoredShape {
  const empty: StoredShape = { accounts: [], dismissedPresets: [] }
  if (typeof window === 'undefined') return empty

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return empty

    const parsed = JSON.parse(raw) as Partial<StoredShape> | null
    if (!parsed || typeof parsed !== 'object') return empty

    return {
      accounts: Array.isArray(parsed.accounts)
        ? parsed.accounts.filter((item) => item && typeof item.studentNumber === 'string' && item.studentNumber)
        : [],
      dismissedPresets: Array.isArray(parsed.dismissedPresets)
        ? parsed.dismissedPresets.filter((item): item is string => typeof item === 'string')
        : [],
    }
  } catch {
    // 存的内容坏了就当没存过，别让登录页因为一条脏数据白屏
    return empty
  }
}

function writeStore(store: StoredShape) {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {
    // 隐私模式 / 存储写满，静默忽略，登录本身不受影响
  }
}

/** 历史记录在前（最近用过的排最前），没用过的预置账号垫底 */
export function loadSavedAccounts(): SavedAccount[] {
  const store = readStore()
  const history = store.accounts
    .map((item) => ({ ...item, preset: false }))
    .sort((a, b) => b.lastUsedAt - a.lastUsedAt)

  const seen = new Set(history.map((item) => item.studentNumber))
  const presets = PRESET_ACCOUNTS.filter(
    (item) => !seen.has(item.studentNumber) && !store.dismissedPresets.includes(item.studentNumber),
  )

  return [...history, ...presets]
}

/** 登录成功后调用。同一个学号只留一条，密码以最新一次为准。 */
export function rememberAccount(input: {
  studentNumber: string
  password: string
  displayName?: string | null
  role?: AuthRole | null
}) {
  const studentNumber = input.studentNumber.trim()
  if (!studentNumber || !input.password) return

  const store = readStore()
  const previous = store.accounts.find((item) => item.studentNumber === studentNumber)
  const rest = store.accounts.filter((item) => item.studentNumber !== studentNumber)

  const entry = {
    studentNumber,
    password: input.password,
    displayName: input.displayName?.trim() || previous?.displayName || '',
    role: input.role ?? previous?.role ?? null,
    lastUsedAt: Date.now(),
  }

  writeStore({
    accounts: [entry, ...rest].slice(0, MAX_ACCOUNTS),
    // 手动删过的预置账号，如果又主动登录了一次，就当它回来了
    dismissedPresets: store.dismissedPresets.filter((item) => item !== studentNumber),
  })
}

export function forgetAccount(studentNumber: string) {
  const store = readStore()
  const isPreset = PRESET_ACCOUNTS.some((item) => item.studentNumber === studentNumber)

  writeStore({
    accounts: store.accounts.filter((item) => item.studentNumber !== studentNumber),
    dismissedPresets: isPreset && !store.dismissedPresets.includes(studentNumber)
      ? [...store.dismissedPresets, studentNumber]
      : store.dismissedPresets,
  })
}

/** 清空历史，并把预置账号也一起隐藏——「忘记全部」应该是真的全空 */
export function clearSavedAccounts() {
  writeStore({
    accounts: [],
    dismissedPresets: PRESET_ACCOUNTS.map((item) => item.studentNumber),
  })
}
