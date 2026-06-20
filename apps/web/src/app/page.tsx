'use client'

import { useState, useEffect, useCallback } from 'react'
import type { Domain, WorkflowResult } from '@/lib/types'
import { DOMAIN_CONFIG } from '@/lib/types'
import { runWorkflow, checkHealth } from '@/lib/api'
import type { FormValues } from '@/lib/api'
import { DomainTabs } from '@/components/DomainTabs'
import { WorkflowForm } from '@/components/WorkflowForm'
import { ResultsPane } from '@/components/ResultsPane'
import { TracePane } from '@/components/TracePane'

function defaultValues(domain: Domain): FormValues {
  const cfg = DOMAIN_CONFIG[domain]
  return {
    domain,
    data_path: cfg.defaultPath,
    focus: '',
    max_documents: 5,
    use_model: false,
    provider: 'claude',
    use_mcp: false,
    target_audience: '',
    prompt: cfg.defaultPrompt,
    candidate_name: '',
    role: '',
    direct_report: '',
  }
}

export default function Page() {
  const [domain, setDomain] = useState<Domain>('director_os')
  const [values, setValues] = useState<FormValues>(defaultValues('director_os'))
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('Ready. Configure and run a workflow.')
  const [result, setResult] = useState<WorkflowResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  // Check API health on mount
  useEffect(() => {
    checkHealth().then(setApiOnline)
  }, [])

  const handleDomainChange = useCallback((d: Domain) => {
    setDomain(d)
    setValues(defaultValues(d))
    setResult(null)
    setError(null)
    setStatus('Ready. Configure and run a workflow.')
  }, [])

  const handleValuesChange = useCallback((v: FormValues) => {
    setValues(v)
  }, [])

  const handleSubmit = useCallback(async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setStatus('Running workflow…')
    try {
      const res = await runWorkflow(values)
      setResult(res)
      setStatus(`Done — ${res.workflow}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      setStatus('Workflow failed.')
    } finally {
      setLoading(false)
    }
  }, [values])

  const cfg = DOMAIN_CONFIG[domain]

  // Compute section counts from the result for direct domain calls (no trace wrapper)
  const directSectionCounts: Record<string, number> | undefined = result && !result.trace
    ? Object.fromEntries(
        cfg.sections
          .map((s) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const items = (result.result as any)[s.key]
            return [s.key, Array.isArray(items) ? items.length : 0]
          })
          .filter(([, v]) => (v as number) > 0),
      )
    : undefined

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-16 pt-8 sm:px-6">

      {/* Header */}
      <header className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 inline-block rounded-full border border-aios-accent/30 bg-aios-accent/10 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-accent">
              Operator Console
            </div>
            <h1 className="text-3xl font-bold leading-tight tracking-tight text-aios-ink sm:text-4xl">
              AI Operating System
            </h1>
            <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-aios-muted">
              Reads your local notes. Retrieves the most relevant evidence.
              Produces grounded output where every item cites the exact source file
              and line number it came from.
            </p>
          </div>
          <div className="flex flex-col items-end gap-1.5 text-right">
            <span className="font-mono text-[11px] text-aios-muted">v1.2.0 · local-first</span>
            <div className="flex items-center gap-1.5">
              <div
                className={[
                  'h-2 w-2 rounded-full',
                  apiOnline === null
                    ? 'bg-aios-muted animate-pulse'
                    : apiOnline
                      ? 'bg-aios-accent'
                      : 'bg-aios-accent2',
                ].join(' ')}
              />
              <span className="text-[11px] text-aios-muted">
                {apiOnline === null
                  ? 'checking API…'
                  : apiOnline
                    ? 'API online'
                    : 'API offline — start uvicorn'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Domain tabs */}
      <div className="mb-6 rounded-2xl border border-aios-line bg-aios-panel p-4">
        <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
          Domain
        </p>
        <DomainTabs active={domain} onChange={handleDomainChange} />
        <p className="mt-3 text-xs text-aios-muted">{cfg.description}</p>
      </div>

      {/* Main workspace */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">

        {/* Form panel */}
        <div className="rounded-2xl border border-aios-line bg-aios-panel p-5">
          <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
            Run Workflow
          </p>
          <WorkflowForm
            domain={domain}
            values={values}
            onChange={handleValuesChange}
            onSubmit={handleSubmit}
            loading={loading}
            status={status}
          />
        </div>

        {/* Output panel */}
        <div className="flex flex-col gap-6">

          {/* Trace pane — always shown when there's a result */}
          {result && (
            <div>
              <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted pl-1">
                Trace
              </p>
              <TracePane
                workflow={result.workflow}
                rationale={result.rationale}
                trace={result.trace}
                evidenceCount={result.result.evidence?.length}
                dataPath={values.data_path}
                sectionCounts={directSectionCounts}
              />
            </div>
          )}

          {/* Results pane */}
          <div>
            {(result || error) && (
              <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted pl-1">
                Result
              </p>
            )}
            <ResultsPane result={result} domain={domain} error={error} />
          </div>

        </div>
      </div>

      {/* Footer */}
      <footer className="mt-12 border-t border-aios-line pt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-aios-muted">
            AI Operating System · Evidence-grounded synthesis from local notes
          </p>
          <div className="flex gap-4 text-xs text-aios-muted">
            <span>246 tests passing</span>
            <span>·</span>
            <span>4 domains</span>
            <span>·</span>
            <span>22 eval cases</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
