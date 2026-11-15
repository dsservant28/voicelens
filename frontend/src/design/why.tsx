// The "Why?" drawer: open any id from anywhere and see its lineage as a vertical drill core.
import { AnimatePresence, motion } from 'motion/react'
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useTrace, type ChainLevel, type TraceResult } from '../api/client'
import { RecordCard } from './record'
import { CHANNEL, fmt } from './tokens'
import { Flatline, IdChip, MagnitudeBadge } from './ui'

const Ctx = createContext<{ open: (id: string) => void; close: () => void }>({ open: () => {}, close: () => {} })
export const useWhy = () => useContext(Ctx)

export function WhyProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<string[]>([])
  const open = useCallback((id: string) => setStack((s) => (s[s.length - 1] === id ? s : [...s, id])), [])
  const close = useCallback(() => setStack([]), [])
  const back = () => setStack((s) => s.slice(0, -1))
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [close])
  const id = stack[stack.length - 1] ?? null
  return (
    <Ctx.Provider value={{ open, close }}>
      {children}
      <AnimatePresence>
        {id && (
          <>
            <motion.div className="fixed inset-0 z-40 bg-black/40" onClick={close}
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            <motion.aside className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[620px] flex-col border-l border-line bg-ink shadow-2xl"
              initial={{ x: 640 }} animate={{ x: 0 }} exit={{ x: 640 }} transition={{ type: 'spring', stiffness: 260, damping: 30 }}>
              <header className="flex items-center gap-3 border-b border-line px-5 py-3">
                {stack.length > 1 && <button onClick={back} className="text-muted hover:text-fg" title="back">←</button>}
                <span className="text-xs font-bold tracking-[0.25em] text-support">WHY?</span>
                <span className="num text-sm">{id}</span>
                <button onClick={close} className="ml-auto text-muted hover:text-fg" title="close (Esc)">✕</button>
              </header>
              <div className="flex-1 overflow-y-auto px-5 py-4"><Trace id={id} /></div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </Ctx.Provider>
  )
}

function Layer({ title, children, last = false }: { title: ReactNode; children: ReactNode; last?: boolean }) {
  return (
    <div className="relative pl-7">
      {!last && <span className="absolute left-[9px] top-5 h-[calc(100%-4px)] w-px bg-line" />}
      <span className="absolute left-[4px] top-1.5 h-3 w-3 rounded-full border-2 border-support bg-ink" />
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{title}</div>
      <div className="mb-5">{children}</div>
    </div>
  )
}

const n = (v: unknown) => Number(v)

function ChainView({ level }: { level: ChainLevel }) {
  if (level.level === 'action_item') {
    const i = level.inputs as { volume: number; neg_share: number; severity_weight: number; shift: number }
    return (
      <Layer title={<>Action item <IdChip id={String(level.id)} /></>}>
        <div className="rounded-lg border border-line bg-panel p-3">
          <div className="text-sm">{String(level.recommendation)}</div>
          <div className="num mt-3 text-xs text-muted">priority = volume × neg share × severity × (1 + shift)</div>
          <div className="num mt-1 text-sm">
            = {fmt.int(i.volume)} × {fmt.num(i.neg_share)} × {i.severity_weight} × (1 + {fmt.num(Math.max(i.shift, 0))})
            {' '}= <b className="text-support">{fmt.num(n(level.priority_score), 1)}</b>
          </div>
          <div className="mt-2 text-xs text-muted">rule: <span className="num">{String(level.rule)}</span></div>
        </div>
      </Layer>
    )
  }
  if (level.level === 'alert') {
    const lead = level.lead_channel as keyof typeof CHANNEL | null
    return (
      <Layer title={<>Alert <IdChip id={String(level.id)} /></>}>
        <div className="flex items-center gap-4 rounded-lg border border-line bg-panel p-3">
          <MagnitudeBadge m={n(level.magnitude)} size={52} />
          <div className="text-sm leading-6">
            <div>detected <b className="num">{fmt.date(String(level.detected_date))}</b> · lead channel{' '}
              <b style={{ color: lead ? CHANNEL[lead].color : undefined }}>{lead ? CHANNEL[lead].label : '–'}</b></div>
            <div className="num text-xs text-muted">negative share {fmt.pct(n(level.baseline_share))} → {fmt.pct(n(level.window_share))}</div>
            <div className="text-xs text-muted">{String(level.test)}</div>
          </div>
        </div>
      </Layer>
    )
  }
  return (
    <Layer title={<>Weekly cell <span className="num normal-case">{String(level.cell_id ?? level.id)}</span></>}>
      <div className="num rounded-lg border border-line bg-panel p-3 text-sm">
        week {String(level.week_start)} · {String(level.channel_type)} · {fmt.int(n(level.n_items))} items · {fmt.pct(n(level.neg_share))} negative
      </div>
    </Layer>
  )
}

function Records({ t }: { t: TraceResult }) {
  const [shown, setShown] = useState(25)
  const items = t.items ?? []
  return (
    <Layer title={`${fmt.int(items.length)} source records`} last>
      <div className="space-y-2">
        {items.slice(0, shown).map((it) => <RecordCard key={it.source_type + it.source_id} item={it} compact />)}
        {items.length > shown && (
          <button onClick={() => setShown((s) => s + 50)} className="w-full rounded-lg border border-dashed border-line py-2 text-xs text-muted hover:text-fg">
            show more ({fmt.int(items.length - shown)} left)
          </button>
        )}
      </div>
    </Layer>
  )
}

function Trace({ id }: { id: string }) {
  const { data: t, isLoading, error } = useTrace(id)
  if (isLoading) return <Flatline label="tracing lineage…" />
  if (error || !t) return <p className="text-sm text-neg">Could not trace “{id}”. Try an id like REV-2026-000123, ALR-000001 or ACT-000001.</p>
  if (t.kind !== 'record') return <>{t.chain?.map((l, i) => <ChainView key={i} level={l} />)}<Records t={t} /></>
  return (
    <>
      {t.quarantined && (
        <div className="mb-4 rounded-lg border border-neg/40 bg-neg/10 p-3 text-sm">
          Quarantined at ingest - kept for audit, excluded from analysis.
        </div>
      )}
      {t.item && <Layer title="Record"><RecordCard item={t.item} /></Layer>}
      {!!t.exceptions?.length && (
        <Layer title="Exceptions on this record">
          {t.exceptions.map((e) => (
            <div key={e.exception_id} className="mb-2 rounded-lg border border-line bg-panel p-2 text-xs">
              <span className="num text-support">{e.exception_type}</span> · {e.disposition} · {e.detected_by}
              <div className="mt-1 text-muted">{e.detail}</div>
            </div>
          ))}
        </Layer>
      )}
      <Layer title="Feeds into" last>
        <div className="space-y-2 text-sm">
          {t.cells?.map((c) => <div key={c.cell_id} className="num text-xs text-muted">cell {c.week_start} · {c.n_items} items · {fmt.pct(c.neg_share)} neg <IdChip id={c.cell_id} /></div>)}
          {t.alerts?.map((a) => <div key={a.alert_id} className="flex items-center gap-2"><MagnitudeBadge m={n(a.magnitude)} size={26} /><IdChip id={a.alert_id} /><span className="text-xs text-muted">{a.kind} · {a.role} evidence</span></div>)}
          {t.actions?.map((a) => <div key={a.action_item_id} className="flex items-center gap-2"><IdChip id={a.action_item_id} /><span className="num text-xs text-muted">priority {fmt.num(n(a.priority_score), 1)} · {a.status}</span></div>)}
          {!t.cells?.length && !t.alerts?.length && !t.actions?.length && <span className="text-xs text-muted">not part of any cell, alert or action</span>}
        </div>
      </Layer>
    </>
  )
}
