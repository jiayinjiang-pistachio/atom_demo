import { defineStore } from 'pinia'
import { ref } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'atom.theme'

function readInitialTheme(): Theme {
  if (typeof window === 'undefined') {
    return 'light'
  }
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') {
    return stored
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.style.colorScheme = theme
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(readInitialTheme())

  function toggle(): void {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    window.localStorage.setItem(STORAGE_KEY, theme.value)
    applyTheme(theme.value)
  }

  applyTheme(theme.value)

  return { theme, toggle }
})
