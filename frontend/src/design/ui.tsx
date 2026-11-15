// Small shared building blocks.
import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import type { Channel, Sentiment } from '../api/client'
import { CHANNEL, M_GATE, SENTIMENT, fmt, magColor, magRings } from './tokens'
import { useWhy } from './why-context'

export function Panel({ title, right, children, className = '' }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-line bg-panel ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-line px-4 py-2.5">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{title}</h2>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

/** Concentric rings, one per doubling of M above the gate; colour amber (M 5) -> red (M 80+). */
export function MagnitudeBadge({ m, size = 44, label = true }: { m: number; size?: number; label?: boolean }) {
  const rings = magRings(m)
  const c = magColor(m)
  const r = size / 2
  return (
    <span className="inline-flex items-center gap-2" title={`Magnitude M = −log₁₀(p) = ${fmt.num(m, 1)}\np ≈ 10^−${fmt.num(m, 1)}  ·  alert gate: M ≥ ${M_GATE}`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        {Array.from({ length: rings }, (_, i) => (
          <motion.circle key={i} cx={r} cy={r} r={(r - 2) * ((i + 1) / rings)} fill="none" stroke={c}
            strokeWidth={i === rings - 1 ? 1.6 : 1} strokeOpacity={0.35 + 0.65 * ((i + 1) / rings)}
            initial={{ scale: 0.2, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: i * 0.08, type: 'spring', stiffness: 160, damping: 18 }} style={{ originX: '50%', originY: '50%' }} />
        ))}
        <circle cx={r} cy={r} r={2.4} fill={c} />
      </svg>
      {label && <span className="num text-sm font-semibold" style={{ color: c }}>M {fmt.num(m, 1)}</span>}
    </span>
  )
}

export function ChannelDot({ c, label = false }: { c: Channel; label?: boolean }) {
  const ch = CHANNEL[c]
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <span className="h-2 w-2 rounded-full" style={{ background: ch.color }} />
      {label && ch.label}
    </span>
  )
}

export function SentimentPill({ s, conf }: { s?: Sentiment; conf?: number }) {
  if (!s) return null
  const t = SENTIMENT[s]
  return (
    <span className="inline-flex items-center gap-2 rounded-full border px-2 py-0.5 text-xs"
      style={{ borderColor: `${t.color}55`, color: t.color }} title={conf != null ? `confidence ${fmt.num(conf, 2)}` : undefined}>
      {t.label}
      {conf != null && (
        <span className="relative h-1 w-10 overflow-hidden rounded-full bg-line">
          <span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${Number(conf) * 100}%`, background: t.color }} />
        </span>
      )}
    </span>
  )
}

/** Any id: mono, click = open the Why? drawer, copy button. */
export function IdChip({ id, className = '' }: { id: string; className?: string }) {
  const why = useWhy()
  return (
    <span className={`group inline-flex items-center gap-1 ${className}`}>
      <button onClick={() => why.open(id)} className="num rounded px-1 text-xs text-fg/90 underline decoration-line decoration-dotted underline-offset-4 hover:bg-panel2 hover:decoration-support">
        {id}
      </button>
      <button onClick={() => navigator.clipboard?.writeText(id)} title="copy id"
        className="text-[10px] text-muted opacity-0 transition group-hover:opacity-100">⧉</button>
    </span>
  )
}

export function Kpi({ label, value, sub, accent }: { label: string; value: ReactNode; sub?: ReactNode; accent?: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel px-4 py-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">{label}</div>
      <div className="num mt-1 text-2xl font-semibold" style={accent ? { color: accent } : undefined}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </div>
  )
}

/** Loading = a flat seismograph line with one travelling blip. */
export function Flatline({ label = 'listening…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-xs text-muted">
      <svg width="220" height="40" viewBox="0 0 220 40">
        <line x1="0" y1="20" x2="220" y2="20" stroke="var(--line)" strokeWidth="1.5" />
        <motion.polyline points="0,20 8,20 11,12 14,28 17,20 25,20" fill="none" stroke="#fbbf24" strokeWidth="1.8"
          animate={{ x: [0, 195] }} transition={{ duration: 1.6, repeat: Infinity, ease: 'linear' }} />
      </svg>
      {label}
    </div>
  )
}
