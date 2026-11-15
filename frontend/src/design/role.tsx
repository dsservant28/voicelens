// Role provider + selector (context lives in role-context.ts).
import { useState, type ReactNode } from 'react'
import { ROLES, RoleCtx, useRole } from './role-context'

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, set] = useState(() => { try { return localStorage.getItem('vl-role') ?? 'analyst' } catch { return 'analyst' } })
  const setRole = (r: string) => { set(r); try { localStorage.setItem('vl-role', r) } catch { /* private mode */ } }
  return <RoleCtx.Provider value={{ role, setRole }}>{children}</RoleCtx.Provider>
}

export function RoleSelect() {
  const { role, setRole } = useRole()
  return (
    <label className="flex items-center gap-2 text-xs text-muted" title="recorded as the actor on every review and action event">
      acting as
      <select value={role} onChange={(e) => setRole(e.target.value)}
        className="rounded-full border border-line bg-panel px-3 py-1 text-fg focus:border-support/60 focus:outline-none">
        {ROLES.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
      </select>
    </label>
  )
}
