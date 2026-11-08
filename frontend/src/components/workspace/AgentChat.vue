<script setup lang="ts">
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  LoaderCircle,
  MessageSquareText,
  Sparkles,
  Square,
} from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

import type { PlanStep, ProjectMessage, RunStreamEvent } from '@/api/types'
import ChatActivityList from '@/components/workspace/ChatActivityList.vue'
import ChatComposer from '@/components/workspace/ChatComposer.vue'

const props = defineProps<{
  messages: ProjectMessage[]
  assistantText: string
  plan: PlanStep[]
  events: RunStreamEvent[]
  status: string
  active: boolean
  replying: boolean
  mode: 'live' | 'demo' | null
  usage: { tokensIn: number; tokensOut: number; durationMs: number } | null
  error: string | null
  initialPrompt: string
  canSend: boolean
  hasFiles: boolean
  projectId: string
}>()

const emit = defineEmits<{
  send: [message: string]
  cancel: []
  start: []
}>()

const scrollArea = ref<HTMLElement | null>(null)

const statusLabels: Record<string, string> = {
  idle: '待生成',
  queued: '排队中',
  running: '生成中',
  succeeded: '已生成',
  failed: '生成失败',
  cancelled: '已取消',
}
const statusLabel = computed(() =>
  props.replying ? '回复中' : (statusLabels[props.status] ?? props.status),
)

const statusClass = computed(() => {
  if (props.replying) {
    return 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300'
  }
  if (props.status === 'running' || props.status === 'queued') {
    return 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'
  }
  if (props.status === 'succeeded') {
    return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
  }
  if (props.status === 'failed' || props.status === 'cancelled') {
    return 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400'
  }
  return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
})

const showStartButton = computed(
  () => props.messages.length === 0 && !props.hasFiles && !props.active,
)

async function scrollToBottom(): Promise<void> {
  await nextTick()
  if (scrollArea.value) {
    scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  }
}

watch(
  () => [props.messages.length, props.assistantText, props.events.length, props.plan.length],
  () => void scrollToBottom(),
)


</script>

<template>
  <section
    class="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
  >
    <div class="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
      <MessageSquareText class="size-4 text-slate-500" />
      <h2 class="text-xs font-semibold text-slate-900 dark:text-white">Agent 对话</h2>
      <span class="rounded-full px-2 py-0.5 text-[10px] font-medium" :class="statusClass">
        {{ statusLabel }}
      </span>
      <span
        v-if="mode === 'demo'"
        class="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-medium text-sky-700 dark:bg-sky-500/10 dark:text-sky-400"
      >
        演示模式
      </span>
      <LoaderCircle
        v-if="active || replying"
        class="size-3.5 animate-spin text-amber-500"
      />
      <button
        v-if="active"
        type="button"
        class="ml-auto inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-600 transition hover:border-rose-300 hover:text-rose-600 dark:border-slate-700 dark:text-slate-300"
        @click="emit('cancel')"
      >
        <Square class="size-3" />
        取消
      </button>
    </div>

    <div ref="scrollArea" class="flex-1 space-y-3 overflow-y-auto px-4 py-4">
      <div
        v-if="messages.length === 0 && !assistantText"
        class="rounded-xl bg-slate-50 px-3 py-4 text-xs leading-6 text-slate-500 dark:bg-slate-950/40 dark:text-slate-400"
      >
        <p>项目已创建并持久化。点击下方按钮，Agent 会规划、写文件并生成可预览版本。</p>
        <button
          v-if="showStartButton"
          type="button"
          class="mt-3 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:opacity-50"
          :disabled="!canSend"
          @click="emit('start')"
        >
          <Sparkles class="size-3.5" />
          开始生成
        </button>
      </div>

      <div
        v-for="message in messages"
        :key="message.id"
        class="rounded-xl px-3 py-2.5 text-xs leading-6 whitespace-pre-wrap"
        :class="message.role === 'user'
          ? 'bg-indigo-50 text-indigo-900 dark:bg-indigo-500/10 dark:text-indigo-200'
          : 'bg-slate-50 text-slate-700 dark:bg-slate-950/40 dark:text-slate-300'"
      >
        {{ message.content }}
      </div>

      <div
        v-if="assistantText"
        class="rounded-xl bg-slate-50 px-3 py-2.5 text-xs leading-6 whitespace-pre-wrap text-slate-700 dark:bg-slate-950/40 dark:text-slate-300"
      >
        {{ assistantText }}
        <span v-if="active" class="ml-0.5 inline-block h-3 w-1 animate-pulse bg-indigo-500 align-middle" />
      </div>

      <div
        v-if="plan.length > 0"
        class="rounded-xl border border-slate-200 px-3 py-3 dark:border-slate-800"
      >
        <p class="text-[11px] font-semibold text-slate-500 dark:text-slate-400">构建计划</p>
        <ul class="mt-2 space-y-1.5">
          <li v-for="step in plan" :key="step.title" class="flex items-center gap-2 text-[11px]">
            <CheckCircle2 v-if="step.status === 'done'" class="size-3.5 text-emerald-500" />
            <LoaderCircle
              v-else-if="step.status === 'in_progress'"
              class="size-3.5 animate-spin text-amber-500"
            />
            <Circle v-else class="size-3.5 text-slate-300 dark:text-slate-600" />
            <span
              :class="step.status === 'done'
                ? 'text-slate-500 line-through dark:text-slate-400'
                : 'text-slate-700 dark:text-slate-300'"
            >
              {{ step.title }}
            </span>
          </li>
        </ul>
      </div>

      <ChatActivityList :events="events" />

      <div
        v-if="usage"
        class="flex flex-wrap gap-3 text-[10px] text-slate-400"
      >
        <span>tokens {{ usage.tokensIn }} / {{ usage.tokensOut }}</span>
        <span>耗时 {{ (usage.durationMs / 1000).toFixed(1) }}s</span>
      </div>

      <div
        v-if="error"
        class="flex items-start gap-2 rounded-xl bg-rose-50 px-3 py-2.5 text-[11px] leading-5 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
      >
        <AlertTriangle class="mt-0.5 size-3.5 shrink-0" />
        <span>{{ error }}</span>
      </div>
    </div>

    <ChatComposer
      :initial-prompt="initialPrompt"
      :can-send="canSend"
      :replying="replying"
      :active="active"
      :has-files="hasFiles"
      :project-id="projectId"
      @send="emit('send', $event)"
    />
  </section>
</template>
