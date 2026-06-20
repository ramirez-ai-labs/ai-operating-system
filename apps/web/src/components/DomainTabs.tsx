'use client'

import type { Domain } from '@/lib/types'
import { DOMAIN_CONFIG } from '@/lib/types'

const DOMAINS: Domain[] = ['director_os', 'brand_os', 'interview_os', 'one_on_one_os', 'auto']

interface Props {
  active: Domain
  onChange: (d: Domain) => void
}

export function DomainTabs({ active, onChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {DOMAINS.map((d) => {
        const cfg = DOMAIN_CONFIG[d]
        const isActive = d === active
        return (
          <button
            key={d}
            onClick={() => onChange(d)}
            className={[
              'px-4 py-2 rounded-full text-sm font-semibold transition-all border',
              isActive
                ? 'bg-aios-accent text-white border-aios-accent shadow-sm'
                : 'bg-aios-panel text-aios-muted border-aios-line hover:border-aios-accent/40 hover:text-aios-ink',
            ].join(' ')}
          >
            {cfg.label}
          </button>
        )
      })}
    </div>
  )
}
