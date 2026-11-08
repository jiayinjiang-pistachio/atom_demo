import { deleteJson, getJson, postJson } from '@/api/client'
import type { PublicShare, ShareCreatePayload, ShareSummary } from '@/api/types'

function sharesPath(projectId: string): string {
  return `/api/v1/projects/${projectId}/shares`
}

export function listShares(projectId: string): Promise<ShareSummary[]> {
  return getJson<ShareSummary[]>(sharesPath(projectId))
}

export function createShare(
  projectId: string,
  payload: ShareCreatePayload,
): Promise<ShareSummary> {
  return postJson<ShareSummary>(sharesPath(projectId), payload)
}

export function revokeShare(projectId: string, slug: string): Promise<void> {
  return deleteJson(`${sharesPath(projectId)}/${slug}`)
}

export function getPublicShare(slug: string): Promise<PublicShare> {
  return getJson<PublicShare>(`/api/v1/shares/${slug}`)
}
