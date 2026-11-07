import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, buildApiUrl, getJson } from './client'

describe('buildApiUrl', () => {
  it('keeps rooted paths stable', () => {
    expect(buildApiUrl('/healthz')).toBe('/healthz')
  })

  it('normalizes paths without a leading slash', () => {
    expect(buildApiUrl('healthz')).toBe('/healthz')
  })
})

describe('getJson', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('throws ApiError for non-accepted statuses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'boom' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(getJson('/broken')).rejects.toBeInstanceOf(ApiError)
  })

  it('accepts explicitly accepted statuses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ status: 'degraded' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    const body = await getJson<{ status: string }>('/healthz', { acceptedStatuses: [503] })

    expect(body.status).toBe('degraded')
  })
})
