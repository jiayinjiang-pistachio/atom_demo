<script setup lang="ts">
import { ArrowRight, LoaderCircle, WandSparkles } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import type { ProjectCreatePayload } from '@/api/types'

const props = defineProps<{
  loading: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  submit: [payload: ProjectCreatePayload]
}>()

const prompt = ref('')
const title = ref('')
const localError = ref<string | null>(null)

const canSubmit = computed(() => prompt.value.trim().length > 0 && !props.loading && !props.disabled)

function submit(): void {
  if (!canSubmit.value) {
    return
  }
  const normalizedPrompt = prompt.value.trim()
  if (normalizedPrompt.length === 0) {
    localError.value = '请先描述你要构建的应用'
    return
  }
  localError.value = null
  emit('submit', {
    prompt: normalizedPrompt,
    title: title.value.trim() || undefined,
  })
}

function useExample(): void {
  prompt.value =
    '做一个支持拖拽的团队任务看板，可以按负责人筛选，并把筛选条件保存在浏览器里。'
}
</script>

<template>
  <form
    class="rounded-2xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-950/40"
    @submit.prevent="submit"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <label
        for="project-prompt"
        class="text-xs font-medium tracking-wide text-slate-500 dark:text-slate-400"
      >
        应用描述
      </label>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 transition hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
        @click="useExample"
      >
        <WandSparkles class="size-3.5" />
        填入示例
      </button>
    </div>

    <textarea
      id="project-prompt"
      v-model="prompt"
      rows="3"
      :disabled="loading || disabled"
      maxlength="4000"
      class="mt-2 w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-70 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200 dark:placeholder:text-slate-500"
      placeholder="例如：做一个支持拖拽的团队任务看板，可以按负责人筛选，并记住当前筛选条件。"
    />

    <div class="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
      <div>
        <label
          for="project-title"
          class="text-xs font-medium text-slate-500 dark:text-slate-400"
        >
          项目名称（可选）
        </label>
        <input
          id="project-title"
          v-model="title"
          type="text"
          maxlength="120"
          :disabled="loading || disabled"
          class="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-70 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
          placeholder="不填则根据描述自动生成"
        >
      </div>

      <button
        type="submit"
        :disabled="!canSubmit"
        class="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 text-sm font-medium text-white shadow-sm shadow-indigo-600/20 transition hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <LoaderCircle v-if="loading" class="size-4 animate-spin" />
        {{ loading ? '创建中' : '创建项目' }}
        <ArrowRight v-if="!loading" class="size-4" />
      </button>
    </div>

    <p
      v-if="localError"
      class="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
    >
      {{ localError }}
    </p>
  </form>
</template>
