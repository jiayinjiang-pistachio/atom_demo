import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ApiError } from '@/api/client'
import {
  diffVersions,
  exportVersion as exportVersionApi,
  listVersions,
  restoreVersion as restoreVersionApi,
} from '@/api/versions'
import type { VersionDiff, VersionSummary } from '@/api/types'
import { useGuestStore } from '@/stores/guest'
import { useProjectsStore } from '@/stores/projects'

function messageOf(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}

export const useVersionsStore = defineStore('versions', () => {
  const guest = useGuestStore()
  const projects = useProjectsStore()

  const items = ref<VersionSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const diff = ref<VersionDiff | null>(null)
  const diffLoading = ref(false)
  const restoring = ref(false)
  const exporting = ref(false)

  const current = computed(
    () => items.value.find((item) => item.is_current) ?? items.value[0] ?? null,
  )

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
      items.value = await withGuest(() => listVersions(projectId))
    } catch (caught) {
      items.value = []
      error.value = messageOf(caught, '版本列表加载失败')
    } finally {
      loading.value = false
    }
  }

  async function loadDiff(projectId: string, fromVersion: number, toVersion: number): Promise<void> {
    diffLoading.value = true
    error.value = null
    diff.value = null
    try {
      diff.value = await withGuest(() => diffVersions(projectId, fromVersion, toVersion))
    } catch (caught) {
      error.value = messageOf(caught, '版本对比加载失败')
    } finally {
      diffLoading.value = false
    }
  }

  function clearDiff(): void {
    diff.value = null
  }

  async function restore(projectId: string, number: number): Promise<VersionSummary | null> {
    restoring.value = true
    error.value = null
    try {
      const version = await withGuest(() => restoreVersionApi(projectId, number))
      await projects.loadProject(projectId, true)
      await load(projectId)
      return version
    } catch (caught) {
      error.value = messageOf(caught, '版本回滚失败')
      return null
    } finally {
      restoring.value = false
    }
  }

  async function exportVersion(projectId: string, version?: number): Promise<void> {
    exporting.value = true
    error.value = null
    try {
      await withGuest(() => exportVersionApi(projectId, version))
    } catch (caught) {
      error.value = messageOf(caught, '导出失败')
    } finally {
      exporting.value = false
    }
  }

  function reset(): void {
    items.value = []
    loading.value = false
    error.value = null
    diff.value = null
    diffLoading.value = false
    restoring.value = false
    exporting.value = false
  }

  return {
    items,
    loading,
    error,
    diff,
    diffLoading,
    restoring,
    exporting,
    current,
    load,
    loadDiff,
    clearDiff,
    restore,
    exportVersion,
    reset,
  }
})
