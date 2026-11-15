// Typed API client + react-query hooks. All calls go through the Vite proxy (/api -> FastAPI :8000).
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })
const get = <T,>(url: string) => api.get<T>(url).then((r) => r.data)

export type Channel = 'support' | 'review' | 'survey'
export type Sentiment = 'positive' | 'negative' | 'neutral' | 'mixed'
export type SourceType = 'review' | 'survey_response' | 'support_message'

export interface Health { status: string; database: string; data_loaded: boolean; items?: number; hint: string | null }
export interface PulseRow { day: string; channel_type: Channel; n: number; negatives: number }

export interface Item {
  source_type: SourceType; source_id: string; product_id: string; product_name: string; channel_type: Channel
  event_at: string; language: string; redacted_text: string; sentiment?: Sentiment; confidence?: number
  theme_ids?: string | null; route?: 'auto' | 'review'; route_reason?: string | null; rules_fired?: string
  evidence?: string | null; role?: string
}

export interface ChainLevel { level: string; id?: string; [k: string]: unknown }
export interface TraceResult {
  kind: 'action' | 'alert' | 'cell' | 'record'; id: string
  chain?: ChainLevel[]; items?: Item[]
  quarantined?: boolean; item?: Item | null
  exceptions?: { exception_id: string; exception_type: string; disposition: string; detail: string; detected_by: string }[]
  cells?: { cell_id: string; week_start: string; theme_id: string; n_items: number; neg_share: number }[]
  alerts?: { alert_id: string; kind: string; magnitude: number; detected_date: string; role: string }[]
  actions?: { action_item_id: string; priority_score: number; status: string }[]
}

export interface Meta {
  products: { product_id: string; name: string; category: string }[]
  themes: { theme_id: string; code: string; name: string; parent_theme_id: string | null; severity_weight: number }[]
  channels: { channel_id: string; name: string; channel_type: Channel }[]
  run: { run_id: string; lexicon_hash: string; n_items: number; n_auto: number; n_review: number; finished_at: string } | null
  action_transitions: [string, string][]
}

export interface Evaluation {
  run_id: string
  splits: { eval: { sentiment_all: { accuracy: number }; coverage: number; sentiment_auto: { accuracy: number } } }
  incidents: { incidents: number; detected: number; false_alarms: number; mean_time_to_detect_days: number | null }
  edge_cases: { issue_type: string; planted: number; detected: number }[]
}
export interface Quality { summary: { status: string; total_exceptions: number; quarantined_rows: number; total_rows: number } }

const MIN = 60_000
export const useHealth = () => useQuery({ queryKey: ['health'], queryFn: () => get<Health>('/health'), retry: false })
export const useMeta = () => useQuery({ queryKey: ['meta'], queryFn: () => get<Meta>('/meta'), staleTime: 5 * MIN })
export const usePulse = () => useQuery({ queryKey: ['pulse'], queryFn: () => get<PulseRow[]>('/pulse'), staleTime: 5 * MIN })
export const useEvaluation = () => useQuery({ queryKey: ['evaluation'], queryFn: () => get<Evaluation>('/evaluation'), staleTime: 5 * MIN })
export const useQuality = () => useQuery({ queryKey: ['quality'], queryFn: () => get<Quality>('/data-quality?limit=1'), staleTime: 5 * MIN })
export const useTrace = (id: string | null) =>
  useQuery({ queryKey: ['trace', id], queryFn: () => get<TraceResult>(`/trace/${encodeURIComponent(id!)}`), enabled: !!id, retry: false })

// ---------------------------------------------------------------- Pulse
export interface Alert {
  alert_id: string; product_id: string; product_name: string; theme_id: string; theme_name: string; theme_code: string
  direction: 'worsen' | 'improve'; kind: 'worsen' | 'improve' | 'recovery'; status: 'ACTIVE' | 'ENDED'
  start_date: string; detected_date: string; peak_date: string; end_date: string
  magnitude: number; peak_z: number; baseline_share: number; window_share: number; shift: number; window_items: number
  lead_channel: Channel | null; first_support_date: string | null; first_review_date: string | null; first_survey_date: string | null
  evidence_count: number; action_item_id: string | null
}
export interface AlertDetail { alert: Alert; daily_series: { day: string; channel_type: Channel; n: number; negatives: number }[]; evidence: Item[] }
export interface Overview {
  kpis: { items: number; auto_coverage: number; neg_share_last_28d: number; neg_share_prev_28d: number; data_until: string
    active_alerts: number; alerts: number; open_actions: number; review_pending: number; exceptions: number }
  top_alerts: Alert[]
}
export const useOverview = () => useQuery({ queryKey: ['overview'], queryFn: () => get<Overview>('/overview') })
export const useAlerts = () => useQuery({ queryKey: ['alerts'], queryFn: () => get<Alert[]>('/alerts') })
export const useAlert = (id: string | null) =>
  useQuery({ queryKey: ['alert', id], queryFn: () => get<AlertDetail>(`/alerts/${id}`), enabled: !!id })

// ---------------------------------------------------------------- Priorities
export interface ThemeRank {
  rank: number; product_id: string; product_name: string; theme_id: string; theme_name: string; theme_code: string
  recent_n: number; neg_share: number; prev_neg_share: number; shift: number; severity_weight: number; priority: number
  active_alerts: string | null; open_actions: string | null
}
export interface WeeklyCell { cell_id: string; week_start: string; channel_type: Channel; n_items: number; n_negative: number; neg_share: number }
export interface ThemeDetail { product_name: string; theme_name: string; weekly_cells: WeeklyCell[]; alerts: { alert_id: string; kind: string; detected_date: string; peak_z: number }[] }
export type ActionStatus = 'OPEN' | 'IN_PROGRESS' | 'DONE' | 'DISMISSED'
export interface ActionItem {
  action_item_id: string; product_id: string; product_name: string; theme_id: string; theme_name: string
  priority_score: number; priority_inputs: string; status: ActionStatus; owner_role: string; evidence_count: number
  recommendation: string; kind: 'alert' | 'chronic'; alert_id: string | null; magnitude: number | null
  created_at: string; updated_at: string; created_from_rule: string
}
export interface ActionEvent { event_id: string; from_status: string | null; to_status: string; actor: string; note: string | null; event_at: string }
export interface ActionDetail { action_item: ActionItem; events: ActionEvent[]; allowed_next: ActionStatus[] }
export const useThemes = () => useQuery({ queryKey: ['themes'], queryFn: () => get<ThemeRank[]>('/themes?limit=200') })
export const useThemeDetail = (p: string | null, t: string | null) =>
  useQuery({ queryKey: ['theme', p, t], queryFn: () => get<ThemeDetail>(`/themes/${p}/${t}`), enabled: !!p && !!t })
export const useActions = () => useQuery({ queryKey: ['actions'], queryFn: () => get<ActionItem[]>('/action-items') })
export const useAction = (id: string | null) =>
  useQuery({ queryKey: ['action', id], queryFn: () => get<ActionDetail>(`/action-items/${id}`), enabled: !!id })
export const setActionStatus = (id: string, to_status: ActionStatus, actor: string, note?: string) =>
  api.post<ActionDetail>(`/action-items/${id}/status`, { to_status, actor, note }).then((r) => r.data)
