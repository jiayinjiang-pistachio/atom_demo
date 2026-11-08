import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ApiError,
  buildApiUrl,
  buildShareAppUrl,
  buildSharePageUrl,
  buildSharePreviewUrl,
  filenameFromDisposition,
  getBlob,
  getJson,
} from './client'

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

describe('buildSharePageUrl', () => {
  it('builds the standard share page url', () => {
    expect(buildSharePageUrl('slug-1', 'https://atom.example.com')).toBe(
      'https://atom.example.com/s/slug-1',
    )
  })

  it('encodes the slug', () => {
    expect(buildSharePageUrl('abc/def', 'https://atom.example.com/')).toBe(
      'https://atom.example.com/s/abc%2Fdef',
    )
  })
})

describe('buildShareAppUrl', () => {
  it('builds the bare app url under the same share', () => {
    expect(buildShareAppUrl('slug-1', 'https://atom.example.com')).toBe(
      'https://atom.example.com/s/slug-1/app',
    )
  })

  it('falls back to a relative url without an origin', () => {
    expect(buildShareAppUrl('slug-1')).toBe('/s/slug-1/app')
  })
})

describe('buildSharePreviewUrl', () => {
  it('encodes the slug and each path segment', () => {
    expect(buildSharePreviewUrl('abc/def', 'nested dir/index.html')).toBe(
      'http://localhost:8000/share-preview/abc%2Fdef/nested%20dir/index.html',
    )
  })

  it('defaults to index.html', () => {
    expect(buildSharePreviewUrl('slug-1')).toBe(
      'http://localhost:8000/share-preview/slug-1/index.html',
    )
  })
})

describe('filenameFromDisposition', () => {
  it('reads a quoted filename', () => {
    expect(filenameFromDisposition('attachment; filename="atom-1-v2.zip"')).toBe('atom-1-v2.zip')
  })

  it('reads an unquoted filename', () => {
    expect(filenameFromDisposition('attachment; filename=atom-1-v2.zip')).toBe('atom-1-v2.zip')
  })

  it('returns null without a filename', () => {
    expect(filenameFromDisposition(null)).toBeNull()
  })
})

describe('getBlob', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns the blob with the response filename', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('zip-bytes', {
          status: 200,
          headers: { 'Content-Disposition': 'attachment; filename="atom-1-v3.zip"' },
        }),
      ),
    )

    const result = await getBlob('/api/v1/projects/1/export?version=3')

    expect(result.filename).toBe('atom-1-v3.zip')
    expect(await result.blob.text()).toBe('zip-bytes')
  })

  it('throws ApiError when the export fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ message: '没有该版本' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(getBlob('/api/v1/projects/1/export?version=99')).rejects.toMatchObject({
      status: 404,
      message: '没有该版本',
    })
  })
})
