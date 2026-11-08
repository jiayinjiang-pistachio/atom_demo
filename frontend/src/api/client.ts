const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
const PREVIEW_ORIGIN = (import.meta.env.VITE_PREVIEW_ORIGIN ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
)
const GUEST_TOKEN_STORAGE_KEY = 'atom.guest_token'

export class ApiError extends Error {
  readonly status: number
  readonly requestId: string | undefined

  constructor(status: number, message: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.requestId = requestId
  }
}

export function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

export function buildPreviewUrl(
  projectId: string,
  version: number,
  path = 'index.html',
): string {
  return `${PREVIEW_ORIGIN}/preview/${projectId}/${version}/${path}`
}

export function buildSharePageUrl(slug: string, origin = ''): string {
  return `${origin.replace(/\/$/, '')}/s/${encodeURIComponent(slug)}`
}

export function buildShareAppUrl(slug: string, origin = ''): string {
  return `${buildSharePageUrl(slug, origin)}/app`
}

export function buildSharePreviewUrl(slug: string, path = 'index.html'): string {
  const safeSlug = encodeURIComponent(slug)
  const safePath = path
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/')
  return `${PREVIEW_ORIGIN}/share-preview/${safeSlug}/${safePath}`
}

export function readGuestToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  return window.localStorage.getItem(GUEST_TOKEN_STORAGE_KEY)
}

export function setGuestToken(token: string): void {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.setItem(GUEST_TOKEN_STORAGE_KEY, token)
}

export function clearGuestToken(): void {
  if (typeof window === 'undefined') {
    return
  }
  window.localStorage.removeItem(GUEST_TOKEN_STORAGE_KEY)
}

export interface JsonRequestOptions extends RequestInit {
  acceptedStatuses?: number[]
}

async function request<T>(path: string, options: JsonRequestOptions = {}): Promise<T> {
  const { acceptedStatuses = [], headers, ...init } = options
  const requestHeaders = new Headers(headers)
  requestHeaders.set('Accept', 'application/json')

  const token = readGuestToken()
  if (token) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(buildApiUrl(path), { ...init, headers: requestHeaders })

  if (!response.ok && !acceptedStatuses.includes(response.status)) {
    const payload = await readErrorPayload(response)
    throw new ApiError(
      response.status,
      payload.message,
      response.headers.get('X-Request-ID') ?? undefined,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export function getJson<T>(path: string, options: JsonRequestOptions = {}): Promise<T> {
  return request<T>(path, { ...options, method: options.method ?? 'GET' })
}

export function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function patchJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function deleteJson(path: string): Promise<void> {
  return request<void>(path, { method: 'DELETE' })
}

export interface BlobResponse {
  blob: Blob
  filename: string | null
}

export async function getBlob(path: string): Promise<BlobResponse> {
  const headers = new Headers()
  headers.set('Accept', 'application/zip, application/octet-stream')
  const token = readGuestToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(buildApiUrl(path), { headers })
  if (!response.ok) {
    const payload = await readErrorPayload(response)
    throw new ApiError(
      response.status,
      payload.message,
      response.headers.get('X-Request-ID') ?? undefined,
    )
  }

  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get('Content-Disposition')),
  }
}

export function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) {
    return null
  }
  const match = /filename="?([^";]+)"?/i.exec(disposition)
  return match?.[1]?.trim() ?? null
}

export function downloadFile(blob: Blob, filename: string | null): void {
  if (typeof document === 'undefined') {
    return
  }
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.href = url
  link.download = filename ?? 'download'
  link.rel = 'noopener'
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function readErrorPayload(response: Response): Promise<{ message: string }> {
  try {
    const body = (await response.json()) as { message?: string; detail?: string }
    return { message: body.message ?? body.detail ?? `请求失败 (${response.status})` }
  } catch {
    return { message: `请求失败 (${response.status})` }
  }
}
