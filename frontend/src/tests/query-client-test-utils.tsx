/**
 * Test-only QueryClient + Router wrapper — ADR-003 S-15: "Tests shall
 * construct a fresh QueryClient per test with retry: false". Used for
 * isolated component tests of workspaces built on the Repository/TanStack
 * Query chain (Watchlist and later), as distinct from renderApp
 * (render-app.tsx), which deliberately renders the real composition with
 * real retry behavior and is for router/integration-level tests only.
 *
 * Includes MemoryRouter because workspace components built on the approved
 * chain contain real navigation <Link>s (e.g. to Ticker, Decision Center);
 * unlike Decision Center and Settings today, they cannot render without a
 * Router context.
 */
import type { ReactElement, ReactNode } from 'react'
import { render, type RenderResult } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
}

export function renderWithQueryClient(
  ui: ReactElement,
  options?: { initialEntries?: string[]; queryClient?: QueryClient },
): RenderResult {
  const queryClient = options?.queryClient ?? createTestQueryClient()

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={options?.initialEntries ?? ['/watchlist']}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

/** For `renderHook(fn, { wrapper: queryClientWrapper(client) })`. */
export function queryClientWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/watchlist']}>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }
}
