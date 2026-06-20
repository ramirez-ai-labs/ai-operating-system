'use client'

import { useState } from 'react'
import type { Domain, WorkflowResult } from '@/lib/types'
import {
  DOMAIN_CONFIG,
  getSummary,
  isWeeklyUpdate,
  isBrandDraft,
  isInterviewBrief,
  isOneOnOne,
} from '@/lib/types'
import { GroundedSection } from './GroundedSection'

interface Props {
  result: WorkflowResult | null
  domain: Domain
  error: string | null
}

function getItems(result: WorkflowResult, sectionKey: string): import('@/lib/types').GroundedItem[] {
  const r = result.result
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const val = (r as any)[sectionKey]
  return Array.isArray(val) ? val : []
}

export function ResultsPane({ result, domain, error }: Props) {
  const [showRaw, setShowRaw] = useState(false)

  const cfg = DOMAIN_CONFIG[domain]
  const sections = result
    ? cfg.sections.length > 0
      ? cfg.sections
      : inferSections(result)
    : []

  if (error) {
    return (
      <div className="rounded-2xl border border-aios-accent2/30 bg-aios-panel p-5">
        <p className="text-sm font-semibold text-aios-accent2">Error</p>
        <p className="mt-1 text-sm text-aios-muted leading-relaxed">{error}</p>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="mb-3 text-4xl opacity-20">⬡</div>
        <p className="text-sm text-aios-muted">
          Select a domain, configure the form, and run a workflow.
        </p>
        <p className="mt-1 text-xs text-aios-muted/70">
          Every output item is grounded to a source file and line number.
        </p>
      </div>
    )
  }

  const summary = getSummary(result.result)
  const r = result.result

  return (
    <div className="flex flex-col gap-5">
      {/* Summary */}
      {summary && (
        <div className="rounded-2xl border border-aios-line bg-aios-panel p-5">
          <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
            Summary
          </p>
          <p className="text-sm leading-relaxed text-aios-ink">{summary}</p>
        </div>
      )}

      {/* Grounded sections */}
      <div className="rounded-2xl border border-aios-line bg-aios-panel p-5">
        {sections.map((sec) => {
          const items = getItems(result, sec.key)
          return (
            <GroundedSection
              key={sec.key}
              label={sec.label}
              items={items}
              variant={sec.variant}
            />
          )
        })}
        {sections.length === 0 && (
          <p className="text-sm text-aios-muted">No sections configured for this domain.</p>
        )}
      </div>

      {/* Formatted content (multi-agent writer output) */}
      {result.formattedContent && (
        <div className="rounded-2xl border border-aios-accent/20 bg-aios-panel p-5">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-accent">
            Formatted Content
          </p>
          <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-aios-ink">
            {result.formattedContent}
          </pre>
        </div>
      )}

      {/* MCP synthesis */}
      {result.mcpSynthesis && (
        <div className="rounded-2xl border border-aios-accent/20 bg-aios-panel p-5">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-accent">
            MCP Synthesis
          </p>
          <pre className="whitespace-pre-wrap font-serif text-sm leading-relaxed text-aios-ink">
            {result.mcpSynthesis}
          </pre>
        </div>
      )}

      {/* Evidence */}
      {r.evidence && r.evidence.length > 0 && (
        <div className="rounded-2xl border border-aios-line bg-aios-panel p-5">
          <p className="mb-3 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
            Evidence ({r.evidence.length})
          </p>
          <div className="flex flex-col gap-2">
            {r.evidence.map((ev, i) => (
              <div key={i} className="rounded-lg bg-aios-bg p-3">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-mono text-[11px] text-aios-accent font-semibold">
                    {ev.source}:{ev.line_number}
                  </span>
                  <span className="text-[11px] text-aios-muted truncate">{ev.title}</span>
                </div>
                <p className="text-xs text-aios-muted leading-relaxed line-clamp-2">{ev.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Raw JSON toggle */}
      <div className="rounded-2xl border border-aios-line bg-aios-panel overflow-hidden">
        <button
          onClick={() => setShowRaw((v) => !v)}
          className="flex w-full items-center justify-between px-5 py-3 text-left text-xs text-aios-muted hover:text-aios-ink transition-colors"
        >
          <span className="font-semibold uppercase tracking-widest">Raw Response</span>
          <span>{showRaw ? '▾' : '▸'}</span>
        </button>
        {showRaw && (
          <pre className="overflow-auto p-5 pt-0 font-mono text-[11px] leading-relaxed text-aios-muted max-h-96">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

function inferSections(result: WorkflowResult): import('@/lib/types').SectionDef[] {
  const r = result.result
  if (isWeeklyUpdate(r)) {
    return [
      { key: 'wins',       label: 'Wins',       variant: 'positive' },
      { key: 'risks',      label: 'Risks',      variant: 'risk'     },
      { key: 'next_steps', label: 'Next Steps', variant: 'default'  },
    ]
  }
  if (isBrandDraft(r)) {
    return [
      { key: 'post_outline',      label: 'Post Outline',      variant: 'default'  },
      { key: 'podcast_angles',    label: 'Podcast Angles',    variant: 'positive' },
      { key: 'repo_improvements', label: 'Repo Improvements', variant: 'default'  },
    ]
  }
  if (isInterviewBrief(r)) {
    return [
      { key: 'key_questions',  label: 'Key Questions',  variant: 'default'  },
      { key: 'talking_points', label: 'Talking Points', variant: 'positive' },
      { key: 'red_flags',      label: 'Red Flags',      variant: 'risk'     },
    ]
  }
  if (isOneOnOne(r)) {
    return [
      { key: 'action_items',   label: 'Action Items',   variant: 'default'  },
      { key: 'talking_points', label: 'Talking Points', variant: 'positive' },
      { key: 'blockers',       label: 'Blockers',       variant: 'risk'     },
      { key: 'kudos',          label: 'Kudos',          variant: 'positive' },
    ]
  }
  return []
}
