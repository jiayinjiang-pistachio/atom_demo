import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { PromptOptimizeResult } from '@/api/types'

const mocks = vi.hoisted(() => ({
  postJson: vi.fn(),
  ensure: vi.fn(async () => {}),
}))

vi.mock('@/api/client', () => ({
  postJson: mocks.postJson,
}))

vi.mock('@/stores/guest', () => ({
  useGuestStore: () => ({ ensure: mocks.ensure }),
}))

import { usePromptsStore } from './prompts'

function deferred<T>(): {
  promise: Promise<T>
  resolve: (value: T) => void
  reject: (reason: unknown) => void
} {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function tick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

describe('prompts store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mocks.postJson.mockReset()
    mocks.ensure.mockReset()
    mocks.ensure.mockResolvedValue(undefined)
  })

  it('optimizes a draft and keeps original and result', async () => {
    const result: PromptOptimizeResult = {
      original: '做个待办',
      optimized: '做一个待办应用，支持新增、完成和删除任务。',
    }
    mocks.postJson.mockResolvedValue(result)
    const store = usePromptsStore()

    await store.optimize('project-1', '  做个待办  ')

    expect(mocks.postJson).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/prompts/optimize',
      { message: '做个待办' },
    )
    expect(mocks.ensure).toHaveBeenCalled()
    expect(store.original).toBe('做个待办')
    expect(store.optimized).toBe(result.optimized)
    expect(store.optimizing).toBe(false)
    expect(store.error).toBeNull()
  })

  it('surfaces the backend error message', async () => {
    mocks.postJson.mockRejectedValue(new Error('演示模式不支持优化，可直接发送原描述'))
    const store = usePromptsStore()

    await store.optimize('project-1', '做个待办')

    expect(store.error).toBe('演示模式不支持优化，可直接发送原描述')
    expect(store.optimizing).toBe(false)
  })

  it('ignores a second optimize while one is in flight', async () => {
    const pending = deferred<PromptOptimizeResult>()
    mocks.postJson.mockReturnValue(pending.promise)
    const store = usePromptsStore()

    const first = store.optimize('project-1', '做个待办')
    void store.optimize('project-1', '做个博客')
    await tick()

    expect(mocks.postJson).toHaveBeenCalledTimes(1)
    pending.resolve({ original: '做个待办', optimized: '优化后的待办' })
    await first

    expect(store.optimized).toBe('优化后的待办')
  })

  it('drops a late response after reset', async () => {
    const pending = deferred<PromptOptimizeResult>()
    mocks.postJson.mockReturnValue(pending.promise)
    const store = usePromptsStore()

    void store.optimize('project-1', '做个待办')
    await tick()
    store.reset()
    pending.resolve({ original: '做个待办', optimized: '迟到的结果' })
    await tick()

    expect(store.original).toBe('')
    expect(store.optimized).toBe('')
    expect(store.error).toBeNull()
    expect(store.optimizing).toBe(false)
  })

  it('reports guest bootstrap failures without calling the API', async () => {
    mocks.ensure.mockRejectedValue(new Error('无法创建访客身份'))
    const store = usePromptsStore()

    await store.optimize('project-1', '做个待办')

    expect(mocks.postJson).not.toHaveBeenCalled()
    expect(store.error).toBe('无法创建访客身份')
    expect(store.optimizing).toBe(false)
  })

  it('does nothing for an empty draft', async () => {
    const store = usePromptsStore()

    await store.optimize('project-1', '   ')

    expect(mocks.ensure).not.toHaveBeenCalled()
    expect(mocks.postJson).not.toHaveBeenCalled()
    expect(store.optimizing).toBe(false)
  })
})
