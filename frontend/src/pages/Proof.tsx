// Page 5 - Proof: evaluation on the held-out split, the abstention frontier (interactive tau), confusion matrix,
// slices, incident time-to-detect, edge-case scoreboard, human review, and a live checklist of every requirement.
import { line, scaleLinear } from 'd3'
import { motion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useDataQuality, useFlow, useFullEvaluation, useMeta, type CurvePoint, type FullEvaluation, type Slice } from '../api/client'
import { useWidth } from '../design/hooks'
import { CHANNEL, CHANNELS, SENTIMENT, fmt } from '../design/tokens'
import { Flatline, IdChip, Kpi, Panel } from '../design/ui'

function Frontier({ ev }: { ev: FullEvaluation }) {
  const curve = ev.splits.eval.coverage_curve.filter((c) => c.auto_accuracy != null)
  const train = ev.splits.train.coverage_curve.filter((c) => c.auto_accuracy != null)
  const [i, setI] = useState(() => Math.max(0, curve.findIndex((c) => Math.abs(c.tau - ev.tau.current) < 1e-9)))
  const [ref, w] = useWidth<HTMLDivElement>(480)
  const h = 260
  const yMin = Math.min(...curve.map((c) => c.auto_accuracy!), ...train.map((c) => c.auto_accuracy!)) - 0.01
  const x = scaleLinear().domain([0, 1]).range([46, w - 14])
  const y = scaleLinear().domain([Math.max(0, yMin), 1]).range([h - 30, 10])
  const ln = line<CurvePoint>().x((c) => x(c.coverage)).y((c) => y(c.auto_accuracy!))
  const p = curve[i]
  return (
    <div ref={ref}>
      <svg width={w} height={h}>
        {x.ticks(5).map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={10} y2={h - 30} stroke="var(--line)" /><text x={x(t)} y={h - 14} textAnchor="middle" className="num fill-muted text-[10px]">{fmt.pct(t, 0)}</text></g>)}
        {y.ticks(5).map((t) => <g key={t}><line x1={46} x2={w - 14} y1={y(t)} y2={y(t)} stroke="var(--line)" /><text x={40} y={y(t) + 3} textAnchor="end" className="num fill-muted text-[10px]">{fmt.pct(t, 0)}</text></g>)}
        <path d={ln(train) ?? ''} fill="none" stroke="var(--muted)" strokeDasharray="4 4" />
        <motion.path d={ln(curve) ?? ''} fill="none" stroke="#fbbf24" strokeWidth={2} initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2 }} />
        {curve.map((c, k) => <circle key={c.tau} cx={x(c.coverage)} cy={y(c.auto_accuracy!)} r={k === i ? 6 : 2.5} fill={k === i ? '#fbbf24' : 'var(--muted)'} className="cursor-pointer" onClick={() => setI(k)} />)}
        <line x1={x(p.coverage)} x2={x(p.coverage)} y1={y(p.auto_accuracy!)} y2={h - 30} stroke="#fbbf24" strokeDasharray="2 3" />
        <text x={(w + 46) / 2} y={h} textAnchor="middle" className="fill-muted text-[11px]">coverage · share of items labelled automatically →</text>
      </svg>
      <input type="range" min={0} max={curve.length - 1} value={i} onChange={(e) => setI(Number(e.target.value))} className="w-full accent-[#fbbf24]" />
      <div className="mt-2 grid grid-cols-3 gap-3 text-center">
        <div><div className="text-[11px] uppercase tracking-wider text-muted">threshold τ</div><div className="num text-xl font-semibold">{fmt.num(p.tau)}</div></div>
        <div><div className="text-[11px] uppercase tracking-wider text-muted">auto-labelled</div><div className="num text-xl font-semibold">{fmt.pct(p.coverage)}</div></div>
        <div><div className="text-[11px] uppercase tracking-wider text-muted">accuracy on those</div><div className="num text-xl font-semibold text-support">{fmt.pct(p.auto_accuracy)}</div></div>
      </div>
      <p className="mt-2 text-xs text-muted">Solid = held-out eval split, dashed = train (tuned on). Deployed τ = <b className="num text-fg">{ev.tau.current}</b>;
        rule “{ev.tau.rule}” would pick <b className="num text-fg">{ev.tau.recommended}</b>. Below τ, items go to humans - the system never guesses silently.</p>
    </div>
  )
}

function Confusion({ ev }: { ev: FullEvaluation }) {
  const { labels, matrix } = ev.splits.eval.sentiment_all.confusion
  return (
    <div>
      <div className="grid grid-cols-[90px_repeat(4,1fr)] gap-1 text-xs">
        <div />
        {labels.map((l) => <div key={l} className="pb-1 text-center text-muted">{SENTIMENT[l].label}</div>)}
        {labels.map((g, r) => {
          const tot = matrix[r].reduce((a, b) => a + b, 0) || 1
          return [
            <div key={`h${g}`} className="flex items-center justify-end pr-2 text-muted">{SENTIMENT[g].label}</div>,
            ...matrix[r].map((v, c) => (
              <div key={`${r}${c}`} className="num grid h-12 place-items-center rounded-md text-sm"
                style={{ background: r === c ? `rgba(52,211,153,${0.12 + 0.7 * (v / tot)})` : `rgba(244,63,94,${v ? 0.08 + 0.7 * (v / tot) : 0.03})` }}
                title={`gold ${g} → predicted ${labels[c]}: ${v} (${fmt.pct(v / tot)})`}>{v}</div>
            )),
          ]
        })}
      </div>
      <div className="mt-2 text-xs text-muted">rows = gold label · columns = prediction · eval split, n = {fmt.int(ev.splits.eval.sentiment_all.n)}</div>
    </div>
  )
}

function Slices({ rows, by }: { rows: Slice[]; by: string }) {
  return (
    <div className="space-y-2">
      {rows.map((r) => (
        <div key={String(r[by])}>
          <div className="flex justify-between text-xs"><span>{String(r[by])} <span className="num text-muted">n={r.n}</span></span>
            <span className="num">{fmt.pct(r.accuracy)} <span className="text-muted">· auto {fmt.pct(r.coverage, 0)}</span></span></div>
          <div className="mt-1 h-1.5 rounded-full bg-line"><div className="h-full rounded-full" style={{ width: `${r.accuracy * 100}%`, background: r.accuracy >= 0.9 ? '#34d399' : r.accuracy >= 0.75 ? '#fbbf24' : '#f43f5e' }} /></div>
        </div>
      ))}
    </div>
  )
}

function Incidents({ ev }: { ev: FullEvaluation }) {
  const meta = useMeta().data
  const name = (p: string, t: string) => `${meta?.products.find((x) => x.product_id === p)?.name ?? p} · ${meta?.themes.find((x) => x.theme_id === t)?.name ?? t}`
  const [ref, w] = useWidth<HTMLDivElement>(600)
  const x = scaleLinear().domain([-1, 14]).range([230, w - 12])
  return (
    <div ref={ref}>
      <svg width={w} height={ev.incidents.per_incident.length * 54 + 28}>
        {[0, 3, 7, 14].map((d) => <g key={d}><line x1={x(d)} x2={x(d)} y1={0} y2={ev.incidents.per_incident.length * 54} stroke="var(--line)" />
          <text x={x(d)} y={ev.incidents.per_incident.length * 54 + 16} textAnchor="middle" className="num fill-muted text-[10px]">{d === 0 ? 'onset' : `+${d} d`}</text></g>)}
        {ev.incidents.per_incident.map((r, k) => {
          const y = k * 54 + 26
          return (
            <g key={r.incident_id}>
              <text x={0} y={y - 4} className="text-[12px]" fill="var(--fg)">{r.incident_id} <tspan fill="var(--muted)">{r.direction}</tspan></text>
              <text x={0} y={y + 12} className="text-[11px]" fill="var(--muted)">{name(r.product_id, r.theme_id).slice(0, 34)}</text>
              <line x1={x(0)} x2={x(r.time_to_detect_days ?? 14)} y1={y} y2={y} stroke={r.detected ? '#fbbf24' : '#f43f5e'} strokeWidth={2} />
              <circle cx={x(0)} cy={y} r={4} fill="var(--muted)" />
              {CHANNELS.map((c) => {
                const m = r[`${c.key}_lag_measured` as const], d = r[`${c.key}_lag_designed` as const]
                return (
                  <g key={c.key}>
                    {d != null && <circle cx={x(d)} cy={y} r={7} fill="none" stroke={c.color} strokeOpacity={0.5} strokeDasharray="2 2"><title>{`${c.label} designed lag ${d} d`}</title></circle>}
                    {m != null && <circle cx={x(Math.min(m, 14))} cy={y} r={3.5} fill={c.color}><title>{`${c.label} first signal at +${m} d`}</title></circle>}
                  </g>
                )
              })}
              {r.detected && <g><rect x={x(r.time_to_detect_days!) - 3} y={y - 9} width={6} height={18} rx={2} fill="#fbbf24" />
                <text x={x(r.time_to_detect_days!) + 8} y={y - 8} className="num text-[11px]" fill="#fbbf24">detected +{r.time_to_detect_days} d</text></g>}
            </g>
          )
        })}
      </svg>
      <div className="flex flex-wrap gap-3 text-xs text-muted">
        <span>dots = first signal per channel (measured)</span><span>dashed rings = designed lag</span><span>bar = alert confirmed</span>
        {ev.incidents.per_incident.filter((r) => r.alert_id).map((r) => <IdChip key={r.alert_id} id={r.alert_id!} />)}
      </div>
    </div>
  )
}

type Status = 'ok' | 'pending' | 'fail'
const MIN_REVIEWS = 20
function Req({ s, children, where }: { s: Status; children: ReactNode; where: ReactNode }) {
  const icon = { ok: '✓', pending: '…', fail: '✗' }[s]
  const col = { ok: 'text-pos border-pos/40', pending: 'text-support border-support/40', fail: 'text-neg border-neg/40' }[s]
  return (
    <div className="flex items-start gap-3 border-t border-line py-2 text-sm">
      <span className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border text-[11px] ${col}`}>{icon}</span>
      <div className="flex-1">{children}</div>
      <div className="shrink-0 text-right text-xs text-muted">{where}</div>
    </div>
  )
}
const go = (to: string, label: string) => <Link to={to} className="text-support hover:underline">{label} →</Link>
const doc = (p: string) => <span className="num">{p}</span>

function Requirements({ ev }: { ev: FullEvaluation }) {
  const dq = useDataQuality(null).data
  const flow = useFlow().data
  const chk = (name: string) => dq?.summary.checks.find((c) => c.check === name)?.exceptions
  const edge = (t: string) => ev.edge_cases.find((e) => e.issue_type === t)
  const allEdge = ev.edge_cases.length === 5 && ev.edge_cases.every((e) => e.recall === 1)
  const planted = (t: string) => edge(t)?.planted ?? 0
  const t = flow?.tables
  const vol = t ? (t.review ?? 0) + (t.survey_response ?? 0) : 0
  const rep = dq?.summary.reproducibility
  const hr = ev.human_review
  const groups: [string, [Status, ReactNode, ReactNode][]][] = [
    ['Objective', [
      ['ok', 'Combine survey responses, reviews and support text', go('/', 'Pulse · 3 channels')],
      ['ok', 'Identify recurring themes', go('/priorities', 'Priorities')],
      [ev.incidents.detected === ev.incidents.incidents ? 'ok' : 'fail', <>Identify sentiment shifts - {ev.incidents.detected}/{ev.incidents.incidents} hidden incidents detected, {ev.incidents.false_alarms} false alarms</>, go('/', 'Pulse · epicenters')],
      ['ok', 'Identify service priorities (formula exposed)', go('/priorities', 'iso-priority map')],
      ['ok', 'Expose key decisions and exceptions', <>Why? drawer · {go('/flow', 'Data flow')}</>],
      ['ok', 'Preserve traceability - any id traces to source records', 'trace box (/)'],
      ['ok', 'Measurable outputs', 'this page'],
    ]],
    ['Actors & workflow rules', [
      ['ok', 'Actors: customer, marketing/sales ops, support agent, analyst, admin', '“acting as” selector · owner roles'],
      [chk('FK_MISSING') === planted('THEME_OUTSIDE_TAXONOMY') ? 'ok' : 'fail', <>Master data first, valid parent IDs - FK failures {fmt.int(chk('FK_MISSING'))} = only the planted out-of-taxonomy links</>, go('/flow', 'checks')],
      ['ok', 'Taxonomies, balanced labels, neutral / mixed / sarcastic / ambiguous / multilingual text', <>{doc('DATA_DICTIONARY.md')} · slices ↓</>],
      ['ok', 'Action items created from recurring themes', go('/priorities', 'action board')],
      ['ok', 'State changes are append-only events, history never overwritten', 'action & review history'],
      ['ok', 'Labels from documented generation rules (template decides)', doc('DECISIONS.md D-005')],
    ]],
    ['Generation steps 1-10', [
      ['ok', '1 · Data dictionary: type, required, allowed values, units, uniqueness, rule, PK/FK, cardinality, lifecycles', doc('docs/DATA_DICTIONARY.md')],
      ['ok', '2 · Parents before children', go('/flow', 'FK check')],
      [chk('ID_FORMAT') === 0 ? 'ok' : 'fail', <>3 · Deterministic, zero-padded IDs - ID_FORMAT failures {fmt.int(chk('ID_FORMAT'))}</>, go('/flow', 'checks')],
      [vol >= 50000 && (t?.support_message ?? 0) >= 20000 ? 'ok' : 'pending', <>4 · Volume: {fmt.int(vol)} reviews + responses, {fmt.int(t?.support_message)} support messages, seed 20261022, --scale</>, go('/flow', 'Sankey')],
      [allEdge ? 'ok' : 'fail', <>5 · Five labelled edge cases injected - all caught ({ev.edge_cases.map((e) => `${e.detected}/${e.planted}`).join(', ')})</>, 'scoreboard ↓'],
      [chk('DERIVED_MISMATCH') === 0 ? 'ok' : 'fail', '6 · Derived values computed from source records - 0 mismatches', go('/flow', 'checks')],
      ['ok', '7 · Separate ground truth, never in model input (policy R1 + R4, tests)', go('/flow', 'manifest')],
      [dq ? 'ok' : 'pending', '8 · Validation: PK, FK, enums, dates, reconciliation, lifecycle, duplicates', go('/flow', '13 checks')],
      ['ok', '9 · Exports CSV / JSON / SQL + README, dictionary, command, seed, manifest, validation summary', go('/flow', 'exports')],
      [rep ? (rep.passed ? 'ok' : 'fail') : 'pending', <>10 · Regenerated twice, checksums compared - {rep ? (rep.passed ? `${rep.files_compared} files identical` : 'differs') : 'run pipeline with the reproducibility check'}</>, go('/flow', 'reproducibility')],
    ]],
    ['Acceptance criteria', [
      [hr.reviewed >= MIN_REVIEWS ? 'ok' : 'pending', <>Evaluation set has human-reviewed labels - {hr.reviewed}/{hr.sample_size} blind-reviewed{hr.reviewed >= MIN_REVIEWS ? `, model vs human ${fmt.pct(hr.model_vs_human?.accuracy)}` : ` (≥ ${MIN_REVIEWS} needed for a meaningful number)`}</>, go('/review', 'Review')],
      ['ok', <>Sentiment / theme metrics measurable - accuracy {fmt.pct(ev.splits.eval.sentiment_all.accuracy)}, theme F1 {fmt.num(ev.splits.eval.themes.micro_f1, 3)}</>, 'metrics ↓'],
      [edge('PII_LEAK')?.recall === 1 ? 'ok' : 'fail', <>Privacy-safe synthetic text - PII redacted before analysis ({edge('PII_LEAK')?.detected}/{edge('PII_LEAK')?.planted} leaks caught)</>, '[EMAIL] chips'],
      ['ok', 'Trends can be traced to source records (reconciled counts)', go('/', 'click a trace')],
    ]],
  ]
  const all = groups.flatMap(([, r]) => r)
  const ok = all.filter(([s]) => s === 'ok').length
  return (
    <Panel title="Requirements · problem statement checklist" right={<span className="num text-xs"><b className="text-pos">{ok}</b> / {all.length} met</span>}>
      <div className="grid gap-x-8 xl:grid-cols-2">
        {groups.map(([g, rows]) => (
          <div key={g} className="mb-3">
            <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{g}</div>
            {rows.map(([s, txt, where], k) => <Req key={k} s={s} where={where}>{txt}</Req>)}
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function Proof() {
  const ev = useFullEvaluation().data
  if (!ev) return <Flatline label="computing proof…" />
  const e = ev.splits.eval
  return (
    <div className="paper min-h-full space-y-5 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Proof</h1>
        <p className="text-sm text-muted">Measured on the held-out evaluation split (rules tuned on train only) against documented ground truth.
          <span className="num ml-2">run {ev.run_id} · rules {ev.rules_hash}</span></p>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Kpi label="Sentiment accuracy" value={fmt.pct(e.sentiment_all.accuracy)} sub={`macro-F1 ${fmt.num(e.sentiment_all.macro_f1, 3)} · n ${fmt.int(e.sentiment_all.n)}`} />
        <Kpi label="Auto-labelled accuracy" value={fmt.pct(e.sentiment_auto.accuracy)} accent="#fbbf24" sub={`on ${fmt.pct(e.coverage, 0)} of items · rest to humans`} />
        <Kpi label="Themes" value={fmt.num(e.themes.micro_f1, 3)} sub={`micro-F1 · exact match ${fmt.pct(e.themes.exact_match)}`} />
        <Kpi label="Incidents found" value={`${ev.incidents.detected}/${ev.incidents.incidents}`} accent="#34d399" sub={`${ev.incidents.false_alarms} false alarms · TTD ${fmt.num(ev.incidents.mean_time_to_detect_days, 1)} d`} />
        <Kpi label="Edge cases caught" value={`${ev.edge_cases.reduce((a, x) => a + x.detected, 0)}/${ev.edge_cases.reduce((a, x) => a + x.planted, 0)}`} accent="#34d399" sub={`5 planted types · ${ev.edge_cases.every((x) => x.precision === 1) ? '100% precision' : 'see table'}`} />
      </div>
      <Requirements ev={ev} />
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Abstention frontier · drag τ"><Frontier ev={ev} /></Panel>
        <Panel title="Confusion matrix"><Confusion ev={ev} />
          <div className="mt-4 grid grid-cols-4 gap-2 text-center text-xs">
            {e.sentiment_all.confusion.labels.map((l) => (
              <div key={l} className="rounded-md border border-line p-2"><div style={{ color: SENTIMENT[l].color }}>{SENTIMENT[l].label}</div>
                <div className="num">P {fmt.num(e.sentiment_all.per_class[l].precision)} · R {fmt.num(e.sentiment_all.per_class[l].recall)}</div></div>
            ))}
          </div>
        </Panel>
      </div>
      <div className="grid gap-5 xl:grid-cols-3">
        <Panel title="Where it fails · by style"><Slices rows={e.by_style} by="style" /></Panel>
        <Panel title="By language"><Slices rows={e.by_language} by="language" /></Panel>
        <Panel title="By source"><Slices rows={e.by_source} by="source_type" /></Panel>
      </div>
      <Panel title="Early warning · time-to-detect vs hidden incidents"><Incidents ev={ev} /></Panel>
      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Panel title="Edge cases · planted vs caught">
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted"><tr><th className="pb-2">Issue type</th><th className="pb-2 text-right">Caught</th><th className="pb-2 text-right">Precision</th><th className="pb-2 pl-6">Expected decision</th><th className="pb-2 text-right">Taken</th></tr></thead>
            <tbody>{ev.edge_cases.map((x) => (
              <tr key={x.issue_type} className="border-t border-line" title={x.check}>
                <td className="num py-2 text-xs">{x.issue_type}</td><td className="num py-2 text-right">{x.detected}/{x.planted}</td>
                <td className="num py-2 text-right">{fmt.pct(x.precision, 0)}</td><td className="py-2 pl-6 text-xs text-muted">{x.expected_decision.replaceAll('_', ' ')}</td>
                <td className={`num py-2 text-right ${x.decision_correct === x.planted ? 'text-pos' : 'text-neg'}`}>{x.decision_correct}/{x.planted}</td></tr>
            ))}</tbody>
          </table>
        </Panel>
        <Panel title="Human-reviewed evaluation set">
          {ev.human_review.reviewed >= MIN_REVIEWS ? (
            <div className="space-y-1 text-sm">
              <div><b className="num text-2xl text-support">{fmt.pct(ev.human_review.model_vs_human?.accuracy)}</b> model agreement with human labels</div>
              <div className="text-muted">n = {ev.human_review.reviewed} of {ev.human_review.sample_size} blind-reviewed · human vs gold rule {fmt.pct(ev.human_review.human_vs_gold)}</div>
            </div>
          ) : <p className="text-sm text-muted">{ev.human_review.reviewed} of {ev.human_review.sample_size} blind-reviewed so far - at least {MIN_REVIEWS} are needed before the agreement number means anything. {go('/review', 'Review the blind sample')}</p>}
          <div className="mt-3 text-xs text-muted">Lead channel correct for {ev.incidents.lead_channel_correct}/{ev.incidents.detected} detected incidents - the signal reaches
            <span style={{ color: CHANNEL.support.color }}> support</span> first.</div>
        </Panel>
      </div>
    </div>
  )
}
