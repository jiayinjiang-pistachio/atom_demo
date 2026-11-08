<script setup lang="ts">
import { LoaderCircle, RefreshCw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

import { buildSharePreviewUrl } from '@/api/client'
import { useSharesStore } from '@/stores/shares'

const route = useRoute()
const shares = useSharesStore()

const slug = computed(() => String(route.params.slug ?? ''))
const previewUrl = computed(() =>
  shares.publicShare ? buildSharePreviewUrl(shares.publicShare.slug, shares.publicShare.entry) : '',
)
const iframeTitle = computed(() => `${shares.publicShare?.title ?? '共享'} 应用`)

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
  <div v-if="shares.publicShare" class="fixed inset-0 bg-white">
    <iframe
      :key="shares.publicShare.slug"
      :src="previewUrl"
      sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
      class="size-full border-0"
      :title="iframeTitle"
    />
  </div>

  <div v-else class="fixed inset-0 grid place-items-center bg-slate-50 px-6 dark:bg-slate-950">
    <div class="text-center">
      <template v-if="shares.publicLoading">
        <LoaderCircle class="mx-auto size-6 animate-spin text-indigo-500" />
        <p class="mt-3 text-sm text-slate-500 dark:text-slate-400">正在加载应用…</p>
      </template>

      <template v-else-if="shares.publicError">
        <p class="text-sm font-medium text-rose-600 dark:text-rose-400">{{ shares.publicError }}</p>
        <button
          type="button"
          class="mt-4 inline-flex items-center gap-1.5 rounded-xl border border-rose-300 px-3 py-2 text-xs font-medium text-rose-700 dark:border-rose-500/40 dark:text-rose-300"
          @click="load"
        >
          <RefreshCw class="size-3.5" />
          重试
        </button>
      </template>

      <template v-else-if="shares.publicMissing">
        <p class="text-sm font-medium text-slate-900 dark:text-white">链接已失效</p>
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
          该分享不存在、已被撤销或已过期。
        </p>
      </template>
    </div>
  </div>
</template>
