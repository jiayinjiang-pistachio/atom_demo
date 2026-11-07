<script setup lang="ts">
import { ExternalLink, LoaderCircle, Monitor, MonitorPlay, Smartphone } from 'lucide-vue-next'
import { computed, ref } from 'vue'

import { buildPreviewUrl } from '@/api/client'

const props = defineProps<{
  projectId: string
  version: number | null
  active: boolean
  status: string
}>()

const viewport = ref<'desktop' | 'mobile'>('desktop')

const previewUrl = computed(() =>
  props.version === null ? '' : buildPreviewUrl(props.projectId, props.version),
)

const frameClass = computed(() =>
  viewport.value === 'mobile' ? 'mx-auto w-[390px] max-w-full' : 'w-full',
)

const overlayLabel = computed(() => {
  if (!props.active) {
    return ''
  }
  return props.version === null ? '正在生成首个版本…' : '正在生成新版本，预览保持上一可用版本'
})
</script>

<template>
  <section
    class="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
  >
    <div class="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
      <MonitorPlay class="size-4 text-slate-500" />
      <h2 class="text-xs font-semibold text-slate-900 dark:text-white">预览</h2>
      <span
        v-if="version !== null"
        class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
      >
        v{{ version }}
      </span>
      <LoaderCircle v-if="active" class="size-3.5 animate-spin text-amber-500" />

      <div class="ml-auto flex items-center gap-1">
        <button
          type="button"
          class="grid size-7 place-items-center rounded-lg transition"
          :class="viewport === 'desktop'
            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
            : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
          aria-label="桌面尺寸"
          @click="viewport = 'desktop'"
        >
          <Monitor class="size-3.5" />
        </button>
        <button
          type="button"
          class="grid size-7 place-items-center rounded-lg transition"
          :class="viewport === 'mobile'
            ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
            : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
          aria-label="移动尺寸"
          @click="viewport = 'mobile'"
        >
          <Smartphone class="size-3.5" />
        </button>
        <a
          v-if="previewUrl"
          :href="previewUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="grid size-7 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-800"
          aria-label="在新窗口打开预览"
        >
          <ExternalLink class="size-3.5" />
        </a>
      </div>
    </div>

    <div class="relative min-h-0 flex-1 p-3">
      <div
        v-if="previewUrl"
        class="relative h-full min-h-105 overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700"
      >
        <iframe
          :key="`${projectId}-${version}`"
          :src="previewUrl"
          sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
          class="h-full min-h-105 border-0 bg-white transition-all"
          :class="frameClass"
          title="生成应用预览"
        />
        <div
          v-if="active"
          class="pointer-events-none absolute inset-x-0 top-0 flex justify-center p-2"
        >
          <span
            class="rounded-full bg-slate-900/85 px-3 py-1.5 text-[11px] font-medium text-white shadow-lg"
          >
            {{ overlayLabel }}
          </span>
        </div>
      </div>

      <div
        v-else
        class="grid h-full min-h-105 place-items-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 text-center dark:border-slate-700 dark:bg-slate-950/40"
      >
        <div>
          <MonitorPlay class="mx-auto size-8 text-slate-300 dark:text-slate-600" />
          <p class="mt-3 text-xs font-medium text-slate-700 dark:text-slate-300">
            {{ status === 'idle' ? '等待首次生成' : '暂无可用版本' }}
          </p>
          <p class="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">
            生成成功后会在这里通过独立预览域渲染，支持桌面与移动尺寸切换。
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
