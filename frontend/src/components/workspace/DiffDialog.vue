<script setup lang="ts">
import { AlertTriangle, LoaderCircle, X } from 'lucide-vue-next'
import { onBeforeUnmount, onMounted, watch } from 'vue'

import type { VersionChangeKind, VersionDiff } from '@/api/types'

const props = defineProps<{
  open: boolean
  diff: VersionDiff | null
  loading: boolean
  error: string | null
}>()

const emit = defineEmits<{
  close: []
  retry: []
}>()

const changeLabels: Record<VersionChangeKind, string> = {
  added: '新增',
  removed: '删除',
  modified: '修改',
}

const changeClasses: Record<VersionChangeKind, string> = {
  added: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400',
  removed: 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400',
  modified: 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400',
}

const changeLabel = (change: VersionChangeKind) => changeLabels[change]
const changeClass = (change: VersionChangeKind) => changeClasses[change]

function lineClass(line: string): string {
  if (line.startsWith('+++') || line.startsWith('---')) {
    return 'text-slate-400'
  }
  if (line.startsWith('@@')) {
    return 'text-indigo-500 dark:text-indigo-400'
  }
  if (line.startsWith('+')) {
    return 'bg-emerald-50/60 text-emerald-700 dark:bg-emerald-500/5 dark:text-emerald-300'
  }
  if (line.startsWith('-')) {
    return 'bg-rose-50/60 text-rose-700 dark:bg-rose-500/5 dark:text-rose-300'
  }
  return 'text-slate-600 dark:text-slate-300'
}

function onKeydown(event: KeyboardEvent): void {
  if (props.open && event.key === 'Escape') {
    emit('close')
  }
}

watch(
  () => props.open,
  (open) => {
    if (typeof document !== 'undefined') {
      document.body.classList.toggle('overflow-hidden', open)
    }
  },
)

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (typeof document !== 'undefined') {
    document.body.classList.remove('overflow-hidden')
  }
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-40 grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm"
      role="button"
      tabindex="0"
      aria-label="关闭版本对比"
      @click.self="emit('close')"
      @keydown.enter="emit('close')"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="diff-dialog-title"
        class="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900"
      >
        <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-3 dark:border-slate-800">
          <h2 id="diff-dialog-title" class="text-sm font-semibold text-slate-900 dark:text-white">
            版本对比
          </h2>
          <span v-if="diff" class="text-[11px] text-slate-400">
            v{{ diff.from_version }} → v{{ diff.to_version }}
          </span>
          <button
            type="button"
            class="ml-auto grid size-8 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="关闭"
            @click="emit('close')"
          >
            <X class="size-4" />
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          <div v-if="loading" class="grid place-items-center py-16">
            <div class="text-center">
              <LoaderCircle class="mx-auto size-6 animate-spin text-indigo-500" />
              <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">正在计算版本差异…</p>
            </div>
          </div>

          <div v-else-if="error" class="rounded-xl bg-rose-50 px-4 py-6 text-center dark:bg-rose-500/10">
            <AlertTriangle class="mx-auto size-6 text-rose-500" />
            <p class="mt-2 text-xs text-rose-700 dark:text-rose-300">{{ error }}</p>
            <button
              type="button"
              class="mt-3 rounded-lg border border-rose-300 px-3 py-1.5 text-[11px] font-medium text-rose-700 dark:border-rose-500/40 dark:text-rose-300"
              @click="emit('retry')"
            >
              重试
            </button>
          </div>

          <div
            v-else-if="diff && diff.files.length === 0"
            class="rounded-xl border border-dashed border-slate-300 px-4 py-10 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400"
          >
            两个版本的文件内容一致。
          </div>

          <template v-else-if="diff">
            <div class="flex flex-wrap gap-3 text-[11px] text-slate-500 dark:text-slate-400">
              <span>新增 {{ diff.summary.files_added }}</span>
              <span>删除 {{ diff.summary.files_removed }}</span>
              <span>修改 {{ diff.summary.files_modified }}</span>
              <span class="text-emerald-600 dark:text-emerald-400">
                +{{ diff.summary.additions }}
              </span>
              <span class="text-rose-600 dark:text-rose-400">-{{ diff.summary.deletions }}</span>
            </div>

            <div class="mt-3 space-y-3">
              <article
                v-for="file in diff.files"
                :key="file.path"
                class="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800"
              >
                <div class="flex flex-wrap items-center gap-2 bg-slate-50 px-3 py-2 dark:bg-slate-950/40">
                  <span class="font-mono text-[11px] text-slate-700 dark:text-slate-200">
                    {{ file.path }}
                  </span>
                  <span
                    class="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                    :class="changeClass(file.change)"
                  >
                    {{ changeLabel(file.change) }}
                  </span>
                  <span class="ml-auto text-[10px]">
                    <span class="text-emerald-600 dark:text-emerald-400">+{{ file.additions }}</span>
                    <span class="ml-1.5 text-rose-600 dark:text-rose-400">-{{ file.deletions }}</span>
                  </span>
                </div>
                <div class="max-h-72 overflow-auto bg-white px-3 py-2 dark:bg-slate-900">
                  <div
                    v-for="(line, index) in file.diff.split('\n')"
                    :key="`${file.path}-${index}`"
                    class="whitespace-pre px-1 font-mono text-[11px] leading-5"
                    :class="lineClass(line)"
                  >
                    {{ line || ' ' }}
                  </div>
                </div>
              </article>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>
