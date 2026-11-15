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
