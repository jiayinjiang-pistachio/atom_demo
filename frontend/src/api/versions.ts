import { downloadFile, getBlob, getJson, postJson } from '@/api/client'
import type { VersionDiff, VersionSummary } from '@/api/types'

function versionsPath(projectId: string): string {
  return `/api/v1/projects/${projectId}/versions`
}

export function listVersions(projectId: string): Promise<VersionSummary[]> {
  return getJson<VersionSummary[]>(versionsPath(projectId))
}

export function diffVersions(
  projectId: string,
  fromVersion: number,
  toVersion: number,
): Promise<VersionDiff> {
  return getJson<VersionDiff>(
    `${versionsPath(projectId)}/${fromVersion}/diff/${toVersion}`,
  )
}

export function restoreVersion(projectId: string, number: number): Promise<VersionSummary> {
  return postJson<VersionSummary>(`${versionsPath(projectId)}/${number}/restore`, {})
}

export async function exportVersion(
  projectId: string,
  version?: number,
): Promise<string | null> {
  const query = version === undefined ? '' : `?version=${version}`
  const { blob, filename } = await getBlob(`/api/v1/projects/${projectId}/export${query}`)
  downloadFile(blob, filename)
  return filename
}
