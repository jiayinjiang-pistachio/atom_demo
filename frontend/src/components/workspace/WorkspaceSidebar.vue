<script setup lang="ts">
import { Files, History } from 'lucide-vue-next'
import { ref } from 'vue'

import type { ProjectFile, VersionSummary } from '@/api/types'
import FilePanel from '@/components/workspace/FilePanel.vue'
import VersionPanel from '@/components/workspace/VersionPanel.vue'

defineProps<{
  files: ProjectFile[]
  selectedPath: string | null
  versions: VersionSummary[]
  versionsLoading: boolean
  versionError: string | null
  restoringNumber: number | null
  exporting: boolean
}>()

const emit = defineEmits<{
  select: [path: string]
  refreshVersions: []
  diff: [fromVersion: number, toVersion: number]
  restore: [number: number]
  export: [number: number]
}>()

const leftTab = ref<'files' | 'versions'>('files')

const onSelect = (path: string) => emit('select', path)
const onRefreshVersions = () => emit('refreshVersions')
const onDiff = (fromVersion: number, toVersion: number) => emit('diff', fromVersion, toVersion)
const onRestore = (number: number) => emit('restore', number)
const onExport = (number: number) => emit('export', number)
</script>

<template>
  <div class="flex min-h-105 flex-col gap-2 lg:min-h-0">
    <div
      class="flex shrink-0 rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-800 dark:bg-slate-900"
    >
      <button
        type="button"
        class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] font-medium transition"
        :class="leftTab === 'files'
          ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'"
        :aria-pressed="leftTab === 'files'"
        @click="leftTab = 'files'"
      >
        <Files class="size-3.5" />
        文件
      </button>
      <button
        type="button"
        class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11px] font-medium transition"
        :class="leftTab === 'versions'
          ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'"
        :aria-pressed="leftTab === 'versions'"
        @click="leftTab = 'versions'"
      >
        <History class="size-3.5" />
        版本
      </button>
    </div>

    <div class="min-h-0 flex-1">
      <FilePanel
        v-if="leftTab === 'files'"
        :files="files"
        :selected-path="selectedPath"
        @select="onSelect"
      />
      <VersionPanel
        v-else
        :versions="versions"
        :loading="versionsLoading"
        :error="versionError"
        :restoring-number="restoringNumber"
        :exporting="exporting"
        @refresh="onRefreshVersions"
        @diff="onDiff"
        @restore="onRestore"
        @export="onExport"
      />
    </div>
  </div>
</template>
