'use client'

import { useState } from 'react'
import type { Domain } from '@/lib/types'
import { DOMAIN_CONFIG } from '@/lib/types'
import type { FormValues } from '@/lib/api'

interface Props {
  domain: Domain
  values: FormValues
  onChange: (values: FormValues) => void
  onSubmit: () => void
  loading: boolean
  status: string
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-widest text-aios-muted">
        {label}
      </span>
      {children}
    </label>
  )
}

const inputClass =
  'w-full rounded-xl border border-aios-line bg-white px-3.5 py-2.5 text-sm text-aios-ink placeholder-aios-muted/60 focus:border-aios-accent focus:outline-none focus:ring-1 focus:ring-aios-accent/30'

export function WorkflowForm({ domain, values, onChange, onSubmit, loading, status }: Props) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const cfg = DOMAIN_CONFIG[domain]

  function set<K extends keyof FormValues>(key: K, val: FormValues[K]) {
    onChange({ ...values, [key]: val })
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit()
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">

      {domain === 'auto' && (
        <Field label="Prompt">
          <textarea
            value={values.prompt}
            onChange={(e) => set('prompt', e.target.value)}
            rows={3}
            placeholder="Describe what you need…"
            className={inputClass + ' resize-none'}
          />
        </Field>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field label="Data Path">
          <input
            value={values.data_path}
            onChange={(e) => set('data_path', e.target.value)}
            placeholder="data/local_only/projects"
            className={inputClass}
          />
        </Field>
        <Field label="Max Documents">
          <input
            type="number"
            min={1}
            max={20}
            value={values.max_documents}
            onChange={(e) => set('max_documents', Number(e.target.value))}
            className={inputClass}
          />
        </Field>
      </div>

      <Field label="Focus (optional)">
        <input
          value={values.focus}
          onChange={(e) => set('focus', e.target.value)}
          placeholder="Filter results by topic or workstream…"
          className={inputClass}
        />
      </Field>

      {cfg.extraFields.includes('candidate_name') && (
        <div className="grid grid-cols-2 gap-3">
          <Field label="Candidate Name">
            <input
              value={values.candidate_name}
              onChange={(e) => set('candidate_name', e.target.value)}
              placeholder="Alex Rivera"
              className={inputClass}
            />
          </Field>
          <Field label="Role">
            <input
              value={values.role}
              onChange={(e) => set('role', e.target.value)}
              placeholder="Senior Platform Engineer"
              className={inputClass}
            />
          </Field>
        </div>
      )}

      {cfg.extraFields.includes('direct_report') && (
        <Field label="Direct Report">
          <input
            value={values.direct_report}
            onChange={(e) => set('direct_report', e.target.value)}
            placeholder="Marcus"
            className={inputClass}
          />
        </Field>
      )}

      {/* Advanced settings toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-aios-muted hover:text-aios-ink transition-colors self-start"
      >
        <span className="text-base leading-none">{showAdvanced ? '▾' : '▸'}</span>
        Advanced settings
      </button>

      {showAdvanced && (
        <div className="flex flex-col gap-3 pl-3 border-l-2 border-aios-line">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={values.use_model}
                onChange={(e) => set('use_model', e.target.checked)}
                className="w-4 h-4 accent-aios-accent"
              />
              <span className="text-sm text-aios-ink">Model-assisted synthesis</span>
            </label>
          </div>

          <Field label="Provider">
            <select
              value={values.provider}
              onChange={(e) => set('provider', e.target.value as 'claude' | 'ollama')}
              className={inputClass}
            >
              <option value="claude">Claude Haiku (default)</option>
              <option value="ollama">Ollama (local)</option>
            </select>
          </Field>

          {domain === 'auto' && (
            <>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={values.use_mcp}
                  onChange={(e) => set('use_mcp', e.target.checked)}
                  className="w-4 h-4 accent-aios-accent"
                />
                <span className="text-sm text-aios-ink">MCP-first synthesis</span>
              </label>

              <Field label="Target Audience">
                <select
                  value={values.target_audience}
                  onChange={(e) => set('target_audience', e.target.value)}
                  className={inputClass}
                >
                  <option value="">None — structured output only</option>
                  <option value="linkedin_post">LinkedIn Post</option>
                  <option value="executive_brief">Executive Brief</option>
                  <option value="team_update">Team Update</option>
                </select>
              </Field>
            </>
          )}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="mt-1 rounded-full bg-aios-accent px-5 py-3 text-sm font-bold text-white transition-all hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Running…' : `Run ${cfg.label} →`}
      </button>

      {status && (
        <p className="text-xs text-aios-muted leading-relaxed">{status}</p>
      )}
    </form>
  )
}
