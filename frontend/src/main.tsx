import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { WhyProvider } from './design/why'
import './index.css'
import { Shell } from './layout/Shell'
import { Placeholder } from './pages/Placeholder'
import { Priorities } from './pages/Priorities'
import { Pulse } from './pages/Pulse'

const qc = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } })
try { document.documentElement.dataset.theme = localStorage.getItem('vl-theme') ?? 'dark' } catch { /* private mode */ }

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <WhyProvider>
          <Routes>
            <Route element={<Shell />}>
              <Route index element={<Pulse />} />
              <Route path="priorities" element={<Priorities />} />
              <Route path="review" element={<Placeholder title="Review" tagline="The sentiment plane and the human-review queue." />} />
              <Route path="flow" element={<Placeholder title="Data flow" tagline="Every row accounted for: validation, quarantine, exceptions." />} />
              <Route path="proof" element={<Placeholder title="Proof" tagline="Evaluation: accuracy, abstention trade-off, time-to-detect." />} />
            </Route>
          </Routes>
        </WhyProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
