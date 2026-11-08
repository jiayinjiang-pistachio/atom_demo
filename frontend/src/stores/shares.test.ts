import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { PublicShare, ShareSummary } from '@/api/types'

const mocks = vi.hoisted(() => ({
  listShares: vi.fn(),
  createShare: vi.fn(),
  revokeShare: vi.fn(),
  getPublicShare: vi.fn(),
  ensure: vi.fn(async () => {}),
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

vi.mock('@/api/shares', () => ({
  listShares: mocks.listShares,
  createShare: mocks.createShare,
  revokeShare: mocks.revokeShare,
  getPublicShare: mocks.getPublicShare,
}))

vi.mock('@/stores/guest', () => ({
  useGuestStore: () => ({ ensure: mocks.ensure }),
}))

import { useSharesStore } from './shares'

function share(slug: string, version = 2): ShareSummary {
  return {
    slug,
    version,
    created_at: '2026-01-01T00:00:00Z',
    expires_at: '2026-01-08T00:00:00Z',
    revoked: false,
  }
}

function publicShare(): PublicShare {
  return {
    slug: 'public-1',
    title: '看板',
    version: 2,
    entry: 'index.html',
    created_at: '2026-01-01T00:00:00Z',
    expires_at: null,
  }
}

describe('shares store', () => {
  let store: ReturnType<typeof useSharesStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useSharesStore()
    vi.clearAllMocks()
    mocks.ensure.mockResolvedValue(undefined)
    mocks.listShares.mockResolvedValue([share('share-1')])
  })

  it('loads active shares', async () => {
    await store.load('project-1')

    expect(mocks.listShares).toHaveBeenCalledWith('project-1')
    expect(store.items).toHaveLength(1)
    expect(store.loading).toBe(false)
  })

  it('creates a share and prepends it', async () => {
    await store.load('project-1')
    mocks.createShare.mockResolvedValueOnce(share('share-2', 3))

    const created = await store.create('project-1', { version: 3, expires_in_days: 30 })

    expect(created?.slug).toBe('share-2')
    expect(store.items.map((item) => item.slug)).toEqual(['share-2', 'share-1'])
    expect(store.creating).toBe(false)
  })

  it('records an error when creation fails', async () => {
    mocks.createShare.mockRejectedValueOnce(new Error('分享数量已达上限'))

    const created = await store.create('project-1', { expires_in_days: 7 })

    expect(created).toBeNull()
    expect(store.error).toBe('分享数量已达上限')
  })

  it('revokes a share and removes it from the list', async () => {
    mocks.revokeShare.mockResolvedValueOnce(undefined)

    const ok = await store.revoke('project-1', 'share-1')

    expect(ok).toBe(true)
    expect(store.items).toEqual([])
    expect(store.revoking).toBe(false)
  })

  it('record a revoked error without dropping the row', async () => {
    await store.load('project-1')
    mocks.revokeShare.mockRejectedValueOnce(new Error('撤销失败'))

    const ok = await store.revoke('project-1', 'share-1')

    expect(ok).toBe(false)
    expect(store.items).toHaveLength(1)
    expect(store.error).toBe('撤销失败')
  })

  it('loads public metadata without guest bootstrap', async () => {
    mocks.getPublicShare.mockResolvedValueOnce(publicShare())

    await store.loadPublic('public-1')

    expect(mocks.getPublicShare).toHaveBeenCalledWith('public-1')
    expect(mocks.ensure).not.toHaveBeenCalled()
    expect(store.publicShare?.title).toBe('看板')
    expect(store.publicMissing).toBe(false)
  })

  it('maps 404 into the missing state', async () => {
    const { ApiError } = await import('@/api/client')
    mocks.getPublicShare.mockRejectedValueOnce(new ApiError(404, 'not found'))

    await store.loadPublic('gone')

    expect(store.publicMissing).toBe(true)
    expect(store.publicError).toBeNull()
    expect(store.publicShare).toBeNull()
  })

  it('maps other public errors into an error state', async () => {
    mocks.getPublicShare.mockRejectedValueOnce(new Error('服务不可用'))

    await store.loadPublic('public-1')

    expect(store.publicMissing).toBe(false)
    expect(store.publicError).toBe('服务不可用')
  })
})
