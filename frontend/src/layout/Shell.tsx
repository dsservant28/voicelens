// App frame: left rail, top bar (live logo, trace box, run chip, theme), page outlet, bottom status strip.
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEvaluation, useHealth, useMeta, useQuality } from '../api/client'
import { RoleSelect } from '../design/role'
import { SeismoLogo } from '../design/seismo'
import { CHANNELS, M_GATE, fmt } from '../design/tokens'
import { Flatline } from '../design/ui'
import { useWhy } from '../design/why-context'

const NAV = [
  { to: '/', label: 'Pulse', icon: '◉', hint: 'signals, alerts & epicenters' },
  { to: '/priorities', label: 'Priorities', icon: '▣', hint: 'themes & action items' },
  { to: '/review', label: 'Review', icon: '⊕', hint: 'sentiment plane & human review' },
  { to: '/flow', label: 'Data flow', icon: '≡', hint: 'validation & exceptions' },
  { to: '/proof', label: 'Proof', icon: '✓', hint: 'evaluation & metrics' },
]

function useTheme() {
  const [theme, setTheme] = useState<string>(() => {
    try { return localStorage.getItem('vl-theme') ?? 'dark' } catch { return 'dark' }
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('vl-theme', theme) } catch { /* private mode */ }
  }, [theme])
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))] as const
}

function TraceBox() {
  const why = useWhy()
  const ref = useRef<HTMLInputElement>(null)
  const [v, setV] = useState('')
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') { e.preventDefault(); ref.current?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  return (
    <form className="relative w-full max-w-md" onSubmit={(e) => { e.preventDefault(); if (v.trim()) why.open(v.trim()) }}>
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted">⌕</span>
      <input ref={ref} value={v} onChange={(e) => setV(e.target.value)} spellCheck={false}
        placeholder="Trace any ID…  REV-2026-000123 · ALR-000001 · ACT-000001"
        className="num w-full rounded-lg border border-line bg-panel py-2 pl-8 pr-10 text-sm placeholder:font-sans placeholder:text-muted/70 focus:border-support/60 focus:outline-none" />
      <kbd className="num absolute right-2 top-1/2 -translate-y-1/2 rounded border border-line px-1.5 text-[10px] text-muted">/</kbd>
    </form>
  )
}

function StatusStrip() {
  const nav = useNavigate()
  const q = useQuality().data?.summary
  const ev = useEvaluation().data
  const cell = 'flex shrink-0 items-center gap-1.5 px-3 hover:bg-panel2 cursor-pointer h-full'
  return (
    <footer className="flex h-9 items-stretch divide-x divide-line overflow-hidden whitespace-nowrap border-t border-line bg-panel text-xs text-muted">
      <div className={cell} onClick={() => nav('/flow')}>
        <span className={`h-2 w-2 rounded-full ${q?.status === 'FAIL' ? 'bg-neg' : 'bg-pos'}`} />
        Validation <b className="num text-fg">{q?.status === 'PASS_WITH_EXCEPTIONS' ? 'PASS*' : q?.status ?? '…'}</b>
        <span className="num">{fmt.int(q?.total_exceptions)} exc · {fmt.int(q?.quarantined_rows)} quarantined</span>
      </div>
      <div className={cell} onClick={() => nav('/proof')}>
        Eval accuracy <b className="num text-fg">{fmt.pct(ev?.splits.eval.sentiment_all.accuracy)}</b>
        <span className="num">· auto {fmt.pct(ev?.splits.eval.sentiment_auto.accuracy)} at {fmt.pct(ev?.splits.eval.coverage, 0)}</span>
      </div>
      <div className={cell} onClick={() => nav('/')}>
        Incidents <b className="num text-fg">{ev ? `${ev.incidents.detected}/${ev.incidents.incidents}` : '…'}</b>
        <span className="num">· {ev?.incidents.false_alarms ?? '…'} false alarms · TTD {fmt.num(ev?.incidents.mean_time_to_detect_days, 1)} d</span>
      </div>
      <div className="ml-auto hidden shrink-0 items-center gap-3 px-3 2xl:flex">
        {CHANNELS.map((c) => (
          <span key={c.key} className="flex items-center gap-1.5">
            <svg width="18" height="6"><line x1="0" y1="3" x2="18" y2="3" stroke={c.color} strokeWidth="2" strokeDasharray={c.dash} /></svg>
            {c.label} <span className="num opacity-70">{c.lag}</span>
          </span>
        ))}
        <span className="num" title="alert gate: M = −log₁₀ p ≥ 5">M ≥ {M_GATE}</span>
      </div>
    </footer>
  )
}

function NoData({ hint, down }: { hint?: string | null; down: boolean }) {
  return (
    <div className="paper grid h-full place-items-center p-8">
      <div className="max-w-xl rounded-2xl border border-line bg-panel p-8">
        <div className="mb-3 text-xs font-bold tracking-[0.25em] text-support">{down ? 'BACKEND NOT REACHABLE' : 'NO DATA YET'}</div>
        <p className="mb-4 text-sm text-muted">
          {down ? 'Start the API in a terminal (from the backend folder):' : 'Run the pipeline once (from the backend folder), then reload:'}
        </p>
        <pre className="num overflow-x-auto rounded-lg bg-ink p-4 text-sm">{down ? 'uvicorn voicelens.api.main:app --reload' : (hint?.split(':  ')[1] ?? 'python -m voicelens.pipeline --scale 1.0')}</pre>
      </div>
    </div>
  )
}

export function Shell() {
  const [theme, toggle] = useTheme()
  const health = useHealth()
  const meta = useMeta()
  const ready = health.data?.data_loaded
  return (
    <div className="grid h-full grid-cols-[208px_1fr] grid-rows-[56px_1fr_auto]">
      <aside className="row-span-3 flex flex-col border-r border-line bg-panel">
        <div className="flex h-14 items-center gap-2 border-b border-line px-4">
          <span className="text-lg font-bold tracking-tight">Voice<span className="text-support">Lens</span></span>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/'}
              className={({ isActive }) => `group rounded-lg px-3 py-2.5 transition ${isActive ? 'bg-panel2 text-fg shadow-[inset_2px_0_0_#fbbf24]' : 'text-muted hover:bg-panel2/60 hover:text-fg'}`}>
              <div className="flex items-center gap-3 text-sm font-medium"><span className="w-4 text-center">{n.icon}</span>{n.label}</div>
              <div className="ml-7 text-[11px] text-muted/80">{n.hint}</div>
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-line p-4 text-[11px] leading-5 text-muted">
          <div>Every number is traceable.</div>
          <div>Click any <span className="num underline decoration-dotted">ID</span> or press <kbd className="num rounded border border-line px-1">/</kbd></div>
        </div>
      </aside>

      <header className="flex items-center gap-5 border-b border-line bg-panel/80 px-5 backdrop-blur">
        <div className="flex items-center gap-2" title="live: daily negative feedback across all channels">
          <SeismoLogo />
        </div>
        <TraceBox />
        <div className="ml-auto flex items-center gap-3 text-xs text-muted">
          <RoleSelect />
          {meta.data?.run && (
            <span className="num rounded-full border border-line px-3 py-1" title={`rules hash ${meta.data.run.lexicon_hash}`}>
              {meta.data.run.run_id} · {fmt.int(meta.data.run.n_items)} items
            </span>
          )}
          <button onClick={toggle} className="rounded-full border border-line px-3 py-1 hover:text-fg" title="toggle light/dark">
            {theme === 'dark' ? '◐ dark' : '◑ light'}
          </button>
        </div>
      </header>

      <main className="overflow-y-auto">
        {health.isLoading ? <Flatline label="connecting to VoiceLens API…" />
          : !ready ? <NoData hint={health.data?.hint} down={!!health.error} /> : <Outlet />}
      </main>
      {ready ? <StatusStrip /> : <div />}
    </div>
  )
}
