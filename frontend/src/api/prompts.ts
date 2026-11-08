import { postJson } from '@/api/client'
import type { PromptOptimizeResult } from '@/api/types'

export function optimizePrompt(
  projectId: string,
  message: string,
): Promise<PromptOptimizeResult> {
  return postJson<PromptOptimizeResult>(
    `/api/v1/projects/${projectId}/prompts/optimize`,
    { message },
  )
}
