import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunStreamHandlers } from '@/api/events'
import type { ProjectDetail, RunStreamEvent } from '@/api/types'

const mocks = vi.hoisted(() => ({
  handlers: [] as RunStreamHandlers[],
  abort: vi.fn(),
  postJson: vi.fn(),
  ensure: vi.fn(async () => {}),
  loadProject: vi.fn<(_projectId: string, _quiet?: boolean) => Promise<void>>(async () => {}),
}))

vi.mock('@/api/events', () => ({
  openRunStream: vi.fn((_runId: string, handlers: RunStreamHandlers) => {
    mocks.handlers.push(handlers)
    return mocks.abort
  }),
}))

vi.mock('@/api/client', () => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
  postJson: mocks.postJson,
}))

vi.mock('@/stores/guest', () => ({
  useGuestStore: () => ({ ensure: mocks.ensure }),
}))

vi.mock('@/stores/projects', () => ({
  useProjectsStore: () => ({ loadProject: mocks.loadProject }),
}))

import { useWorkspaceStore } from './workspace'

function project(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    id: 'project-1',
    title: '看板',
    prompt: '做一个看板',
    entry_path: 'index.html',
    status: 'ready',
    current_version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    messages: [],
    files: [],
    latest_run: null,
    ...overrides,
  }
}

function runEvent(type: string, data: Record<string, unknown> = {}): RunStreamEvent {
  return { seq: 1, type, data }
}

function latestHandlers(): RunStreamHandlers {
  const handlers = mocks.handlers.at(-1)
  if (!handlers) {
    throw new Error('stream was not subscribed')
  }
  return handlers
}

describe('workspace store', () => {
  let store: ReturnType<typeof useWorkspaceStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useWorkspaceStore()
    mocks.handlers = []
    mocks.abort.mockClear()
    mocks.ensure.mockClear()
    mocks.loadProject.mockClear()
    mocks.postJson.mockReset()
    mocks.postJson.mockResolvedValue({
      id: 'run-1',
      project_id: 'project-1',
      status: 'queued',
      model: 'deepseek-chat',
      tokens_in: 0,
      tokens_out: 0,
      error_code: null,
      error_message: null,
      created_at: '2026-01-01T00:00:00Z',
      started_at: null,
      finished_at: null,
    })
  })

  afterEach(() => {
    store.reset()
    vi.useRealTimers()
  })

  it('initializes from the project detail and reconnects an active run', () => {
    const detail = project({
      latest_run: {
        id: 'run-1',
        project_id: 'project-1',
        status: 'running',
        model: 'deepseek-chat',
        tokens_in: 0,
        tokens_out: 0,
        error_code: null,
        error_message: null,
        created_at: '2026-01-01T00:00:00Z',
        started_at: '2026-01-01T00:00:00Z',
        finished_at: null,
      },
    })

    store.init(detail)

    expect(store.runStatus).toBe('running')
    expect(store.previewVersion).toBe(1)
    expect(store.active).toBe(true)
    expect(mocks.handlers).toHaveLength(1)
  })

  it('surfaces the last failure message on init', () => {
    store.init(
      project({
        latest_run: {
          id: 'run-2',
          project_id: 'project-1',
          status: 'failed',
          model: 'deepseek-chat',
          tokens_in: 0,
          tokens_out: 0,
          error_code: 'llm_error',
          error_message: '模型暂时不可用',
          created_at: '2026-01-01T00:00:00Z',
          started_at: '2026-01-01T00:00:00Z',
          finished_at: '2026-01-01T00:00:02Z',
        },
      }),
    )

    expect(store.runStatus).toBe('failed')
    expect(store.error).toBe('模型暂时不可用')
  })

  it('accumulates assistant deltas and applies plan updates', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')

    const handlers = latestHandlers()
    handlers.onEvent(runEvent('assistant.delta', { text: '先规划，' }))
    handlers.onEvent(runEvent('assistant.delta', { text: '再写文件。' }))
    handlers.onEvent(
      runEvent('plan.updated', {
        steps: [
          { title: '规划页面', status: 'done' },
          { title: '写入文件', status: 'in_progress' },
        ],
      }),
    )

    expect(store.assistantText).toBe('先规划，再写文件。')
    expect(store.plan).toHaveLength(2)
    expect(store.events.map((event) => event.type)).not.toContain('assistant.delta')
  })

  it('switches preview version and records usage mode', async () => {
    vi.useFakeTimers()
    store.init(project())
    await store.start('做一个看板', 'project-1')

    const handlers = latestHandlers()
    handlers.onEvent(runEvent('preview.ready', { version: 2 }))
    handlers.onEvent(
      runEvent('usage', { mode: 'demo', tokens_in: 12, tokens_out: 34, duration_ms: 900 }),
    )

    expect(store.previewVersion).toBe(2)
    expect(store.mode).toBe('demo')
    expect(store.usage).toEqual({ tokensIn: 12, tokensOut: 34, durationMs: 900 })

    vi.advanceTimersByTime(0)
    expect(mocks.loadProject).toHaveBeenCalledWith('project-1', true)
  })

  it('closes the stream and clears transient text on a terminal status', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')

    const handlers = latestHandlers()
    handlers.onEvent(runEvent('assistant.delta', { text: '临时流式内容' }))
    handlers.onEvent(runEvent('run.status', { status: 'succeeded' }))

    expect(store.runStatus).toBe('succeeded')
    expect(store.assistantText).toBe('')
    expect(store.active).toBe(false)
    expect(mocks.abort).toHaveBeenCalledTimes(1)
  })

  it('reports a conflict when a run is already active', async () => {
    const { ApiError } = await import('@/api/client')
    mocks.postJson.mockRejectedValueOnce(new ApiError(409, 'conflict'))

    await store.start('做一个看板', 'project-1')

    expect(store.error).toBe('已有生成任务在进行中，请稍候')
    expect(store.starting).toBe(false)
    expect(store.runStatus).toBe('idle')
  })

  it('reset tears down the stream and clears state', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')
    latestHandlers().onEvent(runEvent('run.status', { status: 'running' }))
    store.reset()

    expect(mocks.abort).toHaveBeenCalled()
    expect(store.runStatus).toBe('idle')
    expect(store.events).toHaveLength(0)
    expect(store.previewVersion).toBeNull()
  })
})
