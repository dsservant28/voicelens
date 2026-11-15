import { createContext, useContext } from 'react'

export const WhyCtx = createContext<{ open: (id: string) => void; close: () => void }>({ open: () => {}, close: () => {} })
export const useWhy = () => useContext(WhyCtx)
