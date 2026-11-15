import { useEffect, useRef, useState } from 'react'

/** Width of a container, kept in sync with resizes (for responsive SVG). */
export function useWidth<T extends HTMLElement>(initial = 800) {
  const ref = useRef<T>(null)
  const [w, setW] = useState(initial)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(([e]) => setW(Math.max(320, Math.floor(e.contentRect.width))))
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w] as const
}

export const DAY = 86_400_000
export const toDate = (s: string) => new Date(`${s.slice(0, 10)}T00:00:00`)
export const daysBetween = (a: string, b: string) => Math.round((toDate(b).getTime() - toDate(a).getTime()) / DAY)
