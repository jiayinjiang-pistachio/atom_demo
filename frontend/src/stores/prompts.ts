import { defineStore } from 'pinia'
import { ref } from 'vue'

import { optimizePrompt } from '@/api/prompts'
import { useGuestStore } from '@/stores/guest'

export const usePromptsStore = defineStore('prompts', () => {
  const guest = useGuestStore()

  const optimizing = ref(false)
  const original = ref('')
  const optimized = ref('')
  const error = ref<string | null>(null)

  let requestSeq = 0

  async function optimize(projectId: string, draft: string): Promise<void> {
    if (optimizing.value) {
      return
    }
    const text = draft.trim()
    if (!text) {
      return
    }

    const seq = ++requestSeq
    optimizing.value = true
    original.value = text
    optimized.value = ''
    error.value = null

    try {
      await guest.ensure()
      const result = await optimizePrompt(projectId, text)
      if (seq !== requestSeq) {
        return
      }
      original.value = result.original
      optimized.value = result.optimized
    } catch (caught) {
      if (seq !== requestSeq) {
        return
      }
      error.value = caught instanceof Error ? caught.message : '优化失败，请重试'
    } finally {
      if (seq === requestSeq) {
        optimizing.value = false
      }
    }
  }

  function reset(): void {
    requestSeq += 1
    optimizing.value = false
    original.value = ''
    optimized.value = ''
    error.value = null
  }

  return { optimizing, original, optimized, error, optimize, reset }
})
