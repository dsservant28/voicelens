import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { RoleProvider } from './design/role'
import { WhyProvider } from './design/why'
import './index.css'
import { Shell } from './layout/Shell'
import { Flow } from './pages/Flow'
import { Priorities } from './pages/Priorities'
import { Proof } from './pages/Proof'
import { Pulse } from './pages/Pulse'
import { Review } from './pages/Review'

const qc = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } })
try { document.documentElement.dataset.theme = localStorage.getItem('vl-theme') ?? 'dark' } catch { /* private mode */ }

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <RoleProvider>
        <WhyProvider>
          <Routes>
            <Route element={<Shell />}>
              <Route index element={<Pulse />} />
              <Route path="priorities" element={<Priorities />} />
              <Route path="review" element={<Review />} />
              <Route path="flow" element={<Flow />} />
              <Route path="proof" element={<Proof />} />
            </Route>
          </Routes>
        </WhyProvider>
        </RoleProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
