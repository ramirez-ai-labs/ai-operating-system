import type {
  Domain,
  DomainResponse,
  OrchestratorResponse,
  PlannerKind,
  PlanResponse,
  WorkflowResult,
} from './types'
import { DOMAIN_CONFIG } from './types'

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

export interface FormValues {
  domain: Domain
  data_path: string
  focus: string
  max_documents: number
  use_model: boolean
  provider: 'claude' | 'ollama'
  use_mcp: boolean
  target_audience: string
  prompt: string
  candidate_name: string
  role: string
  direct_report: string
}

export interface PlanFormValues {
  goal: string
  planner: PlannerKind
  max_steps: number
  use_model: boolean
  provider: 'claude' | 'ollama'
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: 'no-store' })
    return res.ok
  } catch {
    return false
  }
}

// FastAPI returns `detail` as a string for 400s and as a list of field errors for 422s.
function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const loc = Array.isArray(d?.loc) ? d.loc.filter((p: unknown) => p !== 'body').join('.') : ''
        return loc ? `${loc}: ${d?.msg}` : String(d?.msg ?? d)
      })
      .join('; ')
  }
  return JSON.stringify(detail)
}

async function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    throw new Error(`Cannot reach the API at ${API_URL}. Start it with: uvicorn apps.api.main:app --reload --env-file .env`)
  }
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const data = await res.json()
      if (data?.detail !== undefined) message = formatDetail(data.detail)
    } catch {
      // Non-JSON error body; keep the status line.
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

// Empty form fields are sent as null so the API applies its own defaults.
function orNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

export async function runWorkflow(values: FormValues): Promise<WorkflowResult> {
  const common = {
    data_path: values.data_path,
    focus: orNull(values.focus),
    max_documents: values.max_documents,
    use_model: values.use_model,
    provider: values.provider,
  }

  if (values.domain === 'auto') {
    const res = await post<OrchestratorResponse>('/orchestrate', {
      ...common,
      prompt: orNull(values.prompt),
      use_mcp: values.use_mcp,
      target_audience: orNull(values.target_audience),
    })
    return {
      workflow: res.selected_workflow,
      rationale: res.rationale,
      trace: res.trace,
      result: res.result,
      formattedContent: res.formatted_content,
      mcpResult: res.mcp_result,
    }
  }

  const cfg = DOMAIN_CONFIG[values.domain]
  const body: Record<string, unknown> = { ...common }
  for (const field of cfg.extraFields) {
    body[field] = orNull(values[field])
  }
  const result = await post<DomainResponse>(cfg.endpoint as string, body)
  return { workflow: values.domain, result }
}

export async function runPlan(values: PlanFormValues): Promise<PlanResponse> {
  return post<PlanResponse>('/plan', {
    goal: values.goal,
    planner: values.planner,
    max_steps: values.max_steps,
    use_model: values.use_model,
    provider: values.provider,
  })
}
