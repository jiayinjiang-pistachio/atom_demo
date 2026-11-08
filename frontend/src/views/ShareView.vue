<script setup lang="ts">
import { Eye, LoaderCircle, RefreshCw, Sparkles } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { buildSharePreviewUrl } from '@/api/client'
import { useSharesStore } from '@/stores/shares'

const route = useRoute()
const shares = useSharesStore()

const slug = computed(() => String(route.params.slug ?? ''))
const previewUrl = computed(() =>
  shares.publicShare ? buildSharePreviewUrl(shares.publicShare.slug, shares.publicShare.entry) : '',
)

const expiresLabel = computed(() => {
  const share = shares.publicShare
  if (!share) {
    return ''
  }
  if (!share.expires_at) {
    return '永久有效'
  }
  return `有效期至 ${new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(share.expires_at))}`
})

function load(): void {
  if (slug.value) {
    void shares.loadPublic(slug.value)
  }
}

watch(slug, load)
onMounted(load)
onBeforeUnmount(() => shares.reset())
</script>

<template>
  <main class="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6">
    <div class="flex items-center gap-2.5">
      <span
        class="grid size-9 place-items-center rounded-xl bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
      >
        <Sparkles class="size-4" />
      </span>
      <div>
        <p class="text-sm font-semibold text-slate-900 dark:text-white">Atom Demo</p>
        <p class="text-[11px] text-slate-500 dark:text-slate-400">只读分享</p>
      </div>
    </div>

    <div
      v-if="shares.publicLoading"
      class="mt-8 grid place-items-center rounded-3xl border border-slate-200 bg-white py-28 dark:border-slate-800 dark:bg-slate-900"
    >
      <LoaderCircle class="size-6 animate-spin text-indigo-500" />
      <p class="mt-3 text-sm text-slate-500 dark:text-slate-400">正在加载分享内容…</p>
    </div>

    <div
      v-else-if="shares.publicError"
      class="mt-8 rounded-3xl border border-rose-200 bg-rose-50 p-8 text-center dark:border-rose-500/30 dark:bg-rose-500/10"
    >
      <p class="text-sm font-medium text-rose-700 dark:text-rose-300">{{ shares.publicError }}</p>
      <button
        type="button"
        class="mt-4 inline-flex items-center gap-1.5 rounded-xl border border-rose-300 px-3 py-2 text-xs font-medium text-rose-700 dark:border-rose-500/40 dark:text-rose-300"
        @click="load"
      >
        <RefreshCw class="size-3.5" />
        重试
      </button>
    </div>

    <div
      v-else-if="shares.publicMissing"
      class="mt-8 rounded-3xl border border-slate-200 bg-white px-6 py-20 text-center dark:border-slate-800 dark:bg-slate-900"
    >
      <Eye class="mx-auto size-8 text-slate-300 dark:text-slate-600" />
      <p class="mt-4 text-sm font-medium text-slate-900 dark:text-white">链接已失效</p>
      <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
        该分享不存在、已被撤销或已过期。
      </p>
      <RouterLink
        to="/"
        class="mt-5 inline-flex rounded-xl bg-slate-900 px-3 py-2 text-xs font-medium text-white dark:bg-white dark:text-slate-900"
      >
        创建自己的应用
      </RouterLink>
    </div>

    <template v-else-if="shares.publicShare">
      <header class="mt-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            {{ shares.publicShare.title }}
          </h1>
          <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
            固定版本 v{{ shares.publicShare.version }} · {{ expiresLabel }}
          </p>
        </div>
        <RouterLink
          to="/"
          class="text-xs font-medium text-slate-500 underline underline-offset-2 transition hover:text-slate-900 dark:hover:text-white"
        >
          使用 Atom Demo 生成应用
        </RouterLink>
      </header>

      <div
        class="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <iframe
          :key="shares.publicShare.slug"
          :src="previewUrl"
          sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
          class="h-[75vh] min-h-105 w-full border-0 bg-white"
          title="分享应用预览"
        />
      </div>
    </template>
  </main>
</template>
