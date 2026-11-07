<script setup lang="ts">
import {
  AlertTriangle,
  Download,
  History,
  LoaderCircle,
  RotateCcw,
  ScanSearch,
} from 'lucide-vue-next'
import { computed } from 'vue'

import type { VersionSummary } from '@/api/types'

const props = defineProps<{
  versions: VersionSummary[]
  loading: boolean
  error: string | null
  restoringNumber: number | null
  exporting: boolean
}>()

const emit = defineEmits<{
  refresh: []
  diff: [fromVersion: number, toVersion: number]
  restore: [number: number]
  export: [number: number]
}>()

const sourceLabels: Record<string, string> = {
  agent: 'Agent 生成',
  restore: '版本回滚',
}

const sorted = computed(() => [...props.versions].sort((a, b) => b.number - a.number))

function sourceLabel(source: string): string {
  return sourceLabels[source] ?? source
}

function displayTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function fileMeta(version: VersionSummary): string {
  const kilobytes = version.total_bytes / 1024
  const size = kilobytes >= 1 ? `${kilobytes.toFixed(1)} KB` : `${version.total_bytes} B`
  return `${version.file_count} 个文件 · ${size}`
}

function diffFrom(index: number): number {
  return sorted.value[index + 1]?.number ?? 0
}
</script>

<template>
  <section
    class="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
  >
    <div class="flex items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
      <History class="size-4 text-slate-500" />
      <h2 class="text-xs font-semibold text-slate-900 dark:text-white">版本历史</h2>
      <span class="ml-auto text-[11px] text-slate-400">{{ versions.length }}</span>
    </div>

    <div v-if="loading" class="grid flex-1 place-items-center px-4 py-10">
      <div class="text-center">
        <LoaderCircle class="mx-auto size-5 animate-spin text-indigo-500" />
        <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">正在加载版本…</p>
      </div>
    </div>

    <div v-else-if="error" class="px-4 py-8 text-center">
      <AlertTriangle class="mx-auto size-6 text-rose-400" />
      <p class="mt-2 text-xs leading-5 text-rose-700 dark:text-rose-300">{{ error }}</p>
      <button
        type="button"
        class="mt-3 inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-600 dark:border-slate-700 dark:text-slate-300"
        @click="emit('refresh')"
      >
        <LoaderCircle class="size-3" />
        重试
      </button>
    </div>

    <div v-else-if="versions.length === 0" class="px-4 py-10 text-center">
      <History class="mx-auto size-7 text-slate-300 dark:text-slate-600" />
      <p class="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
        还没有版本。Agent 首次生成或保存编辑后会在这里留下快照。
      </p>
    </div>

    <ul v-else class="min-h-0 flex-1 space-y-2 overflow-y-auto px-2 py-2">
      <li
        v-for="(version, index) in sorted"
        :key="version.number"
        class="rounded-xl border px-3 py-2.5"
        :class="version.is_current
          ? 'border-indigo-200 bg-indigo-50/60 dark:border-indigo-500/30 dark:bg-indigo-500/10'
          : 'border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950/30'"
      >
        <div class="flex items-center gap-2">
          <span class="font-mono text-xs font-semibold text-slate-900 dark:text-white">
            v{{ version.number }}
          </span>
          <span
            v-if="version.is_current"
            class="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
          >
            当前
          </span>
          <span class="ml-auto text-[10px] text-slate-400">{{ displayTime(version.created_at) }}</span>
        </div>
        <p class="mt-1 truncate text-[11px] text-slate-600 dark:text-slate-300">
          {{ version.label || sourceLabel(version.source) }}
        </p>
        <p class="mt-0.5 text-[10px] text-slate-400">
          {{ sourceLabel(version.source) }} · {{ fileMeta(version) }}
        </p>

        <div class="mt-2 flex flex-wrap items-center gap-1">
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            @click="emit('diff', diffFrom(index), version.number)"
          >
            <ScanSearch class="size-3" />
            查看变更
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
            :disabled="version.is_current || restoringNumber !== null"
            @click="emit('restore', version.number)"
          >
            <LoaderCircle v-if="restoringNumber === version.number" class="size-3 animate-spin" />
            <RotateCcw v-else class="size-3" />
            回滚
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
            :disabled="exporting"
            @click="emit('export', version.number)"
          >
            <Download class="size-3" />
            导出
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>
