// Mirrors the Pydantic schemas in packages/shared/schemas/. Keep field names
// identical so API responses deserialize without mapping.

export type Domain = 'director_os' | 'brand_os' | 'interview_os' | 'one_on_one_os' | 'auto'

export type WorkflowDomain = Exclude<Domain, 'auto'>

// ── Shared grounding primitives (schemas/base.py) ──────────────────────────

export interface GroundedItem {
  text: string
  source: string
  line_number: number
}

export interface EvidenceItem {
  source: string
  line_number: number
  title: string
  excerpt: string
}

interface BaseResponse {
  evidence: EvidenceItem[]
  provider_usage?: Record<string, number>
}

// ── Domain responses ───────────────────────────────────────────────────────

export interface WeeklyUpdateResponse extends BaseResponse {
  summary: string
  wins: GroundedItem[]
  risks: GroundedItem[]
  next_steps: GroundedItem[]
}

export interface BrandContentDraftResponse extends BaseResponse {
  insight_summary: string
  post_outline: GroundedItem[]
  podcast_angles: GroundedItem[]
  repo_improvements: GroundedItem[]
}

export interface InterviewBriefResponse extends BaseResponse {
  candidate_summary: string
  key_questions: GroundedItem[]
  talking_points: GroundedItem[]
  red_flags: GroundedItem[]
}

export interface OneOnOneResponse extends BaseResponse {
  meeting_summary: string
  action_items: GroundedItem[]
  talking_points: GroundedItem[]
  blockers: GroundedItem[]
  kudos: GroundedItem[]
}

export type DomainResponse =
  | WeeklyUpdateResponse
  | BrandContentDraftResponse
  | InterviewBriefResponse
  | OneOnOneResponse

export function isWeeklyUpdate(r: DomainResponse): r is WeeklyUpdateResponse {
  return 'wins' in r
}

export function isBrandDraft(r: DomainResponse): r is BrandContentDraftResponse {
  return 'post_outline' in r
}

export function isInterviewBrief(r: DomainResponse): r is InterviewBriefResponse {
  return 'key_questions' in r
}

export function isOneOnOne(r: DomainResponse): r is OneOnOneResponse {
  return 'action_items' in r
}

export function getSummary(r: DomainResponse): string {
  if (isWeeklyUpdate(r)) return r.summary
  if (isBrandDraft(r)) return r.insight_summary
  if (isInterviewBrief(r)) return r.candidate_summary
  if (isOneOnOne(r)) return r.meeting_summary
  return ''
}

// ── Orchestrator (schemas/orchestrator.py) ─────────────────────────────────

export interface AgentCall {
  agent: string
  model: string
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens: number
  cache_creation_input_tokens: number
}

export interface WorkflowTrace {
  data_path: string
  focus_used: string | null
  evidence_count: number
  evidence_sources: string[]
  model_requested: boolean
  model_supported: boolean
  model_used: boolean
  provider_used: string | null
  model_id_used: string | null
  fallback_used: boolean
  section_counts: Record<string, number>
  validation_summary: string
  routing_model: string
  cache_read_input_tokens: number
  cache_creation_input_tokens: number
  mcp_tool_calls: Record<string, unknown>[]
  mcp_fallback_reason: string | null
  agent_calls: AgentCall[]
}

// Present only when use_mcp=true and every item cited a line the model read.
export interface McpSynthesis {
  summary: string
  items: GroundedItem[]
  evidence: EvidenceItem[]
}

export interface OrchestratorResponse {
  selected_workflow: string
  rationale: string
  trace: WorkflowTrace
  result: DomainResponse
  formatted_content: string | null
  mcp_result: McpSynthesis | null
  mcp_synthesis: string | null
}

// Normalized shape the UI renders for both direct domain calls and /orchestrate.
// Direct calls have no trace wrapper, so trace and rationale are optional.
export interface WorkflowResult {
  workflow: string
  rationale?: string
  trace?: WorkflowTrace
  result: DomainResponse
  formattedContent?: string | null
  mcpResult?: McpSynthesis | null
}

// ── Planner (schemas/planner.py) ───────────────────────────────────────────

export type PlannerKind = 'rules' | 'ollama' | 'claude'

export interface PlanStep {
  step_id: number
  workflow_id: string
  tool_name: string
  tool_input: Record<string, unknown>
  rationale: string
}

export interface Plan {
  goal: string
  steps: PlanStep[]
  planner_requested: PlannerKind
  planner_used: string
  fallback_reason: string | null
  notes: string[]
}

export interface StepResult {
  step_id: number
  workflow_id: string
  status: 'ok' | 'error'
  error: string | null
  trace: WorkflowTrace | null
  result: DomainResponse | null
}

export interface PlanResponse {
  goal: string
  status: 'ok' | 'partial' | 'error'
  plan: Plan
  steps: StepResult[]
  validation_summary: string
  planner_usage: Record<string, number>
}

// ── UI configuration ───────────────────────────────────────────────────────

export interface SectionDef {
  key: string
  label: string
  variant?: 'default' | 'risk' | 'positive'
}

export type ExtraField = 'candidate_name' | 'role' | 'direct_report'

export interface DomainConfig {
  label: string
  description: string
  // POST path for a direct domain call; null for auto, which goes through /orchestrate.
  endpoint: string | null
  defaultPath: string
  defaultPrompt: string
  sections: SectionDef[]
  extraFields: ExtraField[]
  // Brand, Interview, and One-on-One OS are Claude-only.
  supportsOllama: boolean
}

export const DOMAIN_CONFIG: Record<Domain, DomainConfig> = {
  director_os: {
    label: 'Director OS',
    description: 'Project notes → wins, risks, and next steps for a weekly leadership update.',
    endpoint: '/director-os/weekly-update',
    defaultPath: 'data/local_only/projects',
    defaultPrompt: '',
    sections: [
      { key: 'wins',       label: 'Wins',       variant: 'positive' },
      { key: 'risks',      label: 'Risks',      variant: 'risk'     },
      { key: 'next_steps', label: 'Next Steps', variant: 'default'  },
    ],
    extraFields: [],
    supportsOllama: true,
  },
  brand_os: {
    label: 'Brand OS',
    description: 'Technical work notes → post outlines, podcast angles, and repo improvements.',
    endpoint: '/brand-os/content-draft',
    defaultPath: 'data/local_only/brand',
    defaultPrompt: '',
    sections: [
      { key: 'post_outline',      label: 'Post Outline',      variant: 'default'  },
      { key: 'podcast_angles',    label: 'Podcast Angles',    variant: 'positive' },
      { key: 'repo_improvements', label: 'Repo Improvements', variant: 'default'  },
    ],
    extraFields: [],
    supportsOllama: false,
  },
  interview_os: {
    label: 'Interview OS',
    description: 'Hiring notes → candidate brief with key questions, talking points, and red flags.',
    endpoint: '/interview-os/brief',
    defaultPath: 'data/local_only/interviews',
    defaultPrompt: '',
    sections: [
      { key: 'key_questions',  label: 'Key Questions',  variant: 'default'  },
      { key: 'talking_points', label: 'Talking Points', variant: 'positive' },
      { key: 'red_flags',      label: 'Red Flags',      variant: 'risk'     },
    ],
    extraFields: ['candidate_name', 'role'],
    supportsOllama: false,
  },
  one_on_one_os: {
    label: 'One-on-One OS',
    description: 'Direct report notes → meeting brief with action items, blockers, and kudos.',
    endpoint: '/one-on-one/brief',
    defaultPath: 'data/local_only/one_on_one',
    defaultPrompt: '',
    sections: [
      { key: 'action_items',   label: 'Action Items',   variant: 'default'  },
      { key: 'talking_points', label: 'Talking Points', variant: 'positive' },
      { key: 'blockers',       label: 'Blockers',       variant: 'risk'     },
      { key: 'kudos',          label: 'Kudos',          variant: 'positive' },
    ],
    extraFields: ['direct_report'],
    supportsOllama: false,
  },
  auto: {
    label: 'Auto',
    description: 'Describe what you need; the Chief of Staff router picks the domain (/orchestrate).',
    endpoint: null,
    defaultPath: 'data/local_only/projects',
    defaultPrompt: 'Summarize this week\'s wins, risks, and next steps for leadership',
    // Sections are inferred from the routed domain's response shape.
    sections: [],
    extraFields: [],
    supportsOllama: true,
  },
}

// API workflow ids are "<domain>.<workflow>", e.g. "interview_os.brief".
export function domainConfigFor(workflowId: string): DomainConfig | undefined {
  const domain = workflowId.split('.')[0] as WorkflowDomain
  return domain in DOMAIN_CONFIG ? DOMAIN_CONFIG[domain] : undefined
}

export function sectionsFor(workflowId: string): SectionDef[] {
  return domainConfigFor(workflowId)?.sections ?? []
}
