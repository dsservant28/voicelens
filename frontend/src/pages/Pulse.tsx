// Page 1 - Pulse: the seismograph of three channels, alert epicenters, and the wavefront of the selected alert.
import { area, curveMonotoneX, line, max, scaleLinear, scaleTime, timeMonth } from 'd3'
import { motion } from 'motion/react'
import { useMemo, useState } from 'react'
import { useAction, useAlert, useAlerts, useOverview, usePulse, useTrendItems, type Alert, type Channel, type PulseRow } from '../api/client'
import { DAY, daysBetween, toDate, useWidth } from '../design/hooks'
import { RecordCard } from '../design/record'
import { CHANNEL, CHANNELS, fmt, magColor } from '../design/tokens'
import { Flatline, IdChip, Kpi, MagnitudeBadge, Panel } from '../design/ui'
import { useWhy } from '../design/why-context'

const GOOD = '#34d399'
const alertColor = (a: Alert) => (a.direction === 'improve' ? GOOD : magColor(Number(a.magnitude)))
const ROLL = 7

/** 7-day rolling negatives per channel on a continuous daily axis. */
function useSeries(rows: PulseRow[] | undefined) {
  return useMemo(() => {
    if (!rows?.length) return null
    const days = [...new Set(rows.map((r) => r.day))].sort()
    const start = toDate(days[0]).getTime()
    const n = daysBetween(days[0], days[days.length - 1]) + 1
    const out = {} as Record<Channel, { d: Date; v: number; raw: number }[]>
    for (const c of CHANNELS) {
      const raw = new Array(n).fill(0)
      for (const r of rows) if (r.channel_type === c.key) raw[daysBetween(days[0], r.day)] = Number(r.negatives)
      let run = 0
      out[c.key] = raw.map((v, i) => {
        run += v - (i >= ROLL ? raw[i - ROLL] : 0)
        return { d: new Date(start + i * DAY), v: run, raw: v }
      })
    }
    return { series: out, from: new Date(start), to: new Date(start + (n - 1) * DAY) }
  }, [rows])
}

export interface Pick { day: Date; channel: Channel; value: number }

function Seismograph({ alerts, selected, onSelect, onPick }: { alerts: Alert[]; selected: string | null; onSelect: (id: string) => void; onPick: (p: Pick) => void }) {
  const { data } = usePulse()
  const s = useSeries(data)
  const [ref, w] = useWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  if (!s) return <div ref={ref}><Flatline /></div>
  const L = 92, R = 16, lane = 74, top = 22, marks = 92
  const h = top + lane * 3 + marks
  const x = scaleTime().domain([s.from, s.to]).range([L, w - R])
  const n = s.series.support.length
  const placed = [...alerts].sort((a, b) => a.detected_date.localeCompare(b.detected_date))
    .map((a, i, arr) => ({ a, row: arr.slice(0, i).filter((b) => daysBetween(b.detected_date, a.detected_date) < 12).length % 3 }))
  return (
    <div ref={ref} className="relative">
      <svg width={w} height={h} className="block select-none"
        onMouseMove={(e) => {
          const px = e.clientX - e.currentTarget.getBoundingClientRect().left
          const i = Math.round((x.invert(px).getTime() - s.from.getTime()) / DAY)
          setHover(px >= L && px <= w - R ? Math.max(0, Math.min(n - 1, i)) : null)
        }}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => {
          const py = e.clientY - e.currentTarget.getBoundingClientRect().top
          const li = Math.floor((py - top) / lane)
          if (hover == null || li < 0 || li > 2) return
          const c = CHANNELS[li].key
          onPick({ day: s.series[c][hover].d, channel: c, value: s.series[c][hover].v })
        }}
        style={{ cursor: hover != null ? 'crosshair' : 'default' }}>
        {timeMonth.range(s.from, s.to).map((m) => (
          <g key={m.toISOString()}>
            <line x1={x(m)} x2={x(m)} y1={top - 6} y2={top + lane * 3} stroke="var(--line)" />
            <text x={x(m) + 4} y={12} className="fill-muted text-[10px]">{m.toLocaleDateString('en-GB', { month: 'short' })}</text>
          </g>
        ))}
        {placed.map(({ a }) => (
          <rect key={`band-${a.alert_id}`} x={x(toDate(a.start_date))} y={top} height={lane * 3}
            width={Math.max(2, x(toDate(a.end_date)) - x(toDate(a.start_date)))}
            fill={alertColor(a)} opacity={selected === a.alert_id ? 0.16 : 0.06} />
        ))}
        {CHANNELS.map((c, ci) => {
          const pts = s.series[c.key]
          const y = scaleLinear().domain([0, max(pts, (p) => p.v) || 1]).range([top + lane * (ci + 1) - 6, top + lane * ci + 8])
          const ln = line<(typeof pts)[number]>().x((p) => x(p.d)).y((p) => y(p.v)).curve(curveMonotoneX)
          const ar = area<(typeof pts)[number]>().x((p) => x(p.d)).y0(y(0)).y1((p) => y(p.v)).curve(curveMonotoneX)
          return (
            <g key={c.key}>
              <line x1={L} x2={w - R} y1={y(0)} y2={y(0)} stroke="var(--line)" />
              <text x={8} y={top + lane * ci + 30} className="text-[12px] font-medium" fill={c.color}>{c.label}</text>
              <text x={8} y={top + lane * ci + 46} className="fill-muted text-[10px]">{c.lag}</text>
              <path d={ar(pts) ?? ''} fill={c.color} opacity={0.08} />
              <motion.path d={ln(pts) ?? ''} fill="none" stroke={c.color} strokeWidth={1.4} strokeDasharray={c.dash}
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.6, delay: ci * 0.25 }} />
              {hover != null && <circle cx={x(pts[hover].d)} cy={y(pts[hover].v)} r={3.5} fill={c.color} />}
            </g>
          )
        })}
        {placed.map(({ a, row }) => {
          const ax = x(toDate(a.detected_date))
          const col = alertColor(a)
          const sel = selected === a.alert_id
          const cy = top + lane * 3 + 18 + row * 26
          const r = 6 + Math.min(10, Math.log2(Number(a.magnitude) / 5 + 1) * 2.6)
          return (
            <g key={a.alert_id} className="cursor-pointer" onClick={() => onSelect(a.alert_id)}>
              <line x1={ax} x2={ax} y1={top} y2={cy - r} stroke={col} strokeWidth={sel ? 1.6 : 1} strokeDasharray={sel ? '' : '3 3'} />
              {[1, 0.66, 0.33].map((k, i) => (
                <circle key={i} cx={ax} cy={cy} r={r * k} fill={i === 2 ? col : 'none'} stroke={col} strokeOpacity={sel ? 1 : 0.6} />
              ))}
              {sel && <motion.circle cx={ax} cy={cy} r={r} fill="none" stroke={col} initial={{ r, opacity: 0.8 }}
                animate={{ r: r * 2.6, opacity: 0 }} transition={{ duration: 1.6, repeat: Infinity }} />}
              <text x={ax + r + 4} y={cy + 4} className="num text-[10px]" fill={col}>M{Math.round(Number(a.magnitude))}</text>
            </g>
          )
        })}
        {hover != null && (
          <line x1={x(s.series.support[hover].d)} x2={x(s.series.support[hover].d)} y1={top} y2={top + lane * 3}
            stroke="var(--muted)" strokeDasharray="2 3" />
        )}
      </svg>
      {hover != null && (
        <div className="pointer-events-none absolute top-2 rounded-lg border border-line bg-ink/95 px-3 py-2 text-xs shadow-xl"
          style={{ left: Math.min(x(s.series.support[hover].d) + 12, w - 190) }}>
          <div className="num mb-1 text-muted">{s.series.support[hover].d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</div>
          {CHANNELS.map((c) => (
            <div key={c.key} className="flex justify-between gap-4">
              <span style={{ color: c.color }}>{c.label}</span>
              <span className="num">{s.series[c.key][hover].v} <span className="text-muted">/7d</span></span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** Rings expand from the first channel to fire; each lane lights up at its measured arrival delay. */
function Wavefront({ a }: { a: Alert }) {
  const [ref, w] = useWidth<HTMLDivElement>(420)
  const first = { support: a.first_support_date, review: a.first_review_date, survey: a.first_survey_date }
  const known = Object.values(first).filter(Boolean) as string[]
  if (!known.length) return <p className="text-sm text-muted">No per-channel signal recorded for this alert.</p>
  const t0 = known.sort()[0]
  const off = Object.fromEntries(CHANNELS.map((c) => [c.key, first[c.key] ? daysBetween(t0, first[c.key]!) : null])) as Record<Channel, number | null>
  const span = Math.max(7, ...Object.values(off).map((v) => v ?? 0)) + 2
  const L = 76, laneH = 46, h = laneH * 3 + 34
  const x = scaleLinear().domain([0, span]).range([L, w - 16])
  const cycle = 3.2
  const col = alertColor(a)
  return (
    <div ref={ref}>
      <svg width={w} height={h}>
        <defs><clipPath id="wf"><rect x={L} y={0} width={w - L} height={h} /></clipPath></defs>
        {Array.from({ length: span + 1 }, (_, d) => d).filter((d) => d % 2 === 0).map((d) => (
          <g key={d}>
            <line x1={x(d)} x2={x(d)} y1={6} y2={laneH * 3 + 6} stroke="var(--line)" />
            <text x={x(d)} y={h - 8} textAnchor="middle" className="num fill-muted text-[10px]">{d === 0 ? 'day 0' : `+${d}`}</text>
          </g>
        ))}
        <g clipPath="url(#wf)">
          {[0, 1, 2].map((k) => (
            <motion.circle key={k} cx={x(0)} cy={laneH * 1.5 + 6} fill="none" stroke={col} strokeWidth={1.2}
              initial={{ r: 0, opacity: 0.7 }} animate={{ r: x(span) - x(0), opacity: 0 }}
              transition={{ duration: cycle, delay: k * (cycle / 3), repeat: Infinity, ease: 'linear' }} />
          ))}
        </g>
        {CHANNELS.map((c, i) => {
          const y = laneH * i + laneH / 2 + 6
          const d = off[c.key]
          return (
            <g key={c.key}>
              <text x={0} y={y + 4} className="text-[12px] font-medium" fill={c.color}>{c.label}</text>
              <line x1={L} x2={w - 16} y1={y} y2={y} stroke={c.color} strokeOpacity={0.25} strokeDasharray={c.dash || undefined} />
              {d == null ? (
                <text x={w - 16} y={y - 6} textAnchor="end" className="fill-muted text-[10px]">no signal in window</text>
              ) : (
                <>
                  <line x1={L} x2={x(d)} y1={y} y2={y} stroke={c.color} strokeWidth={2} strokeDasharray={c.dash || undefined} />
                  <motion.circle cx={x(d)} cy={y} r={7} fill={c.color} initial={{ scale: 0 }} animate={{ scale: [0, 1.5, 1] }}
                    transition={{ delay: 0.3 + (d / span) * cycle * 0.9, duration: 0.5 }} style={{ originX: '50%', originY: '50%' }} />
                  <text x={x(d) + 12} y={y + 4} className="num text-[11px]" fill={c.color}>{d === 0 ? 'first' : `+${d} d`}</text>
                </>
              )}
            </g>
          )
        })}
      </svg>
      <p className="mt-1 text-xs text-muted">
        Measured from the alert's own per-channel tests (7-day window vs 28-day baseline). Lead channel:{' '}
        <b style={{ color: a.lead_channel ? CHANNEL[a.lead_channel].color : undefined }}>{a.lead_channel ? CHANNEL[a.lead_channel].label : '–'}</b>.
      </p>
    </div>
  )
}

function DailySignal({ a, series }: { a: Alert; series: { day: string; channel_type: Channel; negatives: number }[] }) {
  const [ref, w] = useWidth<HTMLDivElement>(420)
  if (!series.length) return null
  const days = [...new Set(series.map((r) => r.day))].sort()
  const x = scaleTime().domain([toDate(days[0]), toDate(days[days.length - 1])]).range([8, w - 8])
  const h = 120
  const y = scaleLinear().domain([0, max(series, (r) => Number(r.negatives)) || 1]).range([h - 18, 8])
  return (
    <div ref={ref}>
      <svg width={w} height={h}>
        <rect x={x(toDate(a.start_date))} y={4} height={h - 22} width={Math.max(2, x(toDate(a.end_date)) - x(toDate(a.start_date)))} fill={alertColor(a)} opacity={0.12} />
        <line x1={x(toDate(a.detected_date))} x2={x(toDate(a.detected_date))} y1={4} y2={h - 18} stroke={alertColor(a)} />
        <text x={x(toDate(a.detected_date)) + 4} y={14} className="num text-[10px]" fill={alertColor(a)}>detected</text>
        {CHANNELS.map((c) => {
          const pts = days.map((d) => ({ d, v: Number(series.find((r) => r.day === d && r.channel_type === c.key)?.negatives ?? 0) }))
          const ln = line<(typeof pts)[number]>().x((p) => x(toDate(p.d))).y((p) => y(p.v)).curve(curveMonotoneX)
          return <path key={c.key} d={ln(pts) ?? ''} fill="none" stroke={c.color} strokeWidth={1.3} strokeDasharray={c.dash || undefined} />
        })}
        <text x={8} y={h - 4} className="num fill-muted text-[10px]">{fmt.date(days[0])}</text>
        <text x={w - 8} y={h - 4} textAnchor="end" className="num fill-muted text-[10px]">{fmt.date(days[days.length - 1])}</text>
      </svg>
      <div className="text-xs text-muted">negative items per day, this product × theme</div>
    </div>
  )
}

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

/** The records behind one seismograph point: negatives of that channel in the 7 days ending that day. */
function PointRecords({ p, onClose }: { p: Pick; onClose: () => void }) {
  const from = new Date(p.day.getTime() - (ROLL - 1) * DAY)
  const { data } = useTrendItems({ date_from: iso(from), date_to: iso(p.day), channel_type: p.channel, sentiment: 'negative' })
  const ch = CHANNEL[p.channel]
  return (
    <Panel title={<>Records behind this point · <span style={{ color: ch.color }}>{ch.label}</span> · {fmt.date(iso(from))} – {fmt.date(iso(p.day))}</>}
      right={<button onClick={onClose} className="text-xs text-muted hover:text-fg">close ✕</button>}>
      {!data ? <Flatline label="fetching records…" /> : (
        <>
          <div className="mb-3 flex items-center gap-3 text-sm">
            <span className="num">trace value <b>{p.value}</b> = <b>{fmt.int(data.total)}</b> negative records</span>
            {data.total === p.value
              ? <span className="rounded-full border border-pos/40 px-2 py-0.5 text-xs text-pos">✓ reconciled</span>
              : <span className="rounded-full border border-neg/40 px-2 py-0.5 text-xs text-neg">✗ mismatch</span>}
            {data.total > data.items.length && <span className="text-xs text-muted">showing first {data.items.length}</span>}
          </div>
          <div className="grid max-h-[480px] gap-2 overflow-y-auto pr-1 lg:grid-cols-2">
            {data.items.map((it) => <RecordCard key={it.source_id} item={it} compact />)}
          </div>
        </>
      )}
    </Panel>
  )
}

function Epicenter({ id }: { id: string }) {
  const { data } = useAlert(id)
  const act = useAction(data?.alert.action_item_id ?? null).data
  const why = useWhy()
  if (!data) return <Flatline label="locating epicenter…" />
  const a = data.alert
  const inp = act ? (JSON.parse(act.action_item.priority_inputs) as { volume: number; neg_share: number; severity_weight: number; shift: number }) : null
  return (
    <motion.div key={id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
      <Panel title={<>Wavefront · <span className="normal-case tracking-normal">how the signal reached each channel</span></>}>
        <Wavefront a={a} />
      </Panel>
      <Panel title="Epicenter">
        <div className="flex items-start gap-4">
          <MagnitudeBadge m={Number(a.magnitude)} size={64} label={false} />
          <div className="min-w-0 flex-1">
            <div className="text-lg font-semibold leading-tight">{a.product_name} · {a.theme_name}</div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
              <IdChip id={a.alert_id} />
              <span className="num" style={{ color: alertColor(a) }}>M {fmt.num(a.magnitude, 1)} · {a.kind}</span>
              <span className="num">detected {fmt.date(a.detected_date)} (fired {fmt.date(a.start_date)})</span>
              <span>{a.status === 'ACTIVE' ? 'active' : `ended ${fmt.date(a.end_date)}`}</span>
            </div>
            <div className="num mt-2 text-sm">negative share {fmt.pct(a.baseline_share)} <span className="text-muted">→</span> <b style={{ color: alertColor(a) }}>{fmt.pct(a.window_share)}</b>
              <span className="text-xs text-muted"> ({a.shift > 0 ? '+' : ''}{fmt.num(Number(a.shift) * 100, 0)} pts vs 28-day baseline)</span></div>
          </div>
        </div>
        <div className="mt-3"><DailySignal a={a} series={data.daily_series} /></div>
        {act && inp && (
          <div className="mt-3 rounded-lg border border-support/30 bg-support/5 p-3 text-sm">
            <div className="flex items-center gap-2"><IdChip id={act.action_item.action_item_id} /><span className="text-xs text-muted">{act.action_item.owner_role} · {act.action_item.status}</span></div>
            <div className="mt-1">{act.action_item.recommendation}</div>
            <div className="num mt-1 text-xs text-muted">priority = {fmt.int(inp.volume)} × {fmt.num(inp.neg_share)} × {inp.severity_weight} × (1 + {fmt.num(Math.max(inp.shift, 0))}) = <b className="text-support">{fmt.num(act.action_item.priority_score, 1)}</b></div>
          </div>
        )}
      </Panel>
      <Panel className="xl:col-span-2" title={`Evidence · ${fmt.int(a.evidence_count)} records behind this alert`}
        right={<button onClick={() => why.open(a.alert_id)} className="text-xs text-support hover:underline">open full lineage →</button>}>
        <div className="grid gap-2 lg:grid-cols-2">
          {data.evidence.slice(0, 6).map((it) => <RecordCard key={it.source_id} item={it} compact />)}
        </div>
      </Panel>
    </motion.div>
  )
}

export function Pulse() {
  const ov = useOverview().data
  const alerts = useAlerts().data ?? []
  const [sel, setSel] = useState<string | null>(null)
  const [pick, setPick] = useState<Pick | null>(null)
  const strongest = [...alerts].sort((a, b) => Number(b.magnitude) - Number(a.magnitude))[0]?.alert_id ?? null
  const current = sel ?? strongest
  const k = ov?.kpis
  const delta = k ? (Number(k.neg_share_last_28d) - Number(k.neg_share_prev_28d)) * 100 : null
  return (
    <div className="paper min-h-full space-y-5 p-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Pulse</h1>
          <p className="text-sm text-muted">Three channels, one timeline. Epicenters mark statistically confirmed shifts (M = −log₁₀ p ≥ 5).</p>
        </div>
        <span className="num text-xs text-muted">data until {fmt.date(k?.data_until)}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Feedback items" value={fmt.int(k?.items)} sub="reviews · surveys · support" />
        <Kpi label="Negative share · 28 d" value={fmt.pct(k?.neg_share_last_28d)}
          sub={delta == null ? '' : <span style={{ color: delta > 0 ? '#f43f5e' : '#34d399' }}>{delta > 0 ? '▲' : '▼'} {Math.abs(delta).toFixed(1)} pts vs previous 28 d</span>} />
        <Kpi label="Alerts" value={fmt.int(k?.alerts)} sub={`${fmt.int(k?.active_alerts)} active now`} accent="#fbbf24" />
        <Kpi label="Auto-labelled" value={fmt.pct(k?.auto_coverage)} sub={`${fmt.int(k?.review_pending)} routed to humans`} />
      </div>
      <Panel title="Seismograph · 7-day rolling negatives per channel"
        right={<span className="text-xs text-muted">click a trace → its records · click an epicenter → its wavefront</span>}>
        <Seismograph alerts={alerts} selected={current} onSelect={setSel} onPick={setPick} />
        <div className="mt-2 flex flex-wrap gap-2">
          {[...alerts].sort((a, b) => a.detected_date.localeCompare(b.detected_date)).map((a) => (
            <button key={a.alert_id} onClick={() => setSel(a.alert_id)}
              className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs transition ${current === a.alert_id ? 'border-fg/40 bg-panel2' : 'border-line hover:border-muted/50'}`}>
              <span className="h-2 w-2 rounded-full" style={{ background: alertColor(a) }} />
              <span className="num">{fmt.date(a.detected_date)}</span>
              <span>{a.product_name} · {a.theme_name}</span>
              <span className="num" style={{ color: alertColor(a) }}>M{Math.round(Number(a.magnitude))}</span>
            </button>
          ))}
        </div>
      </Panel>
      {pick && <PointRecords key={`${pick.channel}-${pick.day.getTime()}`} p={pick} onClose={() => setPick(null)} />}
      {current && <Epicenter id={current} />}
    </div>
  )
}
