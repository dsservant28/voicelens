// The logo is the data: a live seismograph of daily negative feedback (all channels).
import { curveMonotoneX, line, scaleLinear } from 'd3'
import { motion } from 'motion/react'
import { useMemo } from 'react'
import { usePulse } from '../api/client'

export function SeismoLogo({ width = 132, height = 26 }: { width?: number; height?: number }) {
  const { data } = usePulse()
  const d = useMemo(() => {
    if (!data?.length) return null
    const byDay = new Map<string, number>()
    for (const r of data) byDay.set(r.day, (byDay.get(r.day) ?? 0) + Number(r.negatives))
    const ys = [...byDay.values()]
    const x = scaleLinear().domain([0, ys.length - 1]).range([1, width - 1])
    const y = scaleLinear().domain([Math.min(...ys), Math.max(...ys)]).range([height - 2, 2])
    return line<number>().x((_, i) => x(i)).y((v) => y(v)).curve(curveMonotoneX)(ys)
  }, [data, width, height])
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-label="daily negative feedback, all channels">
      <line x1={0} x2={width} y1={height - 2} y2={height - 2} stroke="var(--line)" />
      {d ? (
        <motion.path d={d} fill="none" stroke="#fbbf24" strokeWidth={1.4} strokeLinejoin="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.8, ease: 'easeInOut' }} />
      ) : (
        <line x1={0} x2={width} y1={height / 2} y2={height / 2} stroke="#fbbf24" strokeOpacity={0.4} />
      )}
    </svg>
  )
}
