// Design tokens shared by every page: channel identity, sentiment colours, magnitude scale.
import { interpolateRgb } from 'd3'
import type { Channel, Sentiment } from '../api/client'

export const CHANNELS: { key: Channel; label: string; color: string; dash: string; lag: string }[] = [
  { key: 'support', label: 'Support', color: '#fbbf24', dash: '', lag: 'day 0' },
  { key: 'review', label: 'Reviews', color: '#38bdf8', dash: '6 4', lag: '+3 days' },
  { key: 'survey', label: 'Surveys', color: '#c084fc', dash: '2 4', lag: '+7 days' },
]
export const CHANNEL = Object.fromEntries(CHANNELS.map((c) => [c.key, c])) as Record<Channel, (typeof CHANNELS)[number]>

export const SENTIMENT: Record<Sentiment, { color: string; label: string }> = {
  positive: { color: '#34d399', label: 'Positive' },
  negative: { color: '#f43f5e', label: 'Negative' },
  neutral: { color: '#94a3b8', label: 'Neutral' },
  mixed: { color: '#f472b6', label: 'Mixed' },
}

/** Magnitude M = -log10(p). The detection gate is M >= 5 (p <= 1e-5). One ring per doubling: 5, 10, 20, 40, 80 ... */
export const M_GATE = 5
export const magRings = (m: number) => Math.max(1, Math.min(6, Math.floor(Math.log2(Math.max(m, M_GATE) / M_GATE)) + 1))
const ramp = interpolateRgb('#fbbf24', '#f43f5e')
export const magColor = (m: number) => ramp(Math.min(1, Math.max(0, Math.log2(Math.max(m, M_GATE) / M_GATE) / 4)))

export const fmt = {
  int: (n: number | null | undefined) => (n == null ? '–' : Math.round(Number(n)).toLocaleString('en-US')),
  pct: (n: number | null | undefined, d = 1) => (n == null ? '–' : `${(Number(n) * 100).toFixed(d)}%`),
  num: (n: number | null | undefined, d = 2) => (n == null ? '–' : Number(n).toFixed(d)),
  date: (s: string | null | undefined) =>
    s ? new Date(s).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '–',
}
