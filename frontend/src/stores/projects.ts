import { defineStore } from 'pinia'
import { ref } from 'vue'

import { ApiError, deleteJson, getJson, patchJson, postJson } from '@/api/client'
import type {
  ProjectCreatePayload,
  ProjectDetail,
  ProjectSummary,
  ProjectUpdatePayload,
} from '@/api/types'
import { useGuestStore } from '@/stores/guest'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref<ProjectSummary[]>([])
  const current = ref<ProjectDetail | null>(null)
  const listLoading = ref(false)
  const currentLoading = ref(false)
  const creating = ref(false)
  const error = ref<string | null>(null)
  const guest = useGuestStore()

  async function withFreshGuest(): Promise<void> {
    await guest.ensure()
  }

  async function refresh(): Promise<void> {
    listLoading.value = true
    error.value = null
    try {
      await withFreshGuest()
      projects.value = await getJson<ProjectSummary[]>('/api/v1/projects')
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        guest.invalidate()
        try {
          await withFreshGuest()
          projects.value = await getJson<ProjectSummary[]>('/api/v1/projects')
          return
        } catch (retryError) {
          error.value = retryError instanceof Error ? retryError.message : '项目列表加载失败'
          return
        }
      }
      error.value = caught instanceof Error ? caught.message : '项目列表加载失败'
    } finally {
      listLoading.value = false
    }
  }

  async function create(payload: ProjectCreatePayload): Promise<ProjectSummary> {
    creating.value = true
    error.value = null
    try {
      await withFreshGuest()
      const project = await postJson<ProjectSummary>('/api/v1/projects', payload)
      projects.value = [project, ...projects.value]
      return project
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '项目创建失败'
      throw caught
    } finally {
      creating.value = false
    }
  }

  async function loadProject(projectId: string, quiet = false): Promise<void> {
    if (!quiet) {
      currentLoading.value = true
      error.value = null
      current.value = null
    }
    try {
      await withFreshGuest()
      current.value = await getJson<ProjectDetail>(`/api/v1/projects/${projectId}`)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        guest.invalidate()
        await withFreshGuest()
        current.value = await getJson<ProjectDetail>(`/api/v1/projects/${projectId}`)
        return
      }
      error.value = caught instanceof Error ? caught.message : '项目加载失败'
    } finally {
      if (!quiet) {
        currentLoading.value = false
      }
    }
  }

  async function rename(projectId: string, title: string): Promise<void> {
    await withFreshGuest()
    const updated = await patchJson<ProjectSummary>(`/api/v1/projects/${projectId}`, {
      title,
    } satisfies ProjectUpdatePayload)
    projects.value = projects.value.map((project) =>
      project.id === updated.id ? updated : project,
    )
    if (current.value?.id === updated.id) {
      current.value = { ...current.value, ...updated }
    }
  }

  async function remove(projectId: string): Promise<void> {
    await withFreshGuest()
    await deleteJson(`/api/v1/projects/${projectId}`)
    projects.value = projects.value.filter((project) => project.id !== projectId)
    if (current.value?.id === projectId) {
      current.value = null
    }
  }

  return {
    projects,
    current,
    listLoading,
    currentLoading,
    creating,
    error,
    refresh,
    create,
    loadProject,
    rename,
    remove,
  }
})
