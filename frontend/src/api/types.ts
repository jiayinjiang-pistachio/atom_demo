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
