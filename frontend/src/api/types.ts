export interface HealthResponse {
  status: 'ok' | 'degraded'
  database: 'ok' | 'down'
  version: string
}

export interface MetaResponse {
  name: string
  environment: string
  api_version: string
}

export interface GuestBootstrapResponse {
  guest_id: string
  token: string
}

export interface ProjectSummary {
  id: string
  title: string
  prompt: string
  entry_path: string
  status: string
  current_version: number | null
  created_at: string
  updated_at: string
}

export interface ProjectMessage {
  id: number
  role: string
  content: string
  run_id: string | null
  created_at: string
}

export interface ProjectFile {
  path: string
  content: string
  size: number
  updated_at: string
}

export interface RunSummary {
  id: string
  project_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  model: string
  tokens_in: number
  tokens_out: number
  error_code: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface ProjectDetail extends ProjectSummary {
  messages: ProjectMessage[]
  files: ProjectFile[]
  latest_run: RunSummary | null
}

export interface PlanStep {
  title: string
  status: 'pending' | 'in_progress' | 'done'
}

export interface RunStreamEvent {
  seq: number
  type: string
  data: Record<string, unknown>
}

export interface ProjectCreatePayload {
  prompt: string
  title?: string
}

export interface ProjectUpdatePayload {
  title: string
}

export interface RunCreatePayload {
  message: string
}

export interface VersionSummary {
  number: number
  label: string
  source: string
  created_at: string
  file_count: number
  total_bytes: number
  is_current: boolean
}

export type VersionChangeKind = 'added' | 'removed' | 'modified'

export interface VersionDiffFile {
  path: string
  change: VersionChangeKind
  additions: number
  deletions: number
  diff: string
}

export interface VersionDiffSummary {
  files_added: number
  files_removed: number
  files_modified: number
  additions: number
  deletions: number
}

export interface VersionDiff {
  from_version: number
  to_version: number
  files: VersionDiffFile[]
  summary: VersionDiffSummary
}

export interface ShareSummary {
  slug: string
  version: number
  created_at: string
  expires_at: string | null
  revoked: boolean
}

export interface ShareCreatePayload {
  version?: number | null
  expires_in_days: 7 | 30 | null
}

export interface PublicShare {
  slug: string
  title: string
  version: number
  entry: string
  created_at: string
  expires_at: string | null
}

export interface PromptOptimizeResult {
  original: string
  optimized: string
}
