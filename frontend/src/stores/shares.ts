import { defineStore } from 'pinia'
import { ref } from 'vue'

import { ApiError } from '@/api/client'
import {
  createShare as createShareApi,
  getPublicShare,
  listShares,
  revokeShare as revokeShareApi,
} from '@/api/shares'
import type { PublicShare, ShareCreatePayload, ShareSummary } from '@/api/types'
import { useGuestStore } from '@/stores/guest'

function messageOf(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}

export const useSharesStore = defineStore('shares', () => {
  const guest = useGuestStore()

  const items = ref<ShareSummary[]>([])
  const loading = ref(false)
  const creating = ref(false)
  const revoking = ref(false)
  const error = ref<string | null>(null)

  const publicShare = ref<PublicShare | null>(null)
  const publicLoading = ref(false)
  const publicError = ref<string | null>(null)
  const publicMissing = ref(false)

  async function withGuest<T>(task: () => Promise<T>): Promise<T> {
    await guest.ensure()
    try {
      return await task()
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        guest.invalidate()
        await guest.ensure()
        return await task()
      }
      throw caught
    }
  }

  async function load(projectId: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      items.value = await withGuest(() => listShares(projectId))
    } catch (caught) {
      error.value = messageOf(caught, '分享列表加载失败')
    } finally {
      loading.value = false
    }
  }

  async function create(
    projectId: string,
    payload: ShareCreatePayload,
  ): Promise<ShareSummary | null> {
    creating.value = true
    error.value = null
    try {
      const share = await withGuest(() => createShareApi(projectId, payload))
      items.value = [share, ...items.value]
      return share
    } catch (caught) {
      error.value = messageOf(caught, '创建分享失败')
      return null
    } finally {
      creating.value = false
    }
  }

  async function revoke(projectId: string, slug: string): Promise<boolean> {
    revoking.value = true
    error.value = null
    try {
      await withGuest(() => revokeShareApi(projectId, slug))
      items.value = items.value.filter((share) => share.slug !== slug)
      return true
    } catch (caught) {
      error.value = messageOf(caught, '撤销分享失败')
      return false
    } finally {
      revoking.value = false
    }
  }

  async function loadPublic(slug: string): Promise<void> {
    publicLoading.value = true
    publicError.value = null
    publicMissing.value = false
    publicShare.value = null
    try {
      publicShare.value = await getPublicShare(slug)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        publicMissing.value = true
      } else {
        publicError.value = messageOf(caught, '分享页加载失败')
      }
    } finally {
      publicLoading.value = false
    }
  }

  function reset(): void {
    items.value = []
    loading.value = false
    creating.value = false
    revoking.value = false
    error.value = null
    publicShare.value = null
    publicLoading.value = false
    publicError.value = null
    publicMissing.value = false
  }

  return {
    items,
    loading,
    creating,
    revoking,
    error,
    publicShare,
    publicLoading,
    publicError,
    publicMissing,
    load,
    create,
    revoke,
    loadPublic,
    reset,
  }
})
