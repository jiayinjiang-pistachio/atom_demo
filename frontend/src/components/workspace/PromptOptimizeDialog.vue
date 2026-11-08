<script setup lang="ts">
import { AlertTriangle, LoaderCircle, Sparkles, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  original: string
  optimized: string
  loading: boolean
  error: string | null
}>()

const emit = defineEmits<{
  close: []
  retry: []
  use: [text: string]
}>()

const edited = ref('')
const canUse = computed(() => !props.loading && edited.value.trim().length > 0)

watch(
  () => [props.open, props.optimized],
  () => {
    if (props.open) {
      edited.value = props.optimized
    }
  },
  { immediate: true },
)

function onKeydown(event: KeyboardEvent): void {
  if (props.open && event.key === 'Escape') {
    emit('close')
  }
}

function apply(): void {
  const text = edited.value.trim()
  if (text && canUse.value) {
    emit('use', text)
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
      aria-label="关闭提示词优化"
      @click.self="emit('close')"
      @keydown.enter="emit('close')"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="optimize-dialog-title"
        class="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900"
      >
        <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-3 dark:border-slate-800">
          <Sparkles class="size-4 text-indigo-500" />
          <h2 id="optimize-dialog-title" class="text-sm font-semibold text-slate-900 dark:text-white">
            优化提示词
          </h2>
          <span class="text-[11px] text-slate-400">优化结果不会自动发送</span>
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
              <p class="mt-2 text-xs text-slate-500 dark:text-slate-400">正在优化描述…</p>
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

          <template v-else>
            <div>
              <p class="text-[11px] font-semibold text-slate-500 dark:text-slate-400">原始描述</p>
              <p
                class="mt-1.5 rounded-xl bg-slate-50 px-3 py-2.5 text-xs leading-6 whitespace-pre-wrap text-slate-600 dark:bg-slate-950/40 dark:text-slate-400"
              >
                {{ original }}
              </p>
            </div>

            <div class="mt-4">
              <p class="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                优化后描述（可编辑）
              </p>
              <textarea
                v-model="edited"
                rows="10"
                maxlength="4000"
                class="mt-1.5 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs leading-6 text-slate-700 outline-none transition focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-200"
                @keydown.enter.stop
              />
              <p class="mt-1.5 text-[10px] text-slate-400">
                可继续修改，点击「使用优化结果」后只回填输入框。
              </p>
            </div>
          </template>
        </div>

        <div class="flex items-center justify-end gap-2 border-t border-slate-100 px-5 py-3 dark:border-slate-800">
          <button
            type="button"
            class="rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            @click="emit('close')"
          >
            取消
          </button>
          <button
            type="button"
            :disabled="!canUse"
            class="rounded-lg bg-indigo-600 px-3 py-1.5 text-[11px] font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40"
            @click="apply"
          >
            使用优化结果
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
