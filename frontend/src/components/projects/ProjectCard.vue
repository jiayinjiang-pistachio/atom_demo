<script setup lang="ts">
import { ArrowUpRight, Clock3, Trash2 } from 'lucide-vue-next'
import { computed } from 'vue'

import type { ProjectSummary } from '@/api/types'

const props = defineProps<{
  project: ProjectSummary
}>()

const emit = defineEmits<{
  remove: [projectId: string]
}>()

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    idle: '待生成',
    queued: '排队中',
    running: '生成中',
    succeeded: '已生成',
    failed: '生成失败',
  }
  return labels[props.project.status] ?? props.project.status
})

const statusClass = computed(() => {
  if (props.project.status === 'failed') {
    return 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-300'
  }
  if (props.project.status === 'running' || props.project.status === 'queued') {
    return 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300'
  }
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
})

const updatedLabel = computed(() => {
  const date = new Date(props.project.updated_at)
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
})
</script>

<template>
  <article
    class="group flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-500/40"
  >
    <div class="flex items-start justify-between gap-3">
      <span
        class="rounded-full px-2.5 py-1 text-[11px] font-medium"
        :class="statusClass"
      >
        {{ statusLabel }}
      </span>
      <button
        type="button"
        class="grid size-8 place-items-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10 dark:hover:text-rose-300"
        :aria-label="`删除项目 ${project.title}`"
        @click="emit('remove', project.id)"
      >
        <Trash2 class="size-4" />
      </button>
    </div>

    <RouterLink
      :to="`/p/${project.id}`"
      class="mt-3 block focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-500"
    >
      <h3
        class="line-clamp-2 text-sm font-semibold text-slate-900 transition group-hover:text-indigo-600 dark:text-white dark:group-hover:text-indigo-400"
      >
        {{ project.title }}
      </h3>
      <p class="mt-1.5 line-clamp-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
        {{ project.prompt }}
      </p>
    </RouterLink>

    <div class="mt-auto flex items-center justify-between gap-3 pt-4">
      <span class="inline-flex items-center gap-1.5 text-[11px] text-slate-400">
        <Clock3 class="size-3.5" />
        {{ updatedLabel }}
      </span>
      <RouterLink
        :to="`/p/${project.id}`"
        class="inline-flex items-center gap-1 text-[11px] font-medium text-slate-600 transition hover:text-indigo-600 dark:text-slate-300 dark:hover:text-indigo-400"
      >
        打开工作台
        <ArrowUpRight class="size-3.5" />
      </RouterLink>
    </div>
  </article>
</template>
