import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { VersionDiff, VersionSummary } from '@/api/types'

const mocks = vi.hoisted(() => ({
  listVersions: vi.fn(),
  diffVersions: vi.fn(),
  restoreVersion: vi.fn(),
  exportVersion: vi.fn(),
  ensure: vi.fn(async () => {}),
  invalidate: vi.fn(),
  loadProject: vi.fn(async () => {}),
}))

vi.mock('@/api/client', () => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
    }
  },
}))

vi.mock('@/api/versions', () => ({
  listVersions: mocks.listVersions,
  diffVersions: mocks.diffVersions,
  restoreVersion: mocks.restoreVersion,
  exportVersion: mocks.exportVersion,
}))

vi.mock('@/stores/guest', () => ({
  useGuestStore: () => ({ ensure: mocks.ensure, invalidate: mocks.invalidate }),
}))

vi.mock('@/stores/projects', () => ({
  useProjectsStore: () => ({ loadProject: mocks.loadProject }),
}))

import { useVersionsStore } from './versions'

function version(number: number, isCurrent = false): VersionSummary {
  return {
    number,
    label: `v${number}`,
    source: 'agent',
    created_at: '2026-01-01T00:00:00Z',
    file_count: 2,
    total_bytes: 120,
    is_current: isCurrent,
  }
}

function diff(): VersionDiff {
  return {
    from_version: 1,
    to_version: 2,
    files: [
      { path: 'index.html', change: 'modified', additions: 1, deletions: 1, diff: '@@ -1 +1 @@' },
    ],
    summary: {
      files_added: 0,
      files_removed: 0,
      files_modified: 1,
      additions: 1,
      deletions: 1,
    },
  }
}

describe('versions store', () => {
  let store: ReturnType<typeof useVersionsStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useVersionsStore()
    vi.clearAllMocks()
    mocks.ensure.mockResolvedValue(undefined)
    mocks.listVersions.mockResolvedValue([version(2, true), version(1)])
  })

  it('loads versions and exposes the current one', async () => {
    await store.load('project-1')

    expect(mocks.listVersions).toHaveBeenCalledWith('project-1')
    expect(store.items).toHaveLength(2)
    expect(store.current?.number).toBe(2)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('maps a load failure into an error state', async () => {
    mocks.listVersions.mockRejectedValueOnce(new Error('网络异常'))

    await store.load('project-1')

    expect(store.items).toEqual([])
    expect(store.error).toBe('网络异常')
  })

  it('retries once with a fresh guest token after a 401', async () => {
    const { ApiError } = await import('@/api/client')
    mocks.listVersions.mockRejectedValueOnce(new ApiError(401, 'unauthorized'))

    await store.load('project-1')

    expect(mocks.invalidate).toHaveBeenCalled()
    expect(mocks.listVersions).toHaveBeenCalledTimes(2)
    expect(store.error).toBeNull()
  })

  it('loads a diff and clears it', async () => {
    mocks.diffVersions.mockResolvedValueOnce(diff())

    await store.loadDiff('project-1', 1, 2)

    expect(mocks.diffVersions).toHaveBeenCalledWith('project-1', 1, 2)
    expect(store.diff?.summary.files_modified).toBe(1)

    store.clearDiff()
    expect(store.diff).toBeNull()
  })

  it('maps a diff failure into an error state', async () => {
    mocks.diffVersions.mockRejectedValueOnce(new Error('对比失败'))

    await store.loadDiff('project-1', 1, 2)

    expect(store.diff).toBeNull()
    expect(store.error).toBe('对比失败')
  })

  it('restores a version, refreshes the project and version list', async () => {
    const restored = version(3, true)
    mocks.restoreVersion.mockResolvedValueOnce(restored)
    mocks.listVersions.mockResolvedValueOnce([restored, version(2), version(1)])

    const result = await store.restore('project-1', 1)

    expect(result?.number).toBe(3)
    expect(mocks.loadProject).toHaveBeenCalledWith('project-1', true)
    expect(mocks.listVersions).toHaveBeenCalledWith('project-1')
    expect(store.restoring).toBe(false)
  })

  it('returns null and records the error when restore fails', async () => {
    mocks.restoreVersion.mockRejectedValueOnce(new Error('版本正在生成中'))

    const result = await store.restore('project-1', 1)

    expect(result).toBeNull()
    expect(store.error).toBe('版本正在生成中')
    expect(store.restoring).toBe(false)
  })

  it('exports a version and resets state', async () => {
    await store.exportVersion('project-1', 2)

    expect(mocks.exportVersion).toHaveBeenCalledWith('project-1', 2)
    expect(store.exporting).toBe(false)

    store.reset()
    expect(store.items).toEqual([])
    expect(store.diff).toBeNull()
  })
})
