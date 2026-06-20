import type { WorkflowTrace, AgentCall } from '@/lib/types'

interface Props {
  workflow: string
  rationale?: string
  trace?: WorkflowTrace
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-1.5 border-b border-aios-line/50 last:border-0">
      <span className="min-w-[110px] text-[11px] font-semibold uppercase tracking-widest text-aios-muted shrink-0">
        {label}
      </span>
      <span className="text-sm text-aios-ink leading-relaxed">{value}</span>
    </div>
  )
}

function Flag({ value }: { value: boolean }) {
  return (
    <span className={value ? 'text-aios-accent font-semibold' : 'text-aios-muted'}>
      {value ? 'yes' : 'no'}
    </span>
  )
}

function AgentPipeline({ calls }: { calls: AgentCall[] }) {
  if (calls.length === 0) return null
  return (
    <div className="rounded-2xl border border-aios-line bg-aios-panel p-4">
      <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
        Agent Pipeline
      </p>
      <div className="flex flex-col gap-1">
        {calls.map((c, i) => (
          <div key={i}>
            <div className="rounded-xl border border-aios-accent/20 bg-white/60 p-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="font-semibold text-sm text-aios-ink">{c.agent}</span>
                <span className="font-mono text-[11px] text-aios-muted">{c.model}</span>
              </div>
              <div className="mt-1.5 flex gap-3 text-[11px] text-aios-muted flex-wrap">
                <span>in: {c.input_tokens.toLocaleString()}</span>
                <span>out: {c.output_tokens.toLocaleString()}</span>
                {c.cache_read_input_tokens > 0 && (
                  <span className="text-aios-accent font-semibold">
                    cache hit: {c.cache_read_input_tokens.toLocaleString()} tokens
                  </span>
                )}
              </div>
            </div>
            {i < calls.length - 1 && (
              <div className="py-0.5 pl-4 text-aios-muted text-xs">↓</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export function TracePane({ workflow, rationale, trace }: Props) {
  const cacheRead   = trace?.cache_read_input_tokens ?? 0
  const cacheCreate = trace?.cache_creation_input_tokens ?? 0

  return (
    <div className="flex flex-col gap-4">
      {/* Routing */}
      <div className="rounded-2xl border border-aios-line bg-aios-panel p-4">
        <p className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
          Routing
        </p>
        <Row label="Workflow"  value={<span className="font-mono text-xs">{workflow || '—'}</span>} />
        {rationale && <Row label="Rationale" value={rationale} />}
        {trace && <Row label="Router" value={<span className="font-mono text-xs">{trace.routing_model}</span>} />}
      </div>

      {/* Execution */}
      {trace && (
        <div className="rounded-2xl border border-aios-line bg-aios-panel p-4">
          <p className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
            Execution
          </p>
          <Row label="Evidence" value={`${trace.evidence_count} items`} />
          <Row label="Model used" value={<Flag value={trace.model_used} />} />
          {trace.model_used && trace.provider_used && (
            <Row label="Provider" value={
              <span className="font-mono text-xs">{trace.provider_used} / {trace.model_id_used ?? '—'}</span>
            } />
          )}
          <Row label="Fallback" value={<Flag value={trace.fallback_used} />} />
          {trace.validation_summary && (
            <Row label="Validation" value={<span className="text-xs">{trace.validation_summary}</span>} />
          )}
          <Row label="Data path" value={<span className="font-mono text-xs break-all">{trace.data_path}</span>} />

          {/* Cache metrics */}
          {(cacheRead > 0 || cacheCreate > 0) && (
            <div className="mt-2.5 rounded-xl border border-aios-accent/20 bg-aios-accent/5 p-3">
              {cacheRead > 0 ? (
                <div className="flex items-center gap-2">
                  <span className="text-aios-accent text-xs font-bold">⚡ Cache hit</span>
                  <span className="text-xs text-aios-accent">
                    {cacheRead.toLocaleString()} tokens saved
                  </span>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-aios-muted text-xs font-semibold">Cache primed</span>
                  <span className="text-xs text-aios-muted">
                    {cacheCreate.toLocaleString()} tokens stored
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Section counts */}
      {trace && Object.keys(trace.section_counts).length > 0 && (
        <div className="rounded-2xl border border-aios-line bg-aios-panel p-4">
          <p className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
            Section Counts
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(trace.section_counts).map(([k, v]) => (
              <div
                key={k}
                className="rounded-full border border-aios-line bg-aios-bg px-3 py-1 text-[11px]"
              >
                <span className="text-aios-muted">{k}</span>
                <span className="ml-1.5 font-bold text-aios-ink">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence sources */}
      {trace && trace.evidence_sources.length > 0 && (
        <div className="rounded-2xl border border-aios-line bg-aios-panel p-4">
          <p className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
            Evidence Sources
          </p>
          <ul className="flex flex-col gap-1">
            {trace.evidence_sources.map((src, i) => (
              <li key={i} className="font-mono text-[11px] text-aios-muted">
                {src}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Agent pipeline */}
      {trace && trace.agent_calls.length > 0 && (
        <AgentPipeline calls={trace.agent_calls} />
      )}
    </div>
  )
}
