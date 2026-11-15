// A feedback record with its evidence highlighted - the classifier's reasoning made visible.
import type { ReactNode } from 'react'
import type { Item } from '../api/client'
import { fmt } from './tokens'
import { ChannelDot, IdChip, SentimentPill } from './ui'

const KIND: Record<string, { cls: string; label: string }> = {
  '+': { cls: 'ev-pos', label: 'positive cue' }, '-': { cls: 'ev-neg', label: 'negative cue' },
  '¬': { cls: 'ev-not', label: 'negated cue (polarity flipped)' }, '!': { cls: 'ev-sarc', label: 'sarcasm cue' },
  '~': { cls: 'ev-neu', label: 'neutral cue' }, '±': { cls: 'ev-mix', label: 'mixed cue' },
  '?': { cls: 'ev-neu', label: 'hedging cue' }, '#': { cls: 'ev-theme', label: 'theme cue' },
}
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** evidence = "+happy|-late|¬bad|!fantastic,|#late_delivery:delayed" -> highlight those spans in the text. */
export function EvidenceText({ text, evidence }: { text: string; evidence?: string | null }) {
  const cues = new Map<string, { cls: string; label: string }>()
  for (const tok of (evidence ?? '').split('|').filter(Boolean)) {
    const k = KIND[tok[0]]
    if (!k) continue
    const term = tok[0] === '#' ? tok.slice(tok.indexOf(':') + 1) : tok.slice(1)
    const key = term.toLowerCase().replace(/,$/, '')
    if (key && (!cues.has(key) || tok[0] !== '#')) cues.set(key, { ...k, label: tok[0] === '#' ? `theme cue: ${tok.slice(1, tok.indexOf(':'))}` : k.label })
  }
  const terms = [...cues.keys()].sort((a, b) => b.length - a.length)
  const parts = terms.length ? `(\\[EMAIL\\]|\\[PHONE\\]|\\[NAME\\]|${terms.map(esc).join('|')})` : '(\\[EMAIL\\]|\\[PHONE\\]|\\[NAME\\])'
  const out: ReactNode[] = []
  text.split(new RegExp(parts, 'gi')).forEach((seg, i) => {
    if (!seg) return
    if (/^\[(EMAIL|PHONE|NAME)\]$/.test(seg)) out.push(<span key={i} className="redacted" title="PII redacted before analysis">{seg}</span>)
    else if (i % 2 === 1 && cues.get(seg.toLowerCase())) {
      const c = cues.get(seg.toLowerCase())!
      out.push(<mark key={i} className={`${c.cls} bg-transparent text-inherit`} title={c.label}>{seg}</mark>)
    } else out.push(seg)
  })
  return <>{out}</>
}

export function RecordCard({ item, compact = false }: { item: Item; compact?: boolean }) {
  return (
    <article className="rounded-lg border border-line bg-panel2/60 p-3 transition hover:border-muted/40">
      <div className="mb-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
        <IdChip id={item.source_id} />
        <ChannelDot c={item.channel_type} label />
        <span>{item.product_name}</span>
        <span className="num">{fmt.date(item.event_at)}</span>
        {item.language !== 'en' && <span className="rounded border border-line px-1 num">{item.language}</span>}
        {item.role && <span className="rounded bg-line px-1.5">{item.role}</span>}
      </div>
      <p className={`leading-relaxed ${compact ? 'text-sm' : 'text-[15px]'}`}>
        <EvidenceText text={item.redacted_text} evidence={item.evidence} />
      </p>
      {item.sentiment && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
          <SentimentPill s={item.sentiment} conf={item.confidence} />
          {item.route === 'review' && <span className="rounded-full border border-support/40 px-2 py-0.5 text-support">needs review · {item.route_reason}</span>}
          <span className="num truncate" title="rules fired">{item.rules_fired}</span>
        </div>
      )}
    </article>
  )
}
