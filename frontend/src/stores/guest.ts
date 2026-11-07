import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { clearGuestToken, postJson, readGuestToken, setGuestToken } from '@/api/client'
import type { GuestBootstrapResponse } from '@/api/types'

export const useGuestStore = defineStore('guest', () => {
  const token = ref<string | null>(readGuestToken())
  const guestId = ref<string | null>(null)
  const ready = ref(false)
  const error = ref<string | null>(null)
  let pendingBootstrap: Promise<void> | null = null

  const hasToken = computed(() => token.value !== null)

  async function ensure(): Promise<void> {
    if (ready.value) {
      return
    }
    if (token.value) {
      ready.value = true
      return
    }
    if (pendingBootstrap) {
      return pendingBootstrap
    }

    pendingBootstrap = (async () => {
      try {
        const response = await postJson<GuestBootstrapResponse>('/api/v1/guest/bootstrap', {})
        token.value = response.token
        guestId.value = response.guest_id
        setGuestToken(response.token)
        ready.value = true
        error.value = null
      } catch (caught) {
        ready.value = false
        error.value = caught instanceof Error ? caught.message : '无法创建访客身份'
        throw caught
      } finally {
        pendingBootstrap = null
      }
    })()

    return pendingBootstrap
  }

  function invalidate(): void {
    clearGuestToken()
    token.value = null
    guestId.value = null
    ready.value = false
  }

  return { token, guestId, ready, error, hasToken, ensure, invalidate }
})
