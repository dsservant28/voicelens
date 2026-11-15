import { useCallback, useRef, useState } from 'react'

/** Width of a container, kept in sync with resizes (for responsive SVG). A callback ref, so it re-measures when the
 *  element changes (e.g. a loading placeholder is replaced by the chart). */
export function useWidth<T extends HTMLElement>(initial = 800) {
  const [w, setW] = useState(initial)
  const ro = useRef<ResizeObserver | null>(null)
  const ref = useCallback((el: T | null) => {
    ro.current?.disconnect()
    ro.current = null
    if (!el) return
    const set = (px: number) => setW(Math.max(320, Math.floor(px)))
    set(el.getBoundingClientRect().width)
    ro.current = new ResizeObserver(([e]) => set(e.contentRect.width))
    ro.current.observe(el)
  }, [])
  return [ref, w] as const
}

export const DAY = 86_400_000
export const toDate = (s: string) => new Date(`${s.slice(0, 10)}T00:00:00`)
export const daysBetween = (a: string, b: string) => Math.round((toDate(b).getTime() - toDate(a).getTime()) / DAY)
