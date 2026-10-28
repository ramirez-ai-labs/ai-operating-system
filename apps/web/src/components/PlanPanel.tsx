'use client'

import { useState } from 'react'
import type { PlanResponse, PlanStep, StepResult } from '@/lib/types'
import { domainConfigFor, getSummary, sectionsFor } from '@/lib/types'
import { runPlan } from '@/lib/api'
import type { PlanFormValues } from '@/lib/api'
import { GroundedSection } from './GroundedSection'

const inputClass =
  'w-full rounded-xl border border-aios-line bg-white px-3.5 py-2.5 text-sm text-aios-ink placeholder-aios-muted/60 focus:border-aios-accent focus:outline-none focus:ring-1 focus:ring-aios-accent/30'

const EXAMPLE_GOALS = [
  'Prep my week',
  'Interview prep for Alex Chen and 1:1 with Sarah about blockers',
  'Weekly leadership update and a LinkedIn post about the platform migration',
]

const DEFAULT_VALUES: PlanFormValues = {
  goal: EXAMPLE_GOALS[1],
  planner: 'rules',
  max_steps: 5,
  use_model: false,
  provider: 'claude',
}

function StatusBadge({ status }: { status: string }) {
  const style =
    status === 'ok'
      ? 'bg-aios-accent/10 text-aios-accent border-aios-accent/30'
      : 'bg-aios-accent2/10 text-aios-accent2 border-aios-accent2/30'
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-widest ${style}`}>
      {status}
    </span>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-xs font-semibold uppercase tracking-widest text-aios-muted">{children}</span>
  )
}

function StepCard({ step, planStep }: { step: StepResult; planStep?: PlanStep }) {
  const [showInput, setShowInput] = useState(false)
  const label = domainConfigFor(step.workflow_id)?.label ?? step.workflow_id

  return (
    <div className="rounded-2xl border border-aios-line bg-aios-panel p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[11px] text-aios-muted">step {step.step_id}</span>
          <span className="text-sm font-semibold text-aios-ink">{label}</span>
        </div>
        <StatusBadge status={step.status} />
      </div>

      {planStep?.rationale && (
        <p className="mb-3 text-xs leading-relaxed text-aios-muted">{planStep.rationale}</p>
      )}

      {step.error && (
        <p className="mb-3 rounded-xl border border-aios-accent2/30 p-3 text-sm text-aios-accent2">
          {step.error}
        </p>
      )}

      {step.result && (
        <>
          <p className="mb-4 text-sm leading-relaxed text-aios-ink">{getSummary(step.result)}</p>
          {sectionsFor(step.workflow_id).map((sec) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const items = (step.result as any)[sec.key]
            return (
              <GroundedSection
                key={sec.key}
                label={sec.label}
                items={Array.isArray(items) ? items : []}
                variant={sec.variant}
              />
            )
          })}
        </>
      )}

      {planStep && (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setShowInput((v) => !v)}
            className="text-xs text-aios-muted transition-colors hover:text-aios-ink"
          >
            {showInput ? '▾' : '▸'} Tool call <span className="font-mono">{planStep.tool_name}</span>
          </button>
          {showInput && (
            <pre className="mt-2 overflow-auto rounded-lg bg-aios-bg p-3 font-mono text-[11px] text-aios-muted">
              {JSON.stringify(planStep.tool_input, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export function PlanPanel() {
  const [values, setValues] = useState<PlanFormValues>(DEFAULT_VALUES)
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<PlanResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showRaw, setShowRaw] = useState(false)

  function set<K extends keyof PlanFormValues>(key: K, val: PlanFormValues[K]) {
    setValues((v) => ({ ...v, [key]: val }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResponse(null)
    try {
      setResponse(await runPlan(values))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const planStepsById = new Map((response?.plan.steps ?? []).map((s) => [s.step_id, s]))

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
      {/* Form panel */}
      <div className="rounded-2xl border border-aios-line bg-aios-panel p-5">
        <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
          Plan a Goal
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <Label>Goal</Label>
            <textarea
              value={values.goal}
              onChange={(e) => set('goal', e.target.value)}
              rows={3}
              className={inputClass + ' resize-none'}
            />
          </label>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLE_GOALS.map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => set('goal', g)}
                className="rounded-full border border-aios-line px-2.5 py-1 text-[11px] text-aios-muted transition-colors hover:border-aios-accent/40 hover:text-aios-ink"
              >
                {g}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1.5">
              <Label>Planner</Label>
              <select
                value={values.planner}
                onChange={(e) => set('planner', e.target.value as PlanFormValues['planner'])}
                className={inputClass}
              >
                <option value="rules">Rules (no model)</option>
                <option value="ollama">Ollama (local)</option>
                <option value="claude">Claude (API key)</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <Label>Max Steps</Label>
              <input
                type="number"
                min={1}
                max={10}
                value={values.max_steps}
                onChange={(e) => set('max_steps', Number(e.target.value))}
                className={inputClass}
              />
            </label>
          </div>

          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="checkbox"
              checked={values.use_model}
              onChange={(e) => set('use_model', e.target.checked)}
              className="h-4 w-4 accent-aios-accent"
            />
            <span className="text-sm text-aios-ink">Model-assisted synthesis in each step</span>
          </label>

          {values.use_model && (
            <label className="flex flex-col gap-1.5">
              <Label>Synthesis Provider</Label>
              <select
                value={values.provider}
                onChange={(e) => set('provider', e.target.value as PlanFormValues['provider'])}
                className={inputClass}
              >
                <option value="claude">Claude</option>
                <option value="ollama">Ollama (Director OS only)</option>
              </select>
            </label>
          )}

          <button
            type="submit"
            disabled={loading || values.goal.trim() === ''}
            className="mt-1 rounded-full bg-aios-accent px-5 py-3 text-sm font-bold text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Planning…' : 'Run Plan →'}
          </button>
          <p className="text-xs leading-relaxed text-aios-muted">
            The planner turns the goal into domain tool calls. Steps run in parallel, and each
            step&apos;s grounding is re-validated at merge.
          </p>
        </form>
      </div>

      {/* Output panel */}
      <div className="flex flex-col gap-6">
        {error && (
          <div className="rounded-2xl border border-aios-accent2/30 bg-aios-panel p-5">
            <p className="text-sm font-semibold text-aios-accent2">Error</p>
            <p className="mt-1 text-sm leading-relaxed text-aios-muted">{error}</p>
          </div>
        )}

        {!response && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-3 text-4xl opacity-20">⬡</div>
            <p className="text-sm text-aios-muted">
              Enter a goal that spans several domains and run the plan.
            </p>
          </div>
        )}

        {response && (
          <>
            <div className="rounded-2xl border border-aios-line bg-aios-panel p-4">
              <div className="mb-2.5 flex items-center justify-between gap-2">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">Plan</p>
                <StatusBadge status={response.status} />
              </div>
              <div className="flex flex-col gap-1.5 text-sm text-aios-ink">
                <p>
                  <span className="text-aios-muted">Planner: </span>
                  <span className="font-mono text-xs">
                    {response.plan.planner_requested}
                    {response.plan.planner_used !== response.plan.planner_requested &&
                      ` → ${response.plan.planner_used}`}
                  </span>
                </p>
                {response.plan.fallback_reason && (
                  <p className="text-xs text-aios-accent2">
                    Fell back to rules: {response.plan.fallback_reason}
                  </p>
                )}
                <p className="text-xs text-aios-muted">{response.validation_summary}</p>
                {response.plan.notes.map((n, i) => (
                  <p key={i} className="text-xs text-aios-muted">· {n}</p>
                ))}
              </div>
            </div>

            {response.steps.map((step) => (
              <StepCard key={step.step_id} step={step} planStep={planStepsById.get(step.step_id)} />
            ))}

            <div className="overflow-hidden rounded-2xl border border-aios-line bg-aios-panel">
              <button
                onClick={() => setShowRaw((v) => !v)}
                className="flex w-full items-center justify-between px-5 py-3 text-left text-xs text-aios-muted transition-colors hover:text-aios-ink"
              >
                <span className="font-semibold uppercase tracking-widest">Raw Response</span>
                <span>{showRaw ? '▾' : '▸'}</span>
              </button>
              {showRaw && (
                <pre className="max-h-96 overflow-auto p-5 pt-0 font-mono text-[11px] leading-relaxed text-aios-muted">
                  {JSON.stringify(response, null, 2)}
                </pre>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
