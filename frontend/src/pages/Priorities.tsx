// Page 2 - Priorities: iso-priority map (priority = x * y, so equal-priority lines are hyperbolas), ranked factor table,
// theme drill-down, and the action board drawn as the contract's state machine.
import { useQueryClient } from '@tanstack/react-query'
import { max, min, scaleLinear, scaleLog } from 'd3'
import { AnimatePresence, motion } from 'motion/react'
import { useMemo, useState } from 'react'
import { setActionStatus, useAction, useActions, useMeta, useThemeDetail, useThemes, type ActionItem, type ActionStatus, type ThemeRank } from '../api/client'
import { useWidth } from '../design/hooks'
import { fmt } from '../design/tokens'
import { Flatline, IdChip, MagnitudeBadge, Panel } from '../design/ui'
import { useWhy } from '../design/why'

const SEV = { 1: '#94a3b8', 2: '#fbbf24', 3: '#f43f5e' } as Record<number, string>
const weighted = (r: ThemeRank) => Number(r.neg_share) * r.severity_weight * (1 + Math.max(Number(r.shift), 0))
const key = (r: ThemeRank) => `${r.product_id}|${r.theme_id}`

function IsoMap({ rows, sel, onSel }: { rows: ThemeRank[]; sel: string | null; onSel: (k: string) => void }) {
  const [ref, w] = useWidth<HTMLDivElement>()
  const [hov, setHov] = useState<ThemeRank | null>(null)
  const h = 380, L = 56, B = 40, T = 14, R = 70
  const x = scaleLog().domain([(min(rows, (r) => Number(r.recent_n)) ?? 1) * 0.8, (max(rows, (r) => Number(r.recent_n)) ?? 10) * 1.3]).range([L, w - R])
  const y = scaleLinear().domain([0, (max(rows, weighted) ?? 1) * 1.12]).range([h - B, T])
  const pMax = max(rows, (r) => Number(r.priority)) ?? 100
  const levels = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000].filter((p) => p >= pMax / 25 && p <= pMax * 1.6)
  const [x0, x1] = x.domain()
  const curve = (p: number) => {
    const pts: string[] = []
    for (let i = 0; i <= 80; i++) {
      const xv = x0 * Math.pow(x1 / x0, i / 80)
      const yv = p / xv
      if (yv <= y.domain()[1] && yv >= 0) pts.push(`${x(xv).toFixed(1)},${y(yv).toFixed(1)}`)
    }
    return pts.length > 1 ? `M${pts.join('L')}` : ''
  }
  const top = new Set([...rows].sort((a, b) => b.priority - a.priority).slice(0, 6).map(key))
  return (
    <div ref={ref} className="relative">
      <svg width={w} height={h}>
        {x.ticks(6).map((t) => (
          <g key={t}><line x1={x(t)} x2={x(t)} y1={T} y2={h - B} stroke="var(--line)" />
            <text x={x(t)} y={h - B + 16} textAnchor="middle" className="num fill-muted text-[10px]">{fmt.int(t)}</text></g>
        ))}
        {y.ticks(5).map((t) => (
          <g key={t}><line x1={L} x2={w - R} y1={y(t)} y2={y(t)} stroke="var(--line)" />
            <text x={L - 8} y={y(t) + 3} textAnchor="end" className="num fill-muted text-[10px]">{fmt.num(t, 1)}</text></g>
        ))}
        <text x={(L + w - R) / 2} y={h - 6} textAnchor="middle" className="fill-muted text-[11px]">volume V · items in last 4 weeks (log scale)</text>
        <text transform={`translate(14 ${(h - B) / 2}) rotate(-90)`} textAnchor="middle" className="fill-muted text-[11px]">N × S × (1 + Δ)</text>
        {levels.map((p, i) => {
          const d = curve(p)
          return (
            <g key={p}>
              <motion.path d={d} fill="none" stroke="#fbbf24" strokeOpacity={0.18 + i * 0.06} strokeDasharray="4 4"
                initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2, delay: i * 0.1 }} />
              <text x={w - R + 6} y={Math.max(T + 8, y(Math.min(p / x1, y.domain()[1])) + 3)} className="num text-[10px]" fill="#fbbf24" fillOpacity={0.7}>P={fmt.int(p)}</text>
            </g>
          )
        })}
        {rows.map((r) => {
          const cx = x(Number(r.recent_n)), cy = y(weighted(r)), k = key(r), s = sel === k
          const c = SEV[r.severity_weight] ?? '#94a3b8'
          return (
            <g key={k} className="cursor-pointer" onClick={() => onSel(k)} onMouseEnter={() => setHov(r)} onMouseLeave={() => setHov(null)}>
              {Number(r.shift) > 0.02 && <circle cx={cx} cy={cy} r={11} fill={c} opacity={0.18} />}
              {r.active_alerts && <motion.circle cx={cx} cy={cy} r={8} fill="none" stroke={c} animate={{ r: [8, 18], opacity: [0.8, 0] }} transition={{ duration: 1.8, repeat: Infinity }} />}
              <circle cx={cx} cy={cy} r={s ? 7 : 4.5} fill={c} stroke={s ? 'var(--fg)' : 'var(--ink)'} strokeWidth={s ? 2 : 1} />
              {(top.has(k) || s) && <text x={cx + 9} y={cy - 6} className="text-[10px]" fill="var(--fg)">{r.product_name} · {r.theme_name}</text>}
            </g>
          )
        })}
      </svg>
      {hov && (
        <div className="pointer-events-none absolute rounded-lg border border-line bg-ink/95 px-3 py-2 text-xs shadow-xl"
          style={{ left: Math.min(x(Number(hov.recent_n)) + 14, w - 260), top: Math.max(0, y(weighted(hov)) - 70) }}>
          <div className="mb-1 font-medium">{hov.product_name} · {hov.theme_name} <span className="num text-muted">#{hov.rank}</span></div>
          <div className="num">{fmt.int(hov.recent_n)} × {fmt.num(hov.neg_share)} × {hov.severity_weight} × (1 + {fmt.num(Math.max(hov.shift, 0))})</div>
          <div className="num">= <b className="text-support">{fmt.num(hov.priority, 1)}</b></div>
        </div>
      )}
      <div className="mt-1 flex flex-wrap gap-4 text-xs text-muted">
        <span>priority = <span className="num">x × y</span>, so dashed hyperbolas are lines of equal priority</span>
        {[1, 2, 3].map((s) => <span key={s} className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: SEV[s] }} />severity {s}</span>)}
        <span>halo = negative share rising · pulse = active alert</span>
      </div>
    </div>
  )
}

function Bar({ v, m, c }: { v: number; m: number; c: string }) {
  return <div className="h-1.5 w-full rounded-full bg-line"><div className="h-full rounded-full" style={{ width: `${Math.max(3, (v / (m || 1)) * 100)}%`, background: c }} /></div>
}

function RankTable({ rows, sel, onSel }: { rows: ThemeRank[]; sel: string | null; onSel: (k: string) => void }) {
  const m = { v: max(rows, (r) => Number(r.recent_n)) ?? 1, p: max(rows, (r) => Number(r.priority)) ?? 1 }
  return (
    <table className="w-full text-sm">
      <thead className="text-left text-[11px] uppercase tracking-wider text-muted">
        <tr><th className="pb-2 pr-2">#</th><th className="pb-2">Product · theme</th><th className="w-24 pb-2">V</th><th className="w-20 pb-2">N</th>
          <th className="w-12 pb-2">S</th><th className="w-16 pb-2">Δ</th><th className="w-40 pb-2">Priority</th></tr>
      </thead>
      <tbody>
        {rows.slice(0, 14).map((r) => (
          <tr key={key(r)} onClick={() => onSel(key(r))}
            className={`cursor-pointer border-t border-line transition ${sel === key(r) ? 'bg-panel2' : 'hover:bg-panel2/50'}`}>
            <td className="num py-2 pr-2 text-muted">{r.rank}</td>
            <td className="py-2">{r.product_name} <span className="text-muted">· {r.theme_name}</span>
              {r.active_alerts && <span className="ml-2 rounded bg-support/15 px-1.5 text-[10px] text-support">alert</span>}</td>
            <td className="py-2 pr-3"><div className="num text-xs">{fmt.int(r.recent_n)}</div><Bar v={Number(r.recent_n)} m={m.v} c="#38bdf8" /></td>
            <td className="py-2 pr-3"><div className="num text-xs">{fmt.pct(r.neg_share, 0)}</div><Bar v={Number(r.neg_share)} m={1} c="#f43f5e" /></td>
            <td className="num py-2" style={{ color: SEV[r.severity_weight] }}>{r.severity_weight}</td>
            <td className="num py-2 text-xs" style={{ color: r.shift > 0 ? '#f43f5e' : '#34d399' }}>{r.shift > 0 ? '+' : ''}{fmt.num(Number(r.shift) * 100, 1)}</td>
            <td className="py-2"><div className="num text-xs font-semibold text-support">{fmt.num(r.priority, 1)}</div><Bar v={Number(r.priority)} m={m.p} c="#fbbf24" /></td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ThemePanel({ k }: { k: string }) {
  const [p, t] = k.split('|')
  const { data } = useThemeDetail(p, t)
  const weeks = useMemo(() => {
    const g = new Map<string, { n: number; neg: number }>()
    for (const c of data?.weekly_cells ?? []) {
      const e = g.get(c.week_start) ?? { n: 0, neg: 0 }
      g.set(c.week_start, { n: e.n + Number(c.n_items), neg: e.neg + Number(c.n_negative) })
    }
    return [...g.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [data])
  if (!data) return <Flatline />
  const mx = max(weeks, ([, v]) => v.n) ?? 1
  const recent = [...data.weekly_cells].sort((a, b) => b.week_start.localeCompare(a.week_start)).slice(0, 6)
  return (
    <div>
      <div className="mb-3 font-medium">{data.product_name} · {data.theme_name}</div>
      <div className="flex h-28 items-end gap-[3px]">
        {weeks.map(([wk, v]) => (
          <div key={wk} className="flex flex-1 flex-col justify-end" title={`week of ${wk}: ${v.n} items, ${v.neg} negative`}>
            <div className="rounded-t-sm bg-neg/80" style={{ height: `${(v.neg / mx) * 100}px` }} />
            <div className="bg-review/30" style={{ height: `${((v.n - v.neg) / mx) * 100}px` }} />
          </div>
        ))}
      </div>
      <div className="mt-1 text-xs text-muted">weekly items (red = negative), Apr → Sep</div>
      <div className="mt-3 text-[11px] uppercase tracking-wider text-muted">Latest weekly cells (click → records)</div>
      <div className="mt-1 space-y-1">
        {recent.map((c) => <div key={c.cell_id} className="flex items-center justify-between text-xs"><IdChip id={c.cell_id} /><span className="num text-muted">{c.n_items} · {fmt.pct(c.neg_share, 0)}</span></div>)}
      </div>
      {!!data.alerts.length && <div className="mt-3 flex flex-wrap gap-2">{data.alerts.map((a) => <IdChip key={a.alert_id} id={a.alert_id} />)}</div>}
    </div>
  )
}

const ORDER: ActionStatus[] = ['OPEN', 'IN_PROGRESS', 'DONE', 'DISMISSED']
const LABEL: Record<ActionStatus, string> = { OPEN: 'Open', IN_PROGRESS: 'In progress', DONE: 'Done', DISMISSED: 'Dismissed' }

function StateMachine({ transitions, counts }: { transitions: [string, string][]; counts: Record<string, number> }) {
  const [ref, w] = useWidth<HTMLDivElement>()
  const col = w / 4, y = 58, nodeW = Math.min(150, col - 24)
  const cx = (s: string) => col * ORDER.indexOf(s as ActionStatus) + col / 2
  return (
    <div ref={ref}>
      <svg width={w} height={92}>
        <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="var(--muted)" /></marker></defs>
        {transitions.filter(([f]) => f).map(([f, t]) => {
          const a = cx(f) + nodeW / 2, b = cx(t) - nodeW / 2, span = ORDER.indexOf(t as ActionStatus) - ORDER.indexOf(f as ActionStatus)
          const lift = span > 1 ? 22 + span * 10 : 0
          return <path key={f + t} d={span > 1 ? `M${cx(f)},${y - 16} C${cx(f)},${y - 16 - lift} ${cx(t)},${y - 16 - lift} ${cx(t)},${y - 16}` : `M${a},${y} L${b},${y}`}
            fill="none" stroke="var(--muted)" strokeOpacity={0.7} markerEnd="url(#arr)" />
        })}
        {ORDER.map((s) => (
          <g key={s}>
            <rect x={cx(s) - nodeW / 2} y={y - 16} width={nodeW} height={32} rx={16} fill="var(--panel2)" stroke="var(--line)" />
            <text x={cx(s)} y={y + 4} textAnchor="middle" className="text-[12px] font-medium" fill="var(--fg)">{LABEL[s]} <tspan className="num" fill="#fbbf24">{counts[s] ?? 0}</tspan></text>
          </g>
        ))}
      </svg>
      <div className="-mt-1 text-center text-[11px] text-muted">lifecycle generated from the data contract · only legal moves are offered · every move is an append-only event</div>
    </div>
  )
}

function ActionCard({ a, next, actor }: { a: ActionItem; next: ActionStatus[]; actor: string }) {
  const qc = useQueryClient()
  const why = useWhy()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const hist = useAction(open ? a.action_item_id : null).data
  const move = async (to: ActionStatus) => {
    setBusy(true)
    try {
      await setActionStatus(a.action_item_id, to, actor || 'analyst')
      for (const k of [['actions'], ['action', a.action_item_id], ['overview'], ['themes']]) await qc.invalidateQueries({ queryKey: k })
    } finally { setBusy(false) }
  }
  return (
    <motion.div layout layoutId={a.action_item_id} className="rounded-lg border border-line bg-panel2/70 p-3">
      <div className="flex items-start gap-3">
        {a.magnitude != null && <MagnitudeBadge m={Number(a.magnitude)} size={30} label={false} />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs text-muted"><IdChip id={a.action_item_id} /><span className="rounded border border-line px-1.5">{a.owner_role}</span><span>{a.kind}</span></div>
          <div className="mt-1 text-sm leading-snug">{a.recommendation}</div>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted">
            <span className="num">priority <b className="text-support">{fmt.num(a.priority_score, 1)}</b></span>
            <button onClick={() => why.open(a.action_item_id)} className="hover:text-fg hover:underline">{a.evidence_count} records →</button>
            <button onClick={() => setOpen((o) => !o)} className="ml-auto hover:text-fg">{open ? 'hide' : 'history'}</button>
          </div>
        </div>
      </div>
      {next.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {next.map((t) => (
            <button key={t} disabled={busy} onClick={() => move(t)}
              className={`rounded-md border px-2.5 py-1 text-xs transition disabled:opacity-40 ${t === 'DISMISSED' ? 'border-line text-muted hover:text-fg' : 'border-support/40 text-support hover:bg-support/10'}`}>
              → {LABEL[t]}
            </button>
          ))}
        </div>
      )}
      <AnimatePresence>
        {open && hist && (
          <motion.ol initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            className="mt-2 space-y-1 overflow-hidden border-l border-line pl-3 text-xs">
            {hist.events.map((e) => (
              <li key={e.event_id} className="num text-muted"><span className="text-fg">{e.from_status ?? '∅'} → {e.to_status}</span> · {e.actor} · {e.event_at.replace('T', ' ').slice(0, 16)}</li>
            ))}
          </motion.ol>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function ActionBoard() {
  const actions = useActions().data ?? []
  const transitions = useMeta().data?.action_transitions ?? []
  const [actor, setActor] = useState(() => { try { return localStorage.getItem('vl-actor') ?? 'analyst' } catch { return 'analyst' } })
  const counts = Object.fromEntries(ORDER.map((s) => [s, actions.filter((a) => a.status === s).length]))
  return (
    <Panel title="Action items · state machine"
      right={<label className="flex items-center gap-2 text-xs text-muted">acting as
        <input value={actor} onChange={(e) => { setActor(e.target.value); try { localStorage.setItem('vl-actor', e.target.value) } catch { /* ignore */ } }}
          className="w-32 rounded border border-line bg-ink px-2 py-1 text-fg focus:outline-none" /></label>}>
      <StateMachine transitions={transitions} counts={counts} />
      <div className="mt-3 grid grid-cols-4 gap-3">
        {ORDER.map((s) => (
          <div key={s} className="min-h-24 space-y-2 rounded-lg bg-ink/40 p-2">
            {actions.filter((a) => a.status === s).map((a) => (
              <ActionCard key={a.action_item_id} a={a} actor={actor}
                next={transitions.filter(([f]) => f === s).map(([, t]) => t as ActionStatus)} />
            ))}
            {!counts[s] && <div className="py-6 text-center text-xs text-muted/60">empty</div>}
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function Priorities() {
  const rows = useThemes().data
  const [sel, setSel] = useState<string | null>(null)
  if (!rows) return <Flatline label="ranking themes…" />
  const current = sel ?? (rows[0] ? key(rows[0]) : null)
  return (
    <div className="paper min-h-full space-y-5 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Priorities</h1>
        <p className="text-sm text-muted">Every recurring product × theme over the last 4 weeks, scored with one formula:
          <span className="num ml-1 text-fg">priority = V × N × S × (1 + Δ)</span></p>
      </div>
      <Panel title="Iso-priority map"><IsoMap rows={rows} sel={current} onSel={setSel} /></Panel>
      <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="Ranked themes · factor bars"><RankTable rows={rows} sel={current} onSel={setSel} /></Panel>
        <Panel title="Selected theme">{current && <ThemePanel k={current} />}</Panel>
      </div>
      <ActionBoard />
    </div>
  )
}
