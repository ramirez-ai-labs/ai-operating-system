import type { GroundedItem } from '@/lib/types'

interface Props {
  label: string
  items: GroundedItem[]
  variant?: 'default' | 'risk' | 'positive'
}

export function GroundedSection({ label, items, variant = 'default' }: Props) {
  if (!items || items.length === 0) return null

  const dotColor =
    variant === 'risk'
      ? 'bg-aios-accent2'
      : 'bg-aios-accent'

  const borderColor =
    variant === 'risk'
      ? 'border-aios-accent2/20'
      : 'border-aios-accent/20'

  return (
    <section className="mb-5">
      <h3 className="mb-2.5 text-[11px] font-bold uppercase tracking-[0.12em] text-aios-muted">
        {label}
        <span className="ml-2 font-normal text-aios-line">({items.length})</span>
      </h3>
      <div className="flex flex-col gap-2">
        {items.map((item, i) => (
          <div
            key={i}
            className={`rounded-xl border ${borderColor} bg-white/60 p-3`}
          >
            <div className="flex items-start gap-2.5">
              <div
                className={`mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full ${dotColor}`}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm leading-relaxed text-aios-ink">{item.text}</p>
                <span className="mt-1.5 inline-block rounded-full bg-aios-bg px-2 py-0.5 font-mono text-[11px] text-aios-muted">
                  {item.source}:{item.line_number}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
