// Temporary page body used while each page is designed; doubles as a live check of the design system.
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { fmt } from '../design/tokens'
import { IdChip, Kpi, MagnitudeBadge, Panel } from '../design/ui'

interface TopAlert { alert_id: string; kind: string; product_name: string; theme_name: string; magnitude: number; detected_date: string; action_item_id: string | null }
interface Overview { kpis: Record<string, number>; top_alerts: TopAlert[] }

export function Placeholder({ title, tagline }: { title: string; tagline: string }) {
  const { data } = useQuery({ queryKey: ['overview'], queryFn: () => api.get<Overview>('/overview').then((r) => r.data) })
  const k = data?.kpis
  return (
    <div className="paper min-h-full p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-muted">{tagline} <span className="ml-2 rounded-full border border-line px-2 py-0.5 text-[11px]">page design next</span></p>
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Feedback items" value={fmt.int(k?.items)} sub="reviews · surveys · support" />
        <Kpi label="Auto-labelled" value={fmt.pct(k?.auto_coverage)} sub="rest routed to humans" />
        <Kpi label="Alerts" value={fmt.int(k?.alerts)} sub={`${fmt.int(k?.active_alerts)} active`} accent="#fbbf24" />
        <Kpi label="Open actions" value={fmt.int(k?.open_actions)} sub={`${fmt.int(k?.review_pending)} items awaiting review`} />
      </div>
      <Panel title="Design-system check · strongest alerts (click any ID → Why?)">
        <div className="divide-y divide-line">
          {data?.top_alerts.map((a) => (
            <div key={a.alert_id} className="flex items-center gap-4 py-3">
              <MagnitudeBadge m={Number(a.magnitude)} />
              <IdChip id={a.alert_id} />
              <span className="text-sm">{a.product_name} · {a.theme_name}</span>
              <span className="text-xs text-muted">{a.kind} · detected {fmt.date(a.detected_date)}</span>
              {a.action_item_id && <span className="ml-auto"><IdChip id={a.action_item_id} /></span>}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  )
}
