import { defineStore } from 'pinia'
import { ref } from 'vue'

import { getJson } from '@/api/client'
import type { HealthResponse, MetaResponse } from '@/api/types'

export const useSystemStore = defineStore('system', () => {
  const health = ref<HealthResponse | null>(null)
  const meta = ref<MetaResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const latencyMs = ref<number | null>(null)

  async function refresh(): Promise<void> {
    loading.value = true
    error.value = null
    const startedAt = performance.now()

    try {
      const [healthResult, metaResult] = await Promise.all([
        getJson<HealthResponse>('/healthz', { acceptedStatuses: [200, 503] }),
        getJson<MetaResponse>('/api/v1/meta'),
      ])
      health.value = healthResult
      meta.value = metaResult
      latencyMs.value = Math.round(performance.now() - startedAt)
    } catch (caught) {
      health.value = null
      meta.value = null
      latencyMs.value = null
      error.value = caught instanceof Error ? caught.message : '检测失败'
    } finally {
      loading.value = false
    }
  }

  return { health, meta, loading, error, latencyMs, refresh }
})
