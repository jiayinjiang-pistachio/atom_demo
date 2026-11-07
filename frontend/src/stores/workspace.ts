import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { ApiError, postJson } from '@/api/client'
import { openRunStream } from '@/api/events'
import type {
  PlanStep,
  ProjectDetail,
  RunCreatePayload,
  RunStreamEvent,
  RunSummary,
} from '@/api/types'
import { useGuestStore } from '@/stores/guest'
import { useProjectsStore } from '@/stores/projects'

export type RunStatus = 'idle' | RunSummary['status']
type RunMode = 'live' | 'demo'

export interface UsageInfo {
  tokensIn: number
  tokensOut: number
  durationMs: number
}

const TERMINAL_STATUSES: readonly string[] = ['succeeded', 'failed', 'cancelled']
const RUN_STATUSES: readonly string[] = ['queued', 'running', 'succeeded', 'failed', 'cancelled']

export const useWorkspaceStore = defineStore('workspace', () => {
  const guest = useGuestStore()
  const projects = useProjectsStore()

  const run = ref<RunSummary | null>(null)
  const runStatus = ref<RunStatus>('idle')
  const events = ref<RunStreamEvent[]>([])
  const assistantText = ref('')
  const plan = ref<PlanStep[]>([])
  const mode = ref<RunMode | null>(null)
  const usage = ref<UsageInfo | null>(null)
  const previewVersion = ref<number | null>(null)
  const error = ref<string | null>(null)
  const starting = ref(false)

  let closeStream: (() => void) | null = null
  let refreshTimer: ReturnType<typeof setTimeout> | null = null
  let activeProjectId: string | null = null

  const active = computed(
    () => runStatus.value === 'queued' || runStatus.value === 'running' || starting.value,
  )
  const canStart = computed(() => !active.value)
  const hasPreview = computed(() => previewVersion.value !== null)

  function init(project: ProjectDetail): void {
    reset()
    activeProjectId = project.id
    previewVersion.value = project.current_version
    const latest = project.latest_run
    if (!latest) {
      runStatus.value = 'idle'
      return
    }
    run.value = latest
    runStatus.value = latest.status
    if (latest.status === 'failed') {
      error.value = latest.error_message ?? '上次生成失败，请重试'
    }
    if (latest.status === 'queued' || latest.status === 'running') {
      subscribe(latest.id, 0)
    }
  }

  async function start(message: string, projectId: string): Promise<void> {
    if (active.value) {
      return
    }
    starting.value = true
    error.value = null
    assistantText.value = ''
    plan.value = []
    events.value = []
    mode.value = null
    usage.value = null
    activeProjectId = projectId
    try {
      await guest.ensure()
      const created = await postJson<RunSummary>(`/api/v1/projects/${projectId}/runs`, {
        message,
      } satisfies RunCreatePayload)
      run.value = created
      runStatus.value = created.status
      subscribe(created.id, 0)
      scheduleRefresh(0)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        error.value = '已有生成任务在进行中，请稍候'
      } else {
        error.value = caught instanceof Error ? caught.message : '无法启动生成任务'
      }
    } finally {
      starting.value = false
    }
  }

  async function cancel(): Promise<void> {
    if (!run.value) {
      return
    }
    try {
      await postJson(`/api/v1/runs/${run.value.id}/cancel`, {})
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        return
      }
      error.value = caught instanceof Error ? caught.message : '取消任务失败'
    }
  }

  function subscribe(runId: string, afterSeq: number): void {
    closeStream?.()
    closeStream = openRunStream(
      runId,
      {
        onEvent: handleEvent,
        onError(message) {
          error.value = message
        },
      },
      afterSeq,
    )
  }

  function handleEvent(event: RunStreamEvent): void {
    if (event.type !== 'assistant.delta') {
      events.value.push(event)
      if (events.value.length > 250) {
        events.value.splice(0, events.value.length - 250)
      }
    }

    if (event.type === 'assistant.delta') {
      assistantText.value += String(event.data.text ?? '')
      return
    }
    if (event.type === 'plan.updated') {
      const steps = event.data.steps
      if (Array.isArray(steps)) {
        plan.value = steps as PlanStep[]
      }
      return
    }
    if (event.type === 'preview.ready') {
      const version = Number(event.data.version ?? 0)
      if (version > 0) {
        previewVersion.value = version
      }
      scheduleRefresh(0)
      return
    }
    if (event.type === 'usage') {
      mode.value = event.data.mode === 'demo' ? 'demo' : 'live'
      usage.value = {
        tokensIn: Number(event.data.tokens_in ?? 0),
        tokensOut: Number(event.data.tokens_out ?? 0),
        durationMs: Number(event.data.duration_ms ?? 0),
      }
      return
    }
    if (event.type === 'file.updated') {
      scheduleRefresh(350)
      return
    }
    if (event.type === 'error') {
      error.value = String(event.data.message ?? '生成失败')
      return
    }
    if (event.type === 'run.status') {
      const next = String(event.data.status ?? '')
      if (RUN_STATUSES.includes(next) && next !== 'idle') {
        runStatus.value = next as RunStatus
      }
      if (event.data.error) {
        error.value = String(event.data.error)
      }
      if (TERMINAL_STATUSES.includes(runStatus.value)) {
        closeStream?.()
        closeStream = null
        // The final assistant message is persisted; the quiet refresh below
        // replaces the transient streamed text with the stored message.
        assistantText.value = ''
        scheduleRefresh(0)
      }
    }
  }

  function scheduleRefresh(delayMs: number): void {
    if (refreshTimer !== null) {
      globalThis.clearTimeout(refreshTimer)
    }
    refreshTimer = globalThis.setTimeout(() => {
      refreshTimer = null
      if (activeProjectId) {
        void projects.loadProject(activeProjectId, true)
      }
    }, delayMs)
  }

  function reset(): void {
    closeStream?.()
    closeStream = null
    if (refreshTimer !== null) {
      globalThis.clearTimeout(refreshTimer)
      refreshTimer = null
    }
    activeProjectId = null
    run.value = null
    runStatus.value = 'idle'
    events.value = []
    assistantText.value = ''
    plan.value = []
    mode.value = null
    usage.value = null
    previewVersion.value = null
    error.value = null
    starting.value = false
  }

  return {
    run,
    runStatus,
    events,
    assistantText,
    plan,
    mode,
    usage,
    previewVersion,
    error,
    starting,
    active,
    canStart,
    hasPreview,
    init,
    start,
    cancel,
    reset,
  }
})
