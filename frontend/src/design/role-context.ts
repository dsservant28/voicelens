// Who is acting: the problem statement's actors. Recorded on every review and action event.
import { createContext, useContext } from 'react'

export const ROLES = [
  { key: 'analyst', label: 'Analyst' },
  { key: 'support_agent', label: 'Support agent' },
  { key: 'support_lead', label: 'Support lead' },
  { key: 'marketing_ops', label: 'Marketing / sales ops' },
  { key: 'billing_ops', label: 'Billing ops' },
  { key: 'logistics_ops', label: 'Logistics ops' },
  { key: 'product_manager', label: 'Product manager' },
  { key: 'admin', label: 'System admin' },
] as const

export const RoleCtx = createContext<{ role: string; setRole: (r: string) => void }>({ role: 'analyst', setRole: () => {} })
export const useRole = () => useContext(RoleCtx)
