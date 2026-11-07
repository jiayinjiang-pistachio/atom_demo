<script setup lang="ts">
import { AlertTriangle, LoaderCircle, Share2, X } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { ShareCreatePayload, ShareSummary, VersionSummary } from '@/api/types'
import ShareList from '@/components/workspace/ShareList.vue'

const props = defineProps<{
  open: boolean
  currentVersion: number | null
  versions: VersionSummary[]
  shares: ShareSummary[]
  loading: boolean
  creating: boolean
  revoking: boolean
  error: string | null
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  create: [payload: ShareCreatePayload]
  revoke: [slug: string]
}>()

const expiry = ref<'7' | '30' | 'permanent'>('7')
const selectedVersion = ref<number | null>(null)

const expiresInDays = computed<7 | 30 | null>(() => {
  if (expiry.value === 'permanent') {
    return null
  }
  return expiry.value === '30' ? 30 : 7
})

const canCreate = computed(() => selectedVersion.value !== null && !props.creating)

function resetForm(): void {
  selectedVersion.value = props.currentVersion ?? props.versions[0]?.number ?? null
  expiry.value = '7'
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      resetForm()
    }
  },
)

watch(
  () => props.versions,
  (items) => {
    if (selectedVersion.value === null && items.length > 0) {
      selectedVersion.value = props.currentVersion ?? items[0]?.number ?? null
    }
  },
  { immediate: true },
)

function submitCreate(): void {
  if (!canCreate.value || selectedVersion.value === null) {
    return
  }
  emit('create', {
    version: selectedVersion.value,
    expires_in_days: expiresInDays.value,
  })
}

function onKeydown(event: KeyboardEvent): void {
  if (props.open && event.key === 'Escape') {
    emit('close')
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
      @click.self="emit('close')"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-dialog-title"
        class="flex max-h-[85vh] w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900"
      >
        <div class="flex items-center gap-3 border-b border-slate-100 px-5 py-3 dark:border-slate-800">
          <Share2 class="size-4 text-slate-500" />
          <h2 id="share-dialog-title" class="text-sm font-semibold text-slate-900 dark:text-white">
            只读分享
          </h2>
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
          <p class="text-xs leading-5 text-slate-500 dark:text-slate-400">
            分享页固定在所选版本，访客无需登录即可查看；撤销或到期后立即失效。
          </p>

          <div class="mt-3 grid gap-2 sm:grid-cols-2">
            <label class="block text-[11px] font-medium text-slate-600 dark:text-slate-300">
              版本
              <select
                v-model="selectedVersion"
                class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-200"
              >
                <option v-for="version in versions" :key="version.number" :value="version.number">
                  v{{ version.number }}{{ version.is_current ? '（当前）' : '' }}
                </option>
              </select>
            </label>
            <label class="block text-[11px] font-medium text-slate-600 dark:text-slate-300">
              有效期
              <select
                v-model="expiry"
                class="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-950/40 dark:text-slate-200"
              >
                <option value="7">7 天</option>
                <option value="30">30 天</option>
                <option value="permanent">永久</option>
              </select>
            </label>
          </div>

          <button
            type="button"
            class="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="!canCreate"
            @click="submitCreate"
          >
            <LoaderCircle v-if="creating" class="size-3.5 animate-spin" />
            <Share2 v-else class="size-3.5" />
            {{ creating ? '创建中…' : '创建分享链接' }}
          </button>

          <div
            v-if="error"
            class="mt-3 flex items-start gap-2 rounded-xl bg-rose-50 px-3 py-2 text-[11px] leading-5 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300"
          >
            <AlertTriangle class="mt-0.5 size-3.5 shrink-0" />
            <span>{{ error }}</span>
          </div>

          <ShareList
            :shares="shares"
            :loading="loading"
            :revoking="revoking"
            @refresh="emit('refresh')"
            @revoke="emit('revoke', $event)"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>
