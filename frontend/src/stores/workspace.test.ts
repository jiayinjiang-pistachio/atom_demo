import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { StreamHandlers } from '@/api/events'
import type { ProjectDetail, RunStreamEvent, RunSummary } from '@/api/types'

const mocks = vi.hoisted(() => ({
  runHandlers: [] as StreamHandlers[],
  messageHandlers: [] as StreamHandlers[],
  abortRun: vi.fn(),
  abortMessage: vi.fn(),
  postJson: vi.fn(),
  ensure: vi.fn(async () => {}),
  loadProject: vi.fn<(_projectId: string, _quiet?: boolean) => Promise<void>>(async () => {}),
  current: null as ProjectDetail | null,
}))

vi.mock('@/api/events', () => ({
  openRunStream: vi.fn((_runId: string, handlers: StreamHandlers) => {
    mocks.runHandlers.push(handlers)
    return mocks.abortRun
  }),
  openMessageStream: vi.fn(
    (_projectId: string, _message: string, handlers: StreamHandlers) => {
      mocks.messageHandlers.push(handlers)
      return mocks.abortMessage
    },
  ),
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
  useProjectsStore: () => ({
    loadProject: mocks.loadProject,
    get current() {
      return mocks.current
    },
  }),
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

function runSummary(overrides: Partial<RunSummary> = {}): RunSummary {
  return {
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
    ...overrides,
  }
}

function runEvent(type: string, data: Record<string, unknown> = {}): RunStreamEvent {
  return { seq: 1, type, data }
}

function latestRunHandlers(): StreamHandlers {
  const handlers = mocks.runHandlers.at(-1)
  if (!handlers) {
    throw new Error('run stream was not subscribed')
  }
  return handlers
}

function latestMessageHandlers(): StreamHandlers {
  const handlers = mocks.messageHandlers.at(-1)
  if (!handlers) {
    throw new Error('message stream was not opened')
  }
  return handlers
}

function emitBuildIntent(run: RunSummary = runSummary()): void {
  latestMessageHandlers().onEvent(
    runEvent('message.intent', { kind: 'build', run, user_message_id: 1 }),
  )
}

function tick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('workspace store', () => {
  let store: ReturnType<typeof useWorkspaceStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useWorkspaceStore()
    mocks.runHandlers = []
    mocks.messageHandlers = []
    mocks.abortRun.mockClear()
    mocks.abortMessage.mockClear()
    mocks.ensure.mockClear()
    mocks.loadProject.mockClear()
    mocks.postJson.mockReset()
    mocks.current = null
  })

  afterEach(() => {
    store.reset()
    vi.useRealTimers()
  })

  it('initializes from the project detail and reconnects an active run', () => {
    const detail = project({ latest_run: runSummary({ status: 'running' }) })

    store.init(detail)

    expect(store.runStatus).toBe('running')
    expect(store.previewVersion).toBe(1)
    expect(store.active).toBe(true)
    expect(mocks.runHandlers).toHaveLength(1)
  })

  it('surfaces the last failure message on init', () => {
    store.init(
      project({
        latest_run: runSummary({
          status: 'failed',
          error_code: 'llm_error',
          error_message: '模型暂时不可用',
        }),
      }),
    )

    expect(store.runStatus).toBe('failed')
    expect(store.error).toBe('模型暂时不可用')
  })

  it('switches to the run stream when the intent is build', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')
    emitBuildIntent()

    expect(store.replying).toBe(false)
    expect(store.runStatus).toBe('queued')
    expect(store.run?.id).toBe('run-1')
    expect(mocks.runHandlers).toHaveLength(1)
    expect(mocks.abortMessage).toHaveBeenCalledTimes(1)
  })

  it('accumulates assistant deltas and applies plan updates', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')
    emitBuildIntent()

    const handlers = latestRunHandlers()
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
    emitBuildIntent()

    const handlers = latestRunHandlers()
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

  it('streams a chat reply without creating a run or version', async () => {
    await store.start('你好', 'project-1')

    const handlers = latestMessageHandlers()
    handlers.onEvent(runEvent('message.intent', { kind: 'chat', run: null, user_message_id: 1 }))
    handlers.onEvent(runEvent('assistant.delta', { text: '你好' }))
    handlers.onEvent(runEvent('assistant.delta', { text: '呀' }))

    expect(store.replying).toBe(true)
    expect(store.runStatus).toBe('idle')
    expect(store.assistantText).toBe('你好呀')
    expect(mocks.runHandlers).toHaveLength(0)

    mocks.current = project({
      messages: [
        {
          id: 1,
          role: 'user',
          content: '你好',
          run_id: null,
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 2,
          role: 'assistant',
          content: '你好呀',
          run_id: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    })
    handlers.onEvent(runEvent('chat.done', { reply: '你好呀', assistant_message_id: 2 }))
    await tick()

    expect(store.replying).toBe(false)
    expect(store.assistantText).toBe('')
    expect(store.error).toBeNull()
    expect(mocks.loadProject).toHaveBeenCalledWith('project-1', true)
  })

  it('reports a chat stream failure and clears the pending state', async () => {
    await store.start('你好', 'project-1')
    const handlers = latestMessageHandlers()

    handlers.onEvent(runEvent('error', { message: '回复失败，请稍后重试' }))

    expect(store.error).toBe('回复失败，请稍后重试')
    expect(store.replying).toBe(false)
  })

  it('reports a dropped message stream', async () => {
    await store.start('你好', 'project-1')

    latestMessageHandlers().onClose?.()

    expect(store.replying).toBe(false)
    expect(store.error).toBe('对话连接已断开，请重试')
  })

  it('closes the run stream and clears transient text on a terminal status', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')
    emitBuildIntent()

    const handlers = latestRunHandlers()
    handlers.onEvent(runEvent('assistant.delta', { text: '临时流式内容' }))
    handlers.onEvent(
      runEvent('plan.updated', {
        steps: [{ title: '写入文件', status: 'in_progress' }],
      }),
    )
    handlers.onEvent(runEvent('run.status', { status: 'succeeded' }))

    expect(store.runStatus).toBe('succeeded')
    expect(store.assistantText).toBe('')
    expect(store.active).toBe(false)
    expect(store.plan.map((step) => step.status)).toEqual(['done'])
    expect(mocks.abortRun).toHaveBeenCalledTimes(1)
  })

  it('stops the plan spinner when a run fails', async () => {
    store.init(project())
    await store.start('做一个看板', 'project-1')
    emitBuildIntent()

    const handlers = latestRunHandlers()
    handlers.onEvent(
      runEvent('plan.updated', {
        steps: [
          { title: '规划页面', status: 'in_progress' },
          { title: '写入文件', status: 'pending' },
        ],
      }),
    )
    handlers.onEvent(
      runEvent('run.status', { status: 'failed', error: '模型输出被截断，请缩小单个文件后重试' }),
    )

    expect(store.runStatus).toBe('failed')
    expect(store.error).toBe('模型输出被截断，请缩小单个文件后重试')
    expect(store.plan.map((step) => step.status)).toEqual(['pending', 'pending'])
    expect(store.active).toBe(false)
  })

  it('reset tears down both streams and clears state', async () => {
    store.init(project())
    await store.start('你好', 'project-1')
    latestMessageHandlers().onEvent(
      runEvent('message.intent', { kind: 'chat', run: null, user_message_id: 1 }),
    )
    store.reset()

    expect(mocks.abortMessage).toHaveBeenCalled()
    expect(store.runStatus).toBe('idle')
    expect(store.events).toHaveLength(0)
    expect(store.previewVersion).toBeNull()
    expect(store.replying).toBe(false)
  })
})
