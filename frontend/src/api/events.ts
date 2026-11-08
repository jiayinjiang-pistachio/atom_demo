import { fetchEventSource } from '@microsoft/fetch-event-source'

import { buildApiUrl, readGuestToken } from '@/api/client'
import type { RunStreamEvent } from '@/api/types'

export interface StreamHandlers {
  onEvent: (event: RunStreamEvent) => void
  onError: (message: string) => void
  onClose?: () => void
}

export type RunStreamHandlers = StreamHandlers
export type MessageStreamHandlers = StreamHandlers

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
  const url = buildApiUrl(
    `/api/v1/runs/${runId}/events${afterSeq > 0 ? `?after_seq=${afterSeq}` : ''}`,
  )
  return openEventStream(
    url,
    {
      method: 'GET',
      headers: {
        Accept: 'text/event-stream',
        ...authHeader(),
      },
    },
    handlers,
    (status) =>
      status === 401 ? '访客身份失效，请刷新页面' : `事件流连接失败 (${status})`,
  )
}

export function openMessageStream(
  projectId: string,
  message: string,
  handlers: MessageStreamHandlers,
): () => void {
  return openEventStream(
    buildApiUrl(`/api/v1/projects/${projectId}/messages/stream`),
    {
      method: 'POST',
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
        ...authHeader(),
      },
      body: JSON.stringify({ message }),
    },
    handlers,
    messageStreamError,
  )
}

interface StreamRequestInit {
  method: string
  headers: Record<string, string>
  body?: string
}

function openEventStream(
  url: string,
  init: StreamRequestInit,
  handlers: StreamHandlers,
  errorForStatus: (status: number) => string,
): () => void {
  const controller = new AbortController()

  void fetchEventSource(url, {
    ...init,
    signal: controller.signal,
    openWhenHidden: true,
    async onopen(response) {
      if (response.ok) {
        return
      }
      const message = errorForStatus(response.status)
      handlers.onError(message)
      throw new FatalStreamError(message, response.status)
    },
    onmessage(event) {
      if (!event.event || event.data === undefined) {
        return
      }
      let data: Record<string, unknown>
      try {
        data = JSON.parse(event.data) as Record<string, unknown>
      } catch {
        return
      }
      handlers.onEvent({
        seq: Number(event.id ?? 0),
        type: event.event,
        data,
      })
    },
    onerror(error) {
      handlers.onError(error instanceof Error ? error.message : '事件流连接异常')
      // Throwing prevents fetch-event-source from auto-retrying a POST that
      // may already have persisted a message or started a run.
      throw error
    },
    onclose() {
      handlers.onClose?.()
    },
  })

  return () => controller.abort()
}

function authHeader(): Record<string, string> {
  const token = readGuestToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function messageStreamError(status: number): string {
  if (status === 401) {
    return '访客身份失效，请刷新页面'
  }
  if (status === 404) {
    return '项目不存在或无权访问'
  }
  if (status === 409) {
    return '已有生成任务在进行中，请稍候'
  }
  if (status === 422) {
    return '消息内容不合法'
  }
  return `请求失败 (${status})`
}
