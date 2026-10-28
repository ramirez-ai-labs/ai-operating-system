'use client'

import type { Domain } from '@/lib/types'
import { DOMAIN_CONFIG } from '@/lib/types'

// 'plan' is not a domain: it runs a goal across several domains via POST /plan.
export type Tab = Domain | 'plan'

const TABS: Tab[] = ['director_os', 'brand_os', 'interview_os', 'one_on_one_os', 'auto', 'plan']

export function tabLabel(tab: Tab): string {
  return tab === 'plan' ? 'Plan' : DOMAIN_CONFIG[tab].label
}

interface Props {
  active: Tab
  onChange: (t: Tab) => void
}

export function DomainTabs({ active, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {TABS.map((t) => {
        const isActive = t === active
        return (
          <button
            key={t}
            onClick={() => onChange(t)}
            className={[
              'px-4 py-2 rounded-full text-sm font-semibold transition-all border',
              isActive
                ? 'bg-aios-accent text-white border-aios-accent shadow-sm'
                : 'bg-aios-panel text-aios-muted border-aios-line hover:border-aios-accent/40 hover:text-aios-ink',
            ].join(' ')}
          >
            {tabLabel(t)}
          </button>
        )
      })}
    </div>
  )
}
