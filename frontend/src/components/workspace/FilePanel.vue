<script setup lang="ts">
import { FileCode2, FileJson, FileText, FolderOpen } from 'lucide-vue-next'
import { computed } from 'vue'

import type { ProjectFile } from '@/api/types'

const props = defineProps<{
  files: ProjectFile[]
  selectedPath: string | null
}>()

const emit = defineEmits<{
  select: [path: string]
}>()

const selected = computed(
  () => props.files.find((file) => file.path === props.selectedPath) ?? props.files[0] ?? null,
)

function iconFor(path: string) {
  if (path.endsWith('.json')) {
    return FileJson
  }
  if (path.endsWith('.md') || path.endsWith('.txt')) {
    return FileText
  }
  return FileCode2
}

function formatSize(size: number): string {
  return size > 1024 ? `${(size / 1024).toFixed(1)} KB` : `${size} B`
}
</script>

<template>
  <aside
    class="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
  >
    <div class="flex items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
      <FileCode2 class="size-4 text-slate-500" />
      <h2 class="text-xs font-semibold text-slate-900 dark:text-white">文件</h2>
      <span class="ml-auto text-[11px] text-slate-400">{{ files.length }}</span>
    </div>

    <div v-if="files.length === 0" class="px-4 py-10 text-center">
      <FolderOpen class="mx-auto size-7 text-slate-300 dark:text-slate-600" />
      <p class="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">
        还没有文件。开始生成后，Agent 写入的每个文件都会实时出现在这里。
      </p>
    </div>

    <template v-else>
      <ul class="max-h-52 shrink-0 space-y-1 overflow-y-auto px-2 py-2">
        <li v-for="file in files" :key="file.path">
          <button
            type="button"
            class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left transition"
            :class="selected?.path === file.path
              ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300'
              : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60'"
            @click="emit('select', file.path)"
          >
            <component :is="iconFor(file.path)" class="size-3.5 shrink-0" />
            <span class="truncate font-mono text-[11px]">{{ file.path }}</span>
            <span class="ml-auto shrink-0 text-[10px] text-slate-400">
              {{ formatSize(file.size) }}
            </span>
          </button>
        </li>
      </ul>

      <div class="min-h-0 flex-1 border-t border-slate-100 dark:border-slate-800">
        <pre
          class="h-full min-h-40 overflow-auto whitespace-pre-wrap p-3 font-mono text-[11px] leading-5 text-slate-700 dark:text-slate-300"
        >{{ selected?.content ?? '' }}</pre>
      </div>
    </template>
  </aside>
</template>
