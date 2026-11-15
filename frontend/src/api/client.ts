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

// ---------------------------------------------------------------- Pulse drill-down
export interface ItemPage { total: number; items: Item[] }
export const useTrendItems = (q: { date_from: string; date_to: string; channel_type: Channel; sentiment?: Sentiment } | null) =>
  useQuery({
    queryKey: ['trend-items', q],
    queryFn: () => get<ItemPage>(`/trend/items?${new URLSearchParams({ ...q!, limit: '200' } as Record<string, string>)}`),
    enabled: !!q,
  })

// ---------------------------------------------------------------- Review
export interface PlaneCell { pos: number; neg: number; sentiment: Sentiment; n: number; sarcasm: number; hedged: number }
export interface Queue extends ItemPage { set: 'uncertain' | 'eval'; blind: boolean; reasons: { reason: string; n: number }[] }
export interface ReviewEvent { event_id: string; old_sentiment: Sentiment; new_sentiment: Sentiment; decision: 'confirmed' | 'overridden'; reviewer: string }
export const usePlane = () => useQuery({ queryKey: ['plane'], queryFn: () => get<PlaneCell[]>('/review/plane') })
export const useQueue = (p: { set: 'uncertain' | 'eval'; status: string; reason?: string | null; pos?: number | null; neg?: number | null; limit?: number }) =>
  useQuery({
    queryKey: ['queue', p],
    queryFn: () => {
      const qs = new URLSearchParams({ set: p.set, status: p.status, limit: String(p.limit ?? 30) })
      if (p.reason) qs.set('reason', p.reason)
      if (p.pos != null) qs.set('pos', String(p.pos))
      if (p.neg != null) qs.set('neg', String(p.neg))
      return get<Queue>(`/review-queue?${qs}`)
    },
  })
export const submitReview = (st: string, id: string, sentiment: Sentiment, reviewer: string, theme_ids: string[] = []) =>
  api.post<ReviewEvent>(`/review/${st}/${id}`, { sentiment, reviewer, theme_ids }).then((r) => r.data)
export const runEvaluation = () => api.post<{ human_reviewed: number; eval_accuracy: number }>('/evaluation/run').then((r) => r.data)

// ---------------------------------------------------------------- Data flow
export interface FlowData {
  nodes: { name: string; stage: number }[]; links: { source: string; target: string; value: number }[]; tables: Record<string, number>
  reconciliation: { rows_in: number; rows_out: number; balanced: boolean; analysed: number; feedback_items: number
    analysed_matches_items: boolean; routed: number; routed_matches_items: boolean }
}
export interface Check { check: string; category: string; disposition: string; description: string; exceptions: number }
export interface ExceptionRow { exception_id: string; table_name: string; record_key: string; source_type: string | null; source_id: string | null
  exception_type: string; check_name: string; check_category: string; disposition: string; detail: string; detected_by: string }
export interface DataQuality {
  summary: { status: string; total_rows: number; total_exceptions: number; quarantined_rows: number; seed: number; scale: number; validated_at: string
    checks: Check[]; tables: { table: string; rows: number; rows_with_exceptions: number; quarantined_rows: number; clean_rows: number }[]
    file_integrity: { table: string; rows_manifest: number; rows_file: number; checksum_ok: boolean; columns_ok: boolean; ok: boolean }[]
    reproducibility: { seed: number; scale: number; files_compared: number; runs_identical: boolean; matches_validated_data?: boolean; seconds: number; passed: boolean } | null }
  manifest: { seed: number; scale: number; command: string; reference_date: string; window: string[]; files: { path: string; rows: number; sha256: string }[] }
  by_type: { exception_type: string; check_category: string; disposition: string; detected_by: string; n: number }[]
  total: number; exceptions: ExceptionRow[]
}
export const useFlow = () => useQuery({ queryKey: ['flow'], queryFn: () => get<FlowData>('/flow') })
export const useDataQuality = (type: string | null) =>
  useQuery({ queryKey: ['dq', type], queryFn: () => get<DataQuality>(`/data-quality?limit=60${type ? `&exception_type=${type}` : ''}`) })

// ---------------------------------------------------------------- Proof
export interface Cls { n: number; accuracy: number | null; macro_f1: number; per_class: Record<Sentiment, { precision: number; recall: number; f1: number; support: number }>
  confusion: { labels: Sentiment[]; matrix: number[][] } }
export interface Slice { n: number; accuracy: number; theme_exact: number; coverage: number; auto_accuracy: number | null; [k: string]: unknown }
export interface CurvePoint { tau: number; coverage: number; auto_accuracy: number | null }
export interface SplitMetrics { gold_items: number; evaluated_items: number; excluded_items: number; sentiment_all: Cls; sentiment_auto: Cls; coverage: number
  themes: { exact_match: number; micro_precision: number; micro_recall: number; micro_f1: number }
  by_style: Slice[]; by_language: Slice[]; by_source: Slice[]; coverage_curve: CurvePoint[] }
export interface IncidentRow { incident_id: string; product_id: string; theme_id: string; direction: string; onset_date: string; detected: boolean
  alert_id?: string; detected_date?: string; time_to_detect_days?: number; lead_channel?: Channel; lead_channel_correct?: boolean
  support_lag_measured?: number | null; review_lag_measured?: number | null; survey_lag_measured?: number | null
  support_lag_designed?: number; review_lag_designed?: number; survey_lag_designed?: number; evidence_precision?: number | null }
export interface FullEvaluation {
  run_id: string; rules_hash: string; evaluated_at: string; params: { tau: number }
  splits: { train: SplitMetrics; eval: SplitMetrics }
  tau: { rule: string; current: number; recommended: number; train: CurvePoint; eval: CurvePoint }
  edge_cases: { issue_type: string; planted: number; detected: number; recall: number; precision: number; flagged_total: number
    expected_decision: string; check: string; decision_correct: number }[]
  incidents: { incidents: number; detected: number; detection_rate: number; false_alarms: number; recoveries: number
    mean_time_to_detect_days: number | null; lead_channel_correct: number; per_incident: IncidentRow[] }
  human_review: { events: number; sample_size: number; reviewed: number; model_vs_human?: Cls; model_vs_human_themes?: { exact_match: number }
    human_vs_gold?: number; overridden?: number }
}
export const useFullEvaluation = () => useQuery({ queryKey: ['evaluation-full'], queryFn: () => get<FullEvaluation>('/evaluation') })
