<script setup lang="ts">
import { Check, Copy, ExternalLink, LoaderCircle, Trash2 } from 'lucide-vue-next'
import { ref, watch } from 'vue'

import { buildShareAppUrl, buildSharePageUrl } from '@/api/client'
import type { ShareSummary } from '@/api/types'

const props = defineProps<{
  shares: ShareSummary[]
  loading: boolean
  revoking: boolean
}>()

const emit = defineEmits<{
  refresh: []
  revoke: [slug: string]
}>()

type ShareLinkKind = 'page' | 'app'

const copiedKey = ref<string | null>(null)
const fallback = ref<{ label: string; url: string } | null>(null)
const revokingSlug = ref<string | null>(null)

watch(
  () => props.revoking,
  (value) => {
    if (!value) {
      revokingSlug.value = null
    }
  },
)

function linkUrl(slug: string, kind: ShareLinkKind): string {
  const origin = typeof window === 'undefined' ? '' : window.location.origin
  return kind === 'app' ? buildShareAppUrl(slug, origin) : buildSharePageUrl(slug, origin)
}

function isCopied(slug: string, kind: ShareLinkKind): boolean {
  return copiedKey.value === `${slug}:${kind}`
}

async function copyLink(slug: string, kind: ShareLinkKind): Promise<void> {
  const url = linkUrl(slug, kind)
  fallback.value = null
  try {
    if (!navigator.clipboard) {
      throw new Error('clipboard unavailable')
    }
    await navigator.clipboard.writeText(url)
    copiedKey.value = `${slug}:${kind}`
  } catch {
    copiedKey.value = null
    fallback.value = { label: kind === 'app' ? '纯净页' : '分享页', url }
  }
}

function requestRevoke(slug: string): void {
  revokingSlug.value = slug
  emit('revoke', slug)
}

function expiryLabel(value: string | null): string {
  if (!value) {
    return '永久有效'
  }
  return `至 ${new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value))}`
}
</script>

<template>
  <div class="mt-5">
    <div class="flex items-center justify-between">
      <h3 class="text-xs font-semibold text-slate-900 dark:text-white">有效分享</h3>
      <button
        type="button"
        class="text-[11px] font-medium text-slate-500 underline underline-offset-2 transition hover:text-slate-900 disabled:opacity-50 dark:hover:text-white"
        :disabled="loading"
        @click="emit('refresh')"
      >
        刷新
      </button>
    </div>

    <div v-if="loading" class="grid place-items-center py-8">
      <LoaderCircle class="size-5 animate-spin text-indigo-500" />
    </div>

    <p
      v-else-if="shares.length === 0"
      class="mt-3 rounded-xl border border-dashed border-slate-300 px-3 py-6 text-center text-[11px] text-slate-500 dark:border-slate-700 dark:text-slate-400"
    >
      暂无有效分享。创建后会显示在这里。
    </p>

    <ul v-else class="mt-3 space-y-2">
      <li
        v-for="share in shares"
        :key="share.slug"
        class="rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800"
      >
        <div class="flex items-center gap-2">
          <span class="font-mono text-[11px] text-slate-700 dark:text-slate-200">
            /s/{{ share.slug }}
          </span>
          <span class="text-[10px] text-slate-400">v{{ share.version }}</span>
          <span class="ml-auto text-[10px] text-slate-400">
            {{ expiryLabel(share.expires_at) }}
          </span>
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-x-1 gap-y-1">
          <span class="text-[10px] font-medium text-slate-500 dark:text-slate-400">分享页</span>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            :aria-label="`复制 /s/${share.slug} 分享页链接`"
            @click="copyLink(share.slug, 'page')"
          >
            <Check v-if="isCopied(share.slug, 'page')" class="size-3 text-emerald-500" />
            <Copy v-else class="size-3" />
            {{ isCopied(share.slug, 'page') ? '已复制' : '复制' }}
          </button>
          <a
            :href="linkUrl(share.slug, 'page')"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ExternalLink class="size-3" />
            打开
          </a>

          <span class="ml-1 text-[10px] font-medium text-slate-500 dark:text-slate-400">
            纯净页
          </span>
          <button
            type="button"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            :aria-label="`复制 /s/${share.slug}/app 纯净页链接`"
            @click="copyLink(share.slug, 'app')"
          >
            <Check v-if="isCopied(share.slug, 'app')" class="size-3 text-emerald-500" />
            <Copy v-else class="size-3" />
            {{ isCopied(share.slug, 'app') ? '已复制' : '复制' }}
          </button>
          <a
            :href="linkUrl(share.slug, 'app')"
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ExternalLink class="size-3" />
            打开
          </a>

          <button
            type="button"
            class="ml-auto inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-medium text-rose-600 transition hover:bg-rose-50 disabled:opacity-50 dark:text-rose-400 dark:hover:bg-rose-500/10"
            :disabled="revoking"
            :aria-label="`撤销 /s/${share.slug}`"
            @click="requestRevoke(share.slug)"
          >
            <LoaderCircle v-if="revokingSlug === share.slug" class="size-3 animate-spin" />
            <Trash2 v-else class="size-3" />
            撤销
          </button>
        </div>
      </li>
    </ul>

    <div
      v-if="fallback"
      class="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-2 dark:border-amber-500/30 dark:bg-amber-500/10"
    >
      <p class="text-[10px] text-amber-700 dark:text-amber-300">
        无法访问剪贴板，请手动复制{{ fallback.label }}链接：
      </p>
      <input
        readonly
        :value="fallback.url"
        class="mt-1 w-full rounded-md border border-amber-200 bg-white px-2 py-1 font-mono text-[11px] text-slate-700 dark:border-amber-500/30 dark:bg-slate-950/40 dark:text-slate-200"
      >
    </div>
  </div>
</template>
