<script setup lang="ts">
import { Clock3, Download, LoaderCircle, Share2, Sparkles } from 'lucide-vue-next'

defineProps<{
  title: string
  prompt: string
  version: number | null
  updatedLabel: string
  exporting: boolean
}>()

const emit = defineEmits<{
  export: []
  share: []
}>()

const onExport = () => emit('export')
const onShare = () => emit('share')
</script>

<template>
  <div>
    <header class="mt-6 flex flex-wrap items-start justify-between gap-4">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h1 class="truncate text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
            {{ title }}
          </h1>
          <span
            v-if="version !== null"
            class="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
          >
            v{{ version }}
          </span>
        </div>
        <p class="mt-2 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <Clock3 class="size-3.5" />
          更新于 {{ updatedLabel }}
        </p>
      </div>

      <div class="flex items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-slate-700 dark:hover:text-white"
          :disabled="version === null || exporting"
          @click="onExport"
        >
          <LoaderCircle v-if="exporting" class="size-3.5 animate-spin" />
          <Download v-else class="size-3.5" />
          导出 ZIP
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
          :disabled="version === null"
          @click="onShare"
        >
          <Share2 class="size-3.5" />
          分享
        </button>
      </div>
    </header>

    <section
      class="mt-6 rounded-2xl border border-indigo-200 bg-indigo-50/60 p-4 dark:border-indigo-500/30 dark:bg-indigo-500/10"
    >
      <div class="flex items-start gap-2">
        <Sparkles class="mt-0.5 size-4 shrink-0 text-indigo-600 dark:text-indigo-400" />
        <div>
          <p class="text-xs font-medium text-indigo-700 dark:text-indigo-300">应用描述</p>
          <p class="mt-1 text-sm leading-6 text-slate-700 dark:text-slate-300">{{ prompt }}</p>
        </div>
      </div>
    </section>
  </div>
</template>
