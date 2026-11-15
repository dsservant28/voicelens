// Page 3 - Review: (a) the blind human-review sample of the evaluation split (model answer hidden),
// (b) the uncertain queue laid out on the classifier's own decision plane (positive score x negative score).
import { useQueryClient } from '@tanstack/react-query'
import { max, scaleLinear, scaleSqrt } from 'd3'
import { AnimatePresence, motion } from 'motion/react'
import { useEffect, useMemo, useState } from 'react'
import { runEvaluation, submitReview, useFullEvaluation, useMeta, usePlane, useQueue, type Item, type ReviewEvent, type Sentiment } from '../api/client'
import { useWidth } from '../design/hooks'
import { RecordCard } from '../design/record'
import { useRole } from '../design/role-context'
import { SENTIMENT, fmt } from '../design/tokens'
import { Flatline, Panel } from '../design/ui'

const ORDER: Sentiment[] = ['positive', 'negative', 'neutral', 'mixed']

function useInvalidateReview() {
  const qc = useQueryClient()
  return () => Promise.all([['queue'], ['plane'], ['overview']].map((k) => qc.invalidateQueries({ queryKey: k })))
}

function LabelButtons({ onPick, busy, keys = false }: { onPick: (s: Sentiment) => void; busy: boolean; keys?: boolean }) {
  return (
    <div className="flex flex-wrap gap-2">
      {ORDER.map((s, i) => (
        <button key={s} disabled={busy} onClick={() => onPick(s)}
          className="rounded-lg border px-3 py-1.5 text-sm transition hover:bg-panel2 disabled:opacity-40"
          style={{ borderColor: `${SENTIMENT[s].color}66`, color: SENTIMENT[s].color }}>
          {keys && <kbd className="num mr-1.5 rounded border border-line px-1 text-[10px] text-muted">{i + 1}</kbd>}{SENTIMENT[s].label}
        </button>
      ))}
    </div>
  )
}

/** Blind review: the reviewer sees only the (redacted) text - never the model's label or the gold label. */
function EvalSet() {
  const { role } = useRole()
  const meta = useMeta().data
  const pending = useQueue({ set: 'eval', status: 'pending', limit: 1 })
  const reviewed = useQueue({ set: 'eval', status: 'reviewed', limit: 1 })
  const ev = useFullEvaluation()
  const invalidate = useInvalidateReview()
  const qc = useQueryClient()
  const [themes, setThemes] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState<ReviewEvent | null>(null)
  const [recomputing, setRecomputing] = useState(false)
  const item = pending.data?.items[0]
  const done = reviewed.data?.total ?? 0
  const total = done + (pending.data?.total ?? 0)

  const submit = async (s: Sentiment) => {
    if (!item || busy) return
    setBusy(true)
    try {
      setLast(await submitReview(item.source_type, item.source_id, s, role, themes))
      setThemes([])
      await invalidate()
    } finally { setBusy(false) }
  }
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'SELECT') return
      const i = Number(e.key) - 1
      if (i >= 0 && i < 4) submit(ORDER[i])
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
  const recompute = async () => {
    setRecomputing(true)
    try { await runEvaluation(); await qc.invalidateQueries({ queryKey: ['evaluation-full'] }); await qc.invalidateQueries({ queryKey: ['evaluation'] }) }
    finally { setRecomputing(false) }
  }
  const hr = ev.data?.human_review
  return (
    <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
      <Panel title="Blind review · evaluation split sample"
        right={<span className="num text-xs text-muted">{done} / {total} reviewed</span>}>
        <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-line">
          <motion.div className="h-full bg-support" animate={{ width: `${total ? (done / total) * 100 : 0}%` }} />
        </div>
        {!item ? (
          pending.isLoading ? <Flatline /> : <p className="py-10 text-center text-sm text-muted">All {total} sample items reviewed. Recompute the metrics →</p>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div key={item.source_id} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}>
              <RecordCard item={item} />
              <div className="mt-4 text-[11px] uppercase tracking-wider text-muted">Your label (keys 1–4) - the model's answer is hidden until you submit</div>
              <div className="mt-2"><LabelButtons onPick={submit} busy={busy} keys /></div>
              <div className="mt-4 text-[11px] uppercase tracking-wider text-muted">Themes (optional - leave empty to keep the model's)</div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {meta?.themes.map((t) => (
                  <button key={t.theme_id} onClick={() => setThemes((x) => (x.includes(t.theme_id) ? x.filter((y) => y !== t.theme_id) : [...x, t.theme_id]))}
                    className={`rounded-full border px-2 py-0.5 text-xs transition ${themes.includes(t.theme_id) ? 'border-support bg-support/15 text-support' : 'border-line text-muted hover:text-fg'}`}>
                    {t.name}
                  </button>
                ))}
              </div>
            </motion.div>
          </AnimatePresence>
        )}
        {last && (
          <div className="mt-4 rounded-lg border border-line bg-panel2 p-3 text-xs">
            Saved <span className="num">{last.event_id}</span> as <b style={{ color: SENTIMENT[last.new_sentiment].color }}>{last.new_sentiment}</b> by {last.reviewer} ·
            model had said <b style={{ color: SENTIMENT[last.old_sentiment].color }}>{last.old_sentiment}</b> →{' '}
            <span className={last.decision === 'confirmed' ? 'text-pos' : 'text-mix'}>{last.decision}</span>
          </div>
        )}
      </Panel>
      <Panel title="Human-reviewed evaluation set" right={
        <button onClick={recompute} disabled={recomputing} className="rounded-md border border-support/40 px-2.5 py-1 text-xs text-support hover:bg-support/10 disabled:opacity-40">
          {recomputing ? 'recomputing…' : 'recompute metrics'}</button>}>
        <p className="mb-3 text-sm text-muted">
          A stratified sample of {hr?.sample_size ?? 100} items from the held-out evaluation split. Reviewers label blind; the metrics compare
          the model with <b className="text-fg">human</b> labels, and humans with the generator's documented gold rules.
        </p>
        {!hr?.reviewed ? <p className="text-sm text-muted">No reviewed items in the last computation yet.</p> : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-line p-3"><div className="text-[11px] uppercase tracking-wider text-muted">model vs human</div>
                <div className="num text-2xl font-semibold text-support">{fmt.pct(hr.model_vs_human?.accuracy)}</div>
                <div className="num text-xs text-muted">macro-F1 {fmt.num(hr.model_vs_human?.macro_f1, 3)} · n = {hr.reviewed}</div></div>
              <div className="rounded-lg border border-line p-3"><div className="text-[11px] uppercase tracking-wider text-muted">human vs gold rule</div>
                <div className="num text-2xl font-semibold">{fmt.pct(hr.human_vs_gold)}</div>
                <div className="num text-xs text-muted">{hr.overridden} model labels overridden</div></div>
            </div>
            <div className="num text-xs text-muted">themes: model vs human exact match {fmt.pct(hr.model_vs_human_themes?.exact_match)}</div>
          </div>
        )}
      </Panel>
    </div>
  )
}

/** The classifier's decision regions on its own score plane. */
function Plane({ sel, onSel }: { sel: { pos: number; neg: number } | null; onSel: (c: { pos: number; neg: number } | null) => void }) {
  const cells = usePlane().data
  const [ref, w] = useWidth<HTMLDivElement>(420)
  const agg = useMemo(() => {
    const m = new Map<string, { pos: number; neg: number; n: number; by: Record<string, number>; sarcasm: number; hedged: number }>()
    for (const c of cells ?? []) {
      const k = `${c.pos}|${c.neg}`
      const e = m.get(k) ?? { pos: Number(c.pos), neg: Number(c.neg), n: 0, by: {}, sarcasm: 0, hedged: 0 }
      e.n += Number(c.n); e.by[c.sentiment] = (e.by[c.sentiment] ?? 0) + Number(c.n); e.sarcasm += Number(c.sarcasm); e.hedged += Number(c.hedged)
      m.set(k, e)
    }
    return [...m.values()]
  }, [cells])
  if (!cells) return <div ref={ref}><Flatline /></div>
  const h = Math.min(420, w)
  const x = scaleLinear().domain([-0.45, 4.3]).range([44, w - 12])
  const y = scaleLinear().domain([-0.45, 4.3]).range([h - 34, 10])
  const r = scaleSqrt().domain([0, max(agg, (a) => a.n) ?? 1]).range([3, 34])
  const band = 0.22
  return (
    <div ref={ref}>
      <svg width={w} height={h}>
        <rect x={x(band)} y={y(4.3)} width={x(4.3) - x(band)} height={y(band) - y(4.3)} fill="#f472b6" opacity={0.06} />
        <rect x={x(band)} y={y(band)} width={x(4.3) - x(band)} height={y(-band) - y(band)} fill="#34d399" opacity={0.1} />
        <rect x={x(-band)} y={y(4.3)} width={x(band) - x(-band)} height={y(band) - y(4.3)} fill="#f43f5e" opacity={0.1} />
        <circle cx={x(0)} cy={y(0)} r={x(band) - x(0) + 6} fill="#94a3b8" opacity={0.14} />
        <text x={x(4.2)} y={y(4.05)} textAnchor="end" className="text-[11px]" fill="#f472b6">mixed · both kinds of cue</text>
        <text x={x(4.2)} y={y(0) - 8} textAnchor="end" className="text-[11px]" fill="#34d399">positive · only + cues</text>
        <text x={x(0) + 10} y={y(4.05)} className="text-[11px]" fill="#f43f5e">negative · only − cues</text>
        <text x={x(0) + 12} y={y(0) + 24} className="text-[11px]" fill="#94a3b8">neutral · no cues</text>
        {[0, 1, 2, 3, 4].map((t) => (
          <g key={t}>
            <text x={x(t)} y={h - 16} textAnchor="middle" className="num fill-muted text-[10px]">{t === 4 ? '4+' : t}</text>
            <text x={34} y={y(t) + 3} textAnchor="end" className="num fill-muted text-[10px]">{t === 4 ? '4+' : t}</text>
          </g>
        ))}
        <text x={(w + 44) / 2} y={h - 2} textAnchor="middle" className="fill-muted text-[11px]">positive cue weight →</text>
        <text transform={`translate(10 ${h / 2}) rotate(-90)`} textAnchor="middle" className="fill-muted text-[11px]">negative cue weight →</text>
        {agg.sort((a, b) => b.n - a.n).map((a) => {
          const dom = Object.entries(a.by).sort((p, q) => q[1] - p[1])[0][0] as Sentiment
          const isSel = sel && sel.pos === a.pos && sel.neg === a.neg
          return (
            <g key={`${a.pos}|${a.neg}`} className="cursor-pointer" onClick={() => onSel(isSel ? null : { pos: a.pos, neg: a.neg })}>
              <title>{`pos ${a.pos} · neg ${a.neg}: ${a.n} items\n${Object.entries(a.by).map(([k, v]) => `${k} ${v}`).join(' · ')}${a.sarcasm ? `\nsarcasm cues ${a.sarcasm}` : ''}${a.hedged ? `\nhedging ${a.hedged}` : ''}`}</title>
              <motion.circle cx={x(a.pos)} cy={y(a.neg)} initial={{ r: 0 }} animate={{ r: r(a.n) }} transition={{ type: 'spring', stiffness: 120, damping: 16 }}
                fill={SENTIMENT[dom].color} fillOpacity={isSel ? 0.75 : 0.4} stroke={isSel ? 'var(--fg)' : SENTIMENT[dom].color} strokeWidth={isSel ? 2 : 1} />
              {a.sarcasm > 0 && <circle cx={x(a.pos)} cy={y(a.neg)} r={r(a.n) + 4} fill="none" stroke="#f472b6" strokeDasharray="2 3" />}
              {a.n > 150 && <text x={x(a.pos)} y={y(a.neg) + 4} textAnchor="middle" className="num text-[10px]" fill="var(--fg)">{fmt.int(a.n)}</text>}
            </g>
          )
        })}
      </svg>
      <p className="text-xs text-muted">Each bubble = review-routed items with the same (positive, negative) cue weights; colour = label the rules gave;
        dashed ring = sarcasm cue overrides the region. Click a bubble to filter the queue.</p>
    </div>
  )
}

function QuickReview({ item }: { item: Item }) {
  const { role } = useRole()
  const invalidate = useInvalidateReview()
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<ReviewEvent | null>(null)
  const pick = async (s: Sentiment) => {
    setBusy(true)
    try { setDone(await submitReview(item.source_type, item.source_id, s, role)); await invalidate() } finally { setBusy(false) }
  }
  return (
    <div>
      <RecordCard item={item} compact />
      <div className="mt-1.5 flex items-center gap-2">
        {done ? <span className="text-xs text-muted">saved · {done.decision} as {done.new_sentiment}</span> : <LabelButtons onPick={pick} busy={busy} />}
      </div>
    </div>
  )
}

function Uncertain() {
  const [cell, setCell] = useState<{ pos: number; neg: number } | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  const q = useQueue({ set: 'uncertain', status: 'pending', reason, pos: cell?.pos, neg: cell?.neg, limit: 20 })
  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_1.15fr]">
      <Panel title="Sentiment plane · the classifier's decision regions"><Plane sel={cell} onSel={setCell} /></Panel>
      <Panel title={`Uncertain queue · ${fmt.int(q.data?.total)} pending`}
        right={cell && <button onClick={() => setCell(null)} className="num text-xs text-support">pos {cell.pos} · neg {cell.neg} ✕</button>}>
        <div className="mb-3 flex flex-wrap gap-1.5">
          {q.data?.reasons.map((r) => (
            <button key={r.reason} onClick={() => setReason(reason === r.reason ? null : r.reason)}
              className={`rounded-full border px-2.5 py-0.5 text-xs transition ${reason === r.reason ? 'border-support bg-support/15 text-support' : 'border-line text-muted hover:text-fg'}`}>
              {r.reason.toLowerCase().replaceAll('_', ' ')} <span className="num opacity-70">{fmt.int(r.n)}</span>
            </button>
          ))}
        </div>
        {!q.data ? <Flatline /> : (
          <div className="max-h-[620px] space-y-3 overflow-y-auto pr-1">
            {q.data.items.map((it) => <QuickReview key={it.source_id} item={it} />)}
            {!q.data.items.length && <p className="py-8 text-center text-sm text-muted">Nothing pending here.</p>}
          </div>
        )}
      </Panel>
    </div>
  )
}

export function Review() {
  const [tab, setTab] = useState<'eval' | 'uncertain'>(() =>
    new URLSearchParams(window.location.search).get('tab') === 'uncertain' ? 'uncertain' : 'eval')
  const ev = useQueue({ set: 'eval', status: 'pending', limit: 1 }).data
  const un = useQueue({ set: 'uncertain', status: 'pending', limit: 1 }).data
  const tabs = [
    { k: 'eval' as const, label: 'Evaluation set · blind', n: ev?.total },
    { k: 'uncertain' as const, label: 'Uncertain queue', n: un?.total },
  ]
  return (
    <div className="paper min-h-full space-y-5 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Review</h1>
        <p className="text-sm text-muted">Humans decide where the rules are unsure. Every decision is an append-only <span className="num">label_review_event</span>, recorded with your role.</p>
      </div>
      <div className="flex gap-2">
        {tabs.map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)}
            className={`rounded-lg border px-4 py-2 text-sm transition ${tab === t.k ? 'border-support/50 bg-panel text-fg' : 'border-line text-muted hover:text-fg'}`}>
            {t.label} <span className="num ml-1 text-xs text-muted">{fmt.int(t.n)} pending</span>
          </button>
        ))}
      </div>
      {tab === 'eval' ? <EvalSet /> : <Uncertain />}
    </div>
  )
}
