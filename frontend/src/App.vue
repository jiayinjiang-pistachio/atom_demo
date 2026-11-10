<script setup lang="ts">
import { Moon, Sparkles, Sun } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import { useThemeStore } from '@/stores/theme'

const route = useRoute()
const themeStore = useThemeStore()
const isShare = computed(() => route.name === 'share' || route.name === 'share-app')
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <header
      v-if="!isShare"
      class="sticky top-0 z-20 border-b border-slate-200/70 bg-white/80 backdrop-blur dark:border-slate-800/70 dark:bg-slate-950/80"
    >
      <div class="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-6">
        <RouterLink to="/" class="flex items-center gap-2.5">
          <span
            class="grid size-9 place-items-center rounded-xl bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
          >
            <Sparkles class="size-4" />
          </span>
          <span class="flex items-center gap-2 text-sm font-semibold tracking-tight sm:text-base">
            Pistachio Atom
            <span
              class="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-400"
            >
              M3
            </span>
          </span>
        </RouterLink>

        <button
          type="button"
          class="grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:border-slate-300 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400 dark:hover:border-slate-700 dark:hover:text-slate-100"
          :aria-label="themeStore.theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'"
          @click="themeStore.toggle()"
        >
          <Sun v-if="themeStore.theme === 'dark'" class="size-4" />
          <Moon v-else class="size-4" />
        </button>
      </div>
    </header>

    <RouterView class="flex-1" />

    <footer v-if="!isShare" class="border-t border-slate-200/70 py-6 dark:border-slate-800/70">
      <div
        class="mx-auto flex w-full max-w-6xl flex-col gap-2 px-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between dark:text-slate-400"
      >
        <span>© 2026 jiayinjiang-pistachio · 保留所有权利</span>
        <span>
          参考：
          <a
            href="https://atoms.dev/"
            target="_blank"
            rel="noopener noreferrer"
            class="underline decoration-slate-300 underline-offset-2 transition hover:text-slate-700 dark:decoration-slate-700 dark:hover:text-slate-200"
          >
            Atom
          </a>
        </span>
      </div>
    </footer>
  </div>
</template>
