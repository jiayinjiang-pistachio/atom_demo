<script setup lang="ts">
import { LoaderCircle, Send, Sparkles } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

import PromptOptimizeDialog from '@/components/workspace/PromptOptimizeDialog.vue'
import { usePromptsStore } from '@/stores/prompts'

const props = defineProps<{
  initialPrompt: string
  canSend: boolean
  replying: boolean
  active: boolean
  hasFiles: boolean
  projectId: string
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const draft = ref('')
const prompts = usePromptsStore()
const optimizeOpen = ref(false)

const showOptimizeHint = computed(
  () => props.canSend && draft.value.trim().length > 0 && draft.value.trim().length <= 20,
)

watch(
  () => props.initialPrompt,
  (value) => {
    if (!draft.value) {
      draft.value = value
    }
  },
  { immediate: true },
)

function submit(): void {
  const message = draft.value.trim()
  if (!message || !props.canSend || optimizeOpen.value) {
    return
  }
  draft.value = ''
  emit('send', message)
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}

function openOptimize(): void {
  const text = draft.value.trim()
  if (!text || !props.canSend) {
    return
  }
  optimizeOpen.value = true
  void prompts.optimize(props.projectId, text)
}

function closeOptimize(): void {
  optimizeOpen.value = false
  prompts.reset()
}

function retryOptimize(): void {
  void prompts.optimize(props.projectId, draft.value.trim())
}

function applyOptimized(text: string): void {
  draft.value = text
  closeOptimize()
}
</script>

<template>
  <div class="border-t border-slate-100 p-3 dark:border-slate-800">
    <div
      class="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 transition focus-within:border-indigo-400 dark:border-slate-800 dark:bg-slate-950/40"
    >
      <textarea
        v-model="draft"
        rows="1"
        :disabled="!canSend"
        maxlength="4000"
        class="max-h-28 min-w-0 flex-1 resize-none bg-transparent py-1 text-xs text-slate-700 outline-none placeholder:text-slate-400 disabled:opacity-60 dark:text-slate-200"
        :placeholder="replying ? '正在回复，请稍候' : active ? '生成中，可等待或取消任务' : hasFiles ? '继续描述修改，例如：加一个负责人筛选' : '描述你要构建的应用'"
        @keydown="onKeydown"
      />
      <button
        type="button"
        :disabled="!canSend || prompts.optimizing || draft.trim().length === 0"
        class="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-slate-200 px-2 text-[11px] font-medium text-slate-600 transition hover:border-indigo-300 hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300"
        aria-label="优化提示词"
        title="优化提示词"
        @click="openOptimize"
      >
        <LoaderCircle v-if="prompts.optimizing" class="size-3.5 animate-spin" />
        <Sparkles v-else class="size-3.5" />
        优化
      </button>
      <button
        type="button"
        :disabled="!canSend || optimizeOpen || draft.trim().length === 0"
        class="grid size-8 shrink-0 place-items-center rounded-lg bg-indigo-600 text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
        aria-label="发送消息"
        @click="submit"
      >
        <Send class="size-3.5" />
      </button>
    </div>
    <p v-if="showOptimizeHint" class="mt-1.5 text-[10px] text-indigo-500 dark:text-indigo-400">
      描述较简短，可点击「优化」补充细节
    </p>
    <p class="mt-2 text-[10px] text-slate-400">
      Enter 发送 · Shift+Enter 换行 · 生成过程通过 SSE 实时展示
    </p>

    <PromptOptimizeDialog
      :open="optimizeOpen"
      :original="prompts.original"
      :optimized="prompts.optimized"
      :loading="prompts.optimizing"
      :error="prompts.error"
      @close="closeOptimize"
      @retry="retryOptimize"
      @use="applyOptimized"
    />
  </div>
</template>
