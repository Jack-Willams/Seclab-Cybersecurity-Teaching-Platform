import { ref } from 'vue'

export type ThemeName = 'light' | 'night'

const STORAGE_KEY = 'seclab-theme'
const DEFAULT_THEME: ThemeName = 'light'

const currentTheme = ref<ThemeName>(DEFAULT_THEME)

function applyTheme(theme: ThemeName) {
  document.documentElement.setAttribute('data-theme', theme)
}

function setTheme(theme: ThemeName) {
  currentTheme.value = theme
  applyTheme(theme)
  try {
    localStorage.setItem(STORAGE_KEY, theme)
  } catch {
    // localStorage 不可用（隐私模式等）时静默忽略，主题仍能在当前会话生效
  }
}

function toggleTheme() {
  setTheme(currentTheme.value === 'night' ? 'light' : 'night')
}

export function initThemeFromStorage() {
  let stored: ThemeName | null = null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === 'light' || raw === 'night') {
      stored = raw
    }
  } catch {
    stored = null
  }
  setTheme(stored ?? DEFAULT_THEME)
}

export function useTheme() {
  return {
    currentTheme,
    setTheme,
    toggleTheme,
  }
}
