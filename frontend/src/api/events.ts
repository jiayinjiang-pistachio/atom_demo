import { fetchEventSource } from '@microsoft/fetch-event-source'

import { buildApiUrl, readGuestToken } from '@/api/client'
import type { RunStreamEvent } from '@/api/types'

export interface RunStreamHandlers {
  onEvent: (event: RunStreamEvent) => void
  onError: (message: string) => void
  onClose?: () => void
}

class FatalStreamError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'FatalStreamError'
    this.status = status
  }
}

export function openRunStream(
  runId: string,
  handlers: RunStreamHandlers,
  afterSeq = 0,
): () => void {
  const controller = new AbortController()
  const token = readGuestToken()
  const url = buildApiUrl(
    `/api/v1/runs/${runId}/events${afterSeq > 0 ? `?after_seq=${afterSeq}` : ''}`,
  )

  void fetchEventSource(url, {
    method: 'GET',
    headers: {
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal: controller.signal,
    openWhenHidden: true,
    async onopen(response) {
      if (response.ok) {
        return
      }
      const message =
        response.status === 401 ? '访客身份失效，请刷新页面' : `事件流连接失败 (${response.status})`
      handlers.onError(message)
      throw new FatalStreamError(message, response.status)
    },
    onmessage(message) {
      if (!message.event || message.data === undefined) {
        return
      }
      let data: Record<string, unknown>
      try {
        data = JSON.parse(message.data) as Record<string, unknown>
      } catch {
        return
      }
      handlers.onEvent({
        seq: Number(message.id ?? 0),
        type: message.event,
        data,
      })
    },
    onerror(error) {
      handlers.onError(error instanceof Error ? error.message : '事件流连接异常')
      throw error
    },
    onclose() {
      handlers.onClose?.()
    },
  })

  return () => controller.abort()
}
