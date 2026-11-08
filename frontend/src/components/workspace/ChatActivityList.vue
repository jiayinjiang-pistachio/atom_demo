<script setup lang="ts">
import { FilePlus2, Wrench } from 'lucide-vue-next'
import { computed } from 'vue'

import type { RunStreamEvent } from '@/api/types'

const props = defineProps<{
  events: RunStreamEvent[]
}>()

const toolEntries = computed(() =>
  props.events
    .filter((event) => event.type === 'tool.start' || event.type === 'file.updated')
    .slice(-12),
)

function entryTitle(event: RunStreamEvent): string {
  if (event.type === 'file.updated') {
    return String(event.data.path ?? '')
  }
  return String(event.data.name ?? 'tool')
}

function entryDetail(event: RunStreamEvent): string {
  if (event.type === 'file.updated') {
    if (event.data.deleted) {
      return '已删除'
    }
    return `${event.data.size ?? 0} bytes`
  }
  const args = event.data.arguments as Record<string, unknown> | undefined
  if (!args) {
    return ''
  }
  if (typeof args.path === 'string') {
    return args.path
  }
  if (typeof args.size === 'number') {
    return `${args.size} bytes`
  }
  if (typeof args.steps === 'number') {
    return `${args.steps} 步`
  }
  return ''
}
</script>

<template>
  <div v-if="toolEntries.length > 0" class="space-y-1">
    <div
      v-for="event in toolEntries"
      :key="`${event.seq}-${event.type}`"
      class="flex items-center gap-2 rounded-lg bg-slate-50 px-2.5 py-1.5 text-[11px] text-slate-500 dark:bg-slate-950/40 dark:text-slate-400"
    >
      <FilePlus2 v-if="event.type === 'file.updated'" class="size-3.5 text-indigo-500" />
      <Wrench v-else class="size-3.5 text-slate-400" />
      <span class="font-mono">{{ entryTitle(event) }}</span>
      <span class="ml-auto truncate text-slate-400">{{ entryDetail(event) }}</span>
    </div>
  </div>
</template>
