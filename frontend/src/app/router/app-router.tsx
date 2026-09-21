/**
 * Route table — Phase 9 Workstream B (B2, B7).
 *
 * Implements Phase 4 Appendix B's canonical routes. Every workspace owns
 * exactly one canonical root (P4-06 §4); no route has two owners (P4-06 §17);
 * no nested workspaces (P4-06 §3).
 *
 * NO LOADERS. React Router's data APIs would fetch outside the frozen chain in
 * Phase 7 v1.1 §8 (Component → ViewModel → Domain Adapter → Repository →
 * Server State → API Client). Data access arrives in Workstream E through the
 * Repository seam, and ADR-003 puts caching in TanStack Query — not in the
 * router. The router resolves URLs; it does not fetch.
 *
 * Route elements are the generic WorkspaceShellPage. Workstream D replaces each
 * one with the real workspace built inside its own domain directory.
 */
import { Navigate, Route, Routes } from 'react-router'
import { useParams } from 'react-router'
import { AppShell } from '../shell/app-shell'
import { WorkspaceShellPage } from '../shell/workspace-shell-page'
import { UrlNormalizationGuard } from './url-normalization-guard'
import { NotFoundPage } from './not-found-page'
import { getWorkspace, ROUTE_PATHS, type WorkspaceId } from './workspaces'
import { DecisionPage } from '@domains/decision/decision-page'
import { SettingsPage } from '@domains/settings/settings-page'
import { WatchlistPage } from '@domains/watchlist/watchlist-page'
import { MarketPage } from '@domains/market/market-page'
import { SearchPage } from '@domains/search/search-page'
import { TickerDetailPage } from '@domains/ticker/ticker-detail-page'
import { IntelligencePage } from '@domains/intelligence/intelligence-page'

function WorkspaceRoute({ id }: { id: WorkspaceId }) {
  return <WorkspaceShellPage workspace={getWorkspace(id)} />
}

/**
 * Ticker is the one workspace whose canonical route carries a resource
 * identifier. The symbol is read from the URL — Resource State is owned by the
 * Router (ADR-001 §3), never mirrored into component state.
 *
 * D4 slice 1 (2026-09-02): /ticker/:symbol now renders the real Ticker
 * Detail workspace (domains/ticker) over GET /api/v1/tickers/:symbol; the
 * symbol still lives only in the URL and is uppercased by the page. The
 * /ticker index below stays on the placeholder shell.
 */
function TickerRoute() {
  const { symbol = '' } = useParams<{ symbol: string }>()

  return <TickerDetailPage key={symbol.toUpperCase()} />
}

export function AppRoutes() {
  return (
    <>
      <UrlNormalizationGuard />

      <Routes>
        <Route element={<AppShell />}>
          {/*
            Phase 4 Appendix B registers `/` as Home, but P4-02 §3 defines no
            Home workspace and Appendix A gives it no screens. UI-001 makes
            Decision Center the primary operational workspace, so `/` resolves
            there. REPLACE, so Back never lands on an empty root.
          */}
          <Route path={ROUTE_PATHS.home} element={<Navigate to={ROUTE_PATHS.decision} replace />} />

          {/*
            Decision Center — the first Workstream D workspace built (see
            domains/decision/decision-page.tsx docstring). Settings, Watchlist,
            Market, Search and the Ticker detail route are also real (see
            their own docstrings); Portfolio and the /ticker index remain
            the generic placeholder shell.
          */}
          <Route path={ROUTE_PATHS.decision} element={<DecisionPage />} />
          {/*
            Investment Intelligence — consolidation 2026-09-03: composes the
            canonical investment portfolio (absorbed from the external
            Investment Dashboard, ex-port 5003) with the watchlist / market /
            registry read models inside the OS. See
            domains/intelligence/intelligence-page.tsx and
            docs/INTEGRATION_CONSOLIDATION_MAP_2026-09-03.md.
          */}
          <Route path={ROUTE_PATHS.intelligence} element={<IntelligencePage />} />
          {/*
            ADR-006 §5 (docs/OneDrive_2026-08-07/Frontend arch/
            ADR-006_LEGACY_UI_DISPOSITION.md), interim fix, applied 2026-08-20:
            no <Route> for ROUTE_PATHS.portfolio here. Flask's own
            `@app.route("/portfolio")` (app.py) already serves a real, working
            legacy page at this URL; this SPA's Portfolio workspace is still
            an empty WorkspaceShellPage placeholder (Workstream D, blocked on
            U-2/U-3/U-4). Registering the shell here made "/portfolio" race
            two different applications depending on how the user arrived
            (full page load -> Flask; client-side nav -> the empty SPA
            shell) -- ADR-006 §5 calls this a live defect independent of
            which of its three disposition options is eventually chosen.
            Dropping the <Route> lets an unmatched client-side "/portfolio"
            fall through to the `*` catch-all (NotFoundPage) instead of
            rendering the misleading empty shell. The route is added back,
            deliberately, when the real Portfolio workspace (D5) is built --
            see ADR-006 §7 Q-3 for what "feature-complete" will mean then.
            workspaces.ts's WORKSPACES entry for 'portfolio' is unchanged:
            the seven-workspace list itself is not being altered here, only
            this one route's SPA registration.
          */}
          {/*
            Watchlist — Production OS Slice 2, first workspace built directly
            on the approved ADR-003 architecture. See
            domains/watchlist/watchlist-page.tsx docstring.
          */}
          <Route path={ROUTE_PATHS.watchlist} element={<WatchlistPage />} />
          {/*
            Market — Production OS Slice 4, built directly on the approved
            ADR-003 architecture. See domains/market/market-page.tsx docstring.
          */}
          <Route path={ROUTE_PATHS.market} element={<MarketPage />} />
          {/*
            Search — Production OS Slice 5, built directly on the approved
            ADR-003 architecture. See domains/search/search-page.tsx docstring.
          */}
          <Route path={ROUTE_PATHS.search} element={<SearchPage />} />
          {/*
            Settings — ADR-008 (docs/OneDrive_2026-08-07/Frontend arch/
            ADR-008_OPERATIONS_DASHBOARD_SETTINGS_PLACEMENT.md): scheduler/
            job-history/system-status information (formerly the standalone,
            unreachable /internal/operations route) is owned here, under
            Settings' own already-frozen "System Information" / "Support &
            Diagnostics" regions — not a new eighth workspace. See
            domains/settings/settings-page.tsx docstring for the full
            rationale.
          */}
          <Route path={ROUTE_PATHS.settings} element={<SettingsPage />} />

          {/*
            `/ticker` carries no symbol. It exists because NP-03 requires every
            workspace to be directly reachable from Global Navigation, and the
            sidebar cannot link to a parameterised route. It renders the Ticker
            workspace with no instrument selected — a legitimate empty state
            under P4-14 §10, not a dead end.

            Flagged for owner ruling: Phase 4 Appendix B registers only
            /ticker/:symbol. This is the same gap family as ADR-002.
          */}
          <Route path={ROUTE_PATHS.ticker} element={<WorkspaceRoute id="ticker" />} />
          <Route path={ROUTE_PATHS.tickerSymbol} element={<TickerRoute />} />

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </>
  )
}
