// Page 4 - Data flow: every loaded row accounted for (reconciled Sankey), the ingest-gate checks, exceptions,
// reproducibility, file integrity and the exported files (manifest).
import { sankey, sankeyLinkHorizontal, type SankeyGraph } from 'd3-sankey'
import { motion } from 'motion/react'
import { useState } from 'react'
import { useDataQuality, useFlow } from '../api/client'
import { useWidth } from '../design/hooks'
import { fmt } from '../design/tokens'
import { Flatline, IdChip, Kpi, Panel } from '../design/ui'

const COLOR: Record<string, string> = {
  Reviews: '#38bdf8', 'Survey responses': '#c084fc', 'Support messages': '#fbbf24', 'Reference & events': '#64748b',
  Quarantined: '#f43f5e', Flagged: '#fb923c', Clean: '#94a3b8',
  'Excluded · audit only': '#f43f5e', 'Agent replies · context': '#64748b', 'Reference data': '#64748b', Analysed: '#38bdf8',
  'Auto-labelled': '#34d399', 'Human review': '#f472b6',
}
type N = { name: string; stage: number }
type L = { source: string; target: string; value: number }

function Sankey() {
  const { data } = useFlow()
  const [ref, w] = useWidth<HTMLDivElement>()
  const [hov, setHov] = useState<string | null>(null)
  if (!data) return <div ref={ref}><Flatline /></div>
  const h = 470
  const gen = sankey<N, L>().nodeId((d) => d.name).nodeAlign((d) => d.stage).nodeWidth(14).nodePadding(34)
    .extent([[160, 30], [w - 190, h - 6]])
  const g = gen({ nodes: data.nodes.map((d) => ({ ...d })), links: data.links.map((d) => ({ ...d })) } as SankeyGraph<N, L>)
  const r = data.reconciliation
  return (
    <div ref={ref}>
      <svg width={w} height={h}>
        {g.links.map((l, i) => {
          const s = (l.source as N).name, t = (l.target as N).name
          const on = !hov || hov === s || hov === t
          return (
            <motion.path key={i} d={sankeyLinkHorizontal()(l) ?? ''} fill="none" stroke={COLOR[t] ?? '#94a3b8'}
              strokeWidth={Math.max(1.5, l.width ?? 1)} initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: on ? 0.38 : 0.08 }} transition={{ duration: 1, delay: (l.source as N).stage * 0.25 }}>
              <title>{`${s} → ${t}: ${fmt.int(l.value)} rows`}</title>
            </motion.path>
          )
        })}
        {g.nodes.map((n) => {
          const left = n.stage === 0
          return (
            <g key={n.name} onMouseEnter={() => setHov(n.name)} onMouseLeave={() => setHov(null)} className="cursor-default">
              <rect x={n.x0} y={n.y0} width={(n.x1 ?? 0) - (n.x0 ?? 0)} height={Math.max(2, (n.y1 ?? 0) - (n.y0 ?? 0))} rx={2} fill={COLOR[n.name] ?? '#94a3b8'} />
              {(n.y1 ?? 0) - (n.y0 ?? 0) < 18 ? (
                <text x={left ? (n.x0 ?? 0) - 8 : (n.x1 ?? 0) + 8} y={((n.y0 ?? 0) + (n.y1 ?? 0)) / 2 + 4} textAnchor={left ? 'end' : 'start'} className="text-[12px]" fill="var(--fg)">
                  {n.name} <tspan className="num text-[11px]" fill="var(--muted)">{fmt.int(n.value)}</tspan></text>
              ) : (
                <>
                  <text x={left ? (n.x0 ?? 0) - 8 : (n.x1 ?? 0) + 8} y={((n.y0 ?? 0) + (n.y1 ?? 0)) / 2 - 2} textAnchor={left ? 'end' : 'start'} className="text-[12px]" fill="var(--fg)">{n.name}</text>
                  <text x={left ? (n.x0 ?? 0) - 8 : (n.x1 ?? 0) + 8} y={((n.y0 ?? 0) + (n.y1 ?? 0)) / 2 + 12} textAnchor={left ? 'end' : 'start'} className="num text-[11px]" fill="var(--muted)">{fmt.int(n.value)}</text>
                </>
              )}
            </g>
          )
        })}
        {['source', 'ingest gate', 'use', 'routing'].map((t, i) => (
          <text key={t} x={160 + ((w - 350) / 3) * i + (i === 0 ? 0 : 7)} y={12} className="fill-muted text-[10px] uppercase tracking-widest" textAnchor={i === 0 ? 'start' : i === 3 ? 'end' : 'middle'}>{t}</text>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-2 text-xs">
        {[
          [`rows in ${fmt.int(r.rows_in)} = rows out ${fmt.int(r.rows_out)}`, r.balanced],
          [`analysed ${fmt.int(r.analysed)} = feedback items ${fmt.int(r.feedback_items)}`, r.analysed_matches_items],
          [`auto + review ${fmt.int(r.routed)} = items`, r.routed_matches_items],
        ].map(([t, ok]) => (
          <span key={String(t)} className={`num rounded-full border px-2.5 py-0.5 ${ok ? 'border-pos/40 text-pos' : 'border-neg/40 text-neg'}`}>{ok ? '✓' : '✗'} {t}</span>
        ))}
      </div>
    </div>
  )
}

export function Flow() {
  const [type, setType] = useState<string | null>(null)
  const dq = useDataQuality(type).data
  const [showFiles, setShowFiles] = useState(false)
  if (!dq) return <Flatline label="auditing data…" />
  const s = dq.summary, rep = s.reproducibility
  const maxN = Math.max(...dq.by_type.map((b) => Number(b.n)), 1)
  return (
    <div className="paper min-h-full space-y-5 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Data flow</h1>
        <p className="text-sm text-muted">Every row is accounted for. Bad rows are quarantined - kept for audit, never silently dropped, never allowed to crash the run.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Rows checked" value={fmt.int(s.total_rows)} sub={`seed ${s.seed} · scale ${s.scale}`} />
        <Kpi label="Validation" value={s.status === 'FAIL' ? 'FAIL' : 'PASS'} accent={s.status === 'FAIL' ? '#f43f5e' : '#34d399'} sub={`${fmt.int(s.total_exceptions)} exceptions raised by 13 checks`} />
        <Kpi label="Quarantined" value={fmt.int(s.quarantined_rows)} accent="#f43f5e" sub="excluded from analysis, kept for audit" />
        <Kpi label="Reproducible" value={rep ? (rep.passed ? 'identical' : 'DIFFERS') : 'not run'} accent={rep?.passed ? '#34d399' : undefined}
          sub={rep ? `generated twice · ${rep.files_compared} files · SHA-256` : 'run with reproducibility check'} />
      </div>
      <Panel title="Where every row goes"><Sankey /></Panel>
      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <Panel title="Ingest-gate checks · driven by the data contract">
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted"><tr><th className="pb-2">Check</th><th className="pb-2">Category</th><th className="pb-2">On failure</th><th className="pb-2 text-right">Exceptions</th></tr></thead>
            <tbody>
              {s.checks.map((c) => (
                <tr key={c.check} className="border-t border-line" title={c.description}>
                  <td className="num py-1.5 text-xs">{c.check}<div className="font-sans text-[11px] text-muted">{c.description}</div></td>
                  <td className="py-1.5 text-xs text-muted">{c.category}</td>
                  <td className={`py-1.5 text-xs ${c.disposition === 'QUARANTINE' ? 'text-neg' : 'text-[#fb923c]'}`}>{c.disposition.toLowerCase()}</td>
                  <td className={`num py-1.5 text-right ${c.exceptions ? 'text-fg' : 'text-pos'}`}>{c.exceptions ? fmt.int(c.exceptions) : '0 ✓'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-muted">Derived values (survey status, ticket status and closed date, per-parent ID counters, channel/product consistency) are recomputed from source records - DERIVED_MISMATCH counts any disagreement.</p>
        </Panel>
        <Panel title="Exceptions by type · validation + analysis" right={type && <button onClick={() => setType(null)} className="text-xs text-support">{type} ✕</button>}>
          <div className="space-y-1.5">
            {dq.by_type.map((b) => (
              <button key={b.exception_type + b.detected_by} onClick={() => setType(b.exception_type)}
                className={`block w-full rounded-md px-2 py-1 text-left transition hover:bg-panel2 ${type === b.exception_type ? 'bg-panel2' : ''}`}>
                <div className="flex justify-between text-xs"><span className="num">{b.exception_type}</span>
                  <span className="text-muted">{b.disposition.toLowerCase()} · {b.detected_by} · <b className="num text-fg">{fmt.int(b.n)}</b></span></div>
                <div className="mt-1 h-1 rounded-full bg-line"><div className="h-full rounded-full" style={{ width: `${(Number(b.n) / maxN) * 100}%`, background: b.disposition === 'QUARANTINE' ? '#f43f5e' : '#fb923c' }} /></div>
              </button>
            ))}
          </div>
          <div className="mt-4 text-[11px] uppercase tracking-wider text-muted">{type ?? 'all'} · {fmt.int(dq.total)} rows · click an id → Why?</div>
          <div className="mt-1 max-h-72 space-y-1.5 overflow-y-auto pr-1">
            {dq.exceptions.map((e) => (
              <div key={e.exception_id} className="rounded-md border border-line p-2 text-xs">
                <div className="flex items-center gap-2"><span className="num text-muted">{e.exception_id}</span>
                  {e.source_id ? <IdChip id={e.source_id} /> : <span className="num">{e.record_key}</span>}
                  <span className="ml-auto num text-muted">{e.table_name}</span></div>
                <div className="mt-0.5 text-muted">{e.exception_type} · {e.detail}</div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Reproducibility & file integrity">
          <div className="mb-3 text-sm">
            {rep ? <>Generated twice with seed <b className="num">{rep.seed}</b> at scale <b className="num">{rep.scale}</b>: <b className={rep.runs_identical ? 'text-pos' : 'text-neg'}>{rep.runs_identical ? 'all files byte-identical' : 'files differ'}</b>
              {rep.matches_validated_data != null && <> · matches the validated data: <b className={rep.matches_validated_data ? 'text-pos' : 'text-neg'}>{String(rep.matches_validated_data)}</b></>} <span className="num text-muted">({rep.seconds} s)</span></>
              : 'Reproducibility check not run for this dataset (run the pipeline without --no-repro).'}
          </div>
          <table className="w-full text-xs">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted"><tr><th className="pb-1">Table</th><th className="pb-1 text-right">Manifest</th><th className="pb-1 text-right">File</th><th className="pb-1 text-right">SHA-256</th><th className="pb-1 text-right">Columns</th></tr></thead>
            <tbody>{s.file_integrity.map((f) => (
              <tr key={f.table} className="border-t border-line"><td className="num py-1">{f.table}</td><td className="num py-1 text-right">{fmt.int(f.rows_manifest)}</td>
                <td className="num py-1 text-right">{fmt.int(f.rows_file)}</td><td className={`py-1 text-right ${f.checksum_ok ? 'text-pos' : 'text-neg'}`}>{f.checksum_ok ? '✓' : '✗'}</td>
                <td className={`py-1 text-right ${f.columns_ok ? 'text-pos' : 'text-neg'}`}>{f.columns_ok ? '✓' : '✗'}</td></tr>
            ))}</tbody>
          </table>
        </Panel>
        <Panel title="Exports · manifest" right={<button onClick={() => setShowFiles((v) => !v)} className="text-xs text-support">{showFiles ? 'hide files' : `show ${dq.manifest.files.length} files`}</button>}>
          <div className="space-y-1 text-sm">
            <div>generator command: <code className="num rounded bg-ink px-1.5 py-0.5 text-xs">{dq.manifest.command}</code></div>
            <div className="text-muted">reference date <span className="num text-fg">{dq.manifest.reference_date}</span> · window <span className="num text-fg">{dq.manifest.window.join(' → ')}</span></div>
            <div className="text-muted">formats: CSV + JSON per table, <span className="num">sql/seed.sql</span> (DDL from the contract + INSERTs), separate <span className="num">ground_truth/</span>, <span className="num">manifest.json</span></div>
          </div>
          {showFiles && (
            <div className="mt-3 max-h-64 overflow-y-auto">
              {dq.manifest.files.map((f) => (
                <div key={f.path} className="num flex justify-between border-t border-line py-1 text-xs">
                  <span className={f.path.startsWith('ground_truth') ? 'text-mix' : ''}>{f.path}</span>
                  <span className="text-muted">{fmt.int(f.rows)} rows · {f.sha256.slice(0, 12)}…</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
