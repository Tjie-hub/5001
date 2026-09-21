/**
 * Architecture boundary guards — Phase 9 Workstream A (task A4).
 *
 * These rules are the machine-checkable subset of the frozen architecture.
 * They exist so that an import which violates ADR-001 or ADR-003 fails CI
 * rather than surviving review.
 *
 * Authority:
 *   ADR-001 §4        domain dependency edge list
 *   ADR-003 N-3, S-2  Server State confined to the Repository seam
 *   Phase 7 v1.1 §8   Component → ViewModel → Adapter → Repository → Server
 *                     State → API Client → Backend
 *   Phase 7 v1.1 §9   backend DTOs never reach components
 *
 * Proven by src/tests/architecture-boundaries.test.ts, which lints deliberate
 * violations through this configuration and asserts they are reported. Weaken a
 * rule here and that suite fails.
 *
 * WHY the rule and not just a review checklist: Phase 9 AC-5 requires
 * architecture compliance to be *verified*, and the failure mode these guard
 * against — the cache becoming a general state manager, workspaces reaching
 * into each other — is invisible in a small diff and expensive to unwind later.
 */

const RULE = '@typescript-eslint/no-restricted-imports'

/**
 * The frozen workspaces (Phase 4 P4-02 §3, Phase 7 v1.1 §4) plus
 * 'intelligence' (consolidation 2026-09-03 — see
 * docs/INTEGRATION_CONSOLIDATION_MAP_2026-09-03.md).
 */
export const WORKSPACES = [
  'decision',
  'portfolio',
  'intelligence',
  'watchlist',
  'ticker',
  'market',
  'search',
  'settings',
]

/**
 * Permitted cross-workspace edges.
 *
 * ADR-001 §4 states exactly one: "decision may import from market, portfolio,
 * and watchlist models. The reverse is prohibited."
 *
 * Everything not listed is denied. Workspaces that need to share data do so
 * through `models/` — ADR-001 §4 is explicit that domain ownership lives in
 * `models/` and `api/`, not in folder adjacency. Widening this map is an
 * architecture change and requires an ADR. Intelligence deliberately shares
 * through `api/` + `models/` only (no domain imports), so it gets no edge.
 */
export const PERMITTED_WORKSPACE_EDGES = {
  decision: ['market', 'portfolio', 'watchlist'],
  portfolio: [],
  intelligence: [],
  watchlist: [],
  ticker: [],
  market: [],
  search: [],
  settings: [],
}

/** Import specifiers that reach workspace `name`, in every alias and relative form. */
function workspaceSpecifiers(name) {
  return [
    `@domains/${name}`,
    `@/domains/${name}`,
    `**/domains/${name}`,
    `../${name}`,
    `../../${name}`,
    `../../../${name}`,
  ]
}

/** As above, but only the deep paths beneath a workspace's public surface. */
function workspaceDeepSpecifiers(name) {
  return [
    `@domains/${name}/**`,
    `@/domains/${name}/**`,
    `**/domains/${name}/**`,
    `../${name}/**`,
    `../../${name}/**`,
    `../../../${name}/**`,
  ]
}

/** Everything beneath a top-level layer, in alias and relative form. */
function layerSpecifiers(alias) {
  const bare = alias.replace(/^@/, '')
  return [`@${bare}`, `@${bare}/**`, `@/${bare}`, `@/${bare}/**`]
}

const SERVER_STATE_PACKAGES = ['@tanstack/react-query', '@tanstack/react-query/**']

const SERVER_STATE_DENIAL = {
  group: SERVER_STATE_PACKAGES,
  message:
    'ADR-003 N-3: Server State is confined to the Repository seam. Import ' +
    '@tanstack/react-query only in src/domains/*/repository/**, src/state/**, ' +
    'src/app/providers/** or src/tests/**. Components and adapters consume the ' +
    'hook surface a Repository exposes — never the library directly.',
}

const COMPOSITION_ROOT_DENIAL = {
  group: layerSpecifiers('@app'),
  message:
    'Phase 7 v1.1 §8: src/app is the composition root. Nothing below it may ' +
    'import from it — that would invert the layer direction.',
}

/** Build the cross-workspace denial patterns for one workspace. */
function crossWorkspacePatterns(self) {
  const permitted = PERMITTED_WORKSPACE_EDGES[self] ?? []
  const forbidden = WORKSPACES.filter((w) => w !== self && !permitted.includes(w))

  const patterns = []

  if (forbidden.length > 0) {
    patterns.push({
      group: forbidden.flatMap((w) => [...workspaceSpecifiers(w), ...workspaceDeepSpecifiers(w)]),
      message:
        `ADR-001 §4: workspace "${self}" may not import workspace ` +
        `${forbidden.map((w) => `"${w}"`).join(', ')}. Cross-domain access is by ` +
        'reference only; share through src/models. Widening the edge list requires an ADR.',
    })
  }

  if (permitted.length > 0) {
    patterns.push({
      group: permitted.flatMap((w) => workspaceDeepSpecifiers(w)),
      message:
        `ADR-001 §4: workspace "${self}" may import ` +
        `${permitted.map((w) => `"${w}"`).join(', ')} only through its public surface ` +
        '(e.g. "@domains/market"), never a deep path into its internals.',
    })
  }

  return patterns
}

function block(files, patterns) {
  return {
    files,
    rules: {
      'no-restricted-imports': 'off',
      [RULE]: ['error', { patterns }],
    },
  }
}

/**
 * Emit the boundary configuration.
 *
 * Order is significant. ESLint flat config replaces rule options wholesale for
 * every matching block, so the last matching block wins. Blocks that *relax*
 * the Server State denial (repository, state, providers, tests) are therefore
 * emitted after the blocks that impose it.
 */
export function architectureBoundaries() {
  return [
    // 1. Baseline: Server State is denied everywhere under src/ ...
    block(['src/**/*.{ts,tsx}'], [SERVER_STATE_DENIAL]),

    // 2. Workspaces: cross-workspace edges + composition-root direction.
    ...WORKSPACES.map((w) =>
      block(
        [`src/domains/${w}/**/*.{ts,tsx}`],
        [...crossWorkspacePatterns(w), COMPOSITION_ROOT_DENIAL, SERVER_STATE_DENIAL],
      ),
    ),

    // 3. Layer direction (Phase 7 v1.1 §8).
    block(
      ['src/design-system/**/*.{ts,tsx}'],
      [
        {
          group: [
            ...layerSpecifiers('@domains'),
            ...layerSpecifiers('@api'),
            ...layerSpecifiers('@models'),
            ...layerSpecifiers('@state'),
          ],
          message:
            'Phase 6 P6-01 / Phase 7 v1.1 §8: the design system is presentation only. ' +
            'It may not import workspaces, the api layer, domain models or server state — ' +
            'components receive data as props.',
        },
        COMPOSITION_ROOT_DENIAL,
        SERVER_STATE_DENIAL,
      ],
    ),

    block(
      ['src/api/**/*.{ts,tsx}'],
      [
        {
          group: [
            ...layerSpecifiers('@domains'),
            ...layerSpecifiers('@design-system'),
            ...layerSpecifiers('@state'),
          ],
          message:
            'Phase 7 v1.1 §8: the API client sits below the Repository. It may not ' +
            'import workspaces, the design system or server state. It may import @models.',
        },
        COMPOSITION_ROOT_DENIAL,
        SERVER_STATE_DENIAL,
      ],
    ),

    block(
      ['src/models/**/*.{ts,tsx}'],
      [
        {
          group: [
            ...layerSpecifiers('@domains'),
            ...layerSpecifiers('@design-system'),
            ...layerSpecifiers('@api'),
            ...layerSpecifiers('@state'),
          ],
          message:
            'Phase 7 v1.1 §9: models are pure types and mappers. They may not import the ' +
            'api layer, the design system, workspaces or server state.',
        },
        COMPOSITION_ROOT_DENIAL,
        SERVER_STATE_DENIAL,
      ],
    ),

    block(
      ['src/utils/**/*.{ts,tsx}'],
      [
        {
          group: [
            ...layerSpecifiers('@domains'),
            ...layerSpecifiers('@design-system'),
            ...layerSpecifiers('@api'),
            ...layerSpecifiers('@models'),
            ...layerSpecifiers('@state'),
          ],
          message:
            'utils is a leaf layer: it may not import any other layer. If a helper needs ' +
            'domain knowledge it belongs in that domain, not here.',
        },
        COMPOSITION_ROOT_DENIAL,
        SERVER_STATE_DENIAL,
      ],
    ),

    block(
      ['src/hooks/**/*.{ts,tsx}'],
      [
        {
          group: [...layerSpecifiers('@domains'), ...layerSpecifiers('@design-system')],
          message:
            'src/hooks holds cross-cutting presentation hooks only. Domain hooks belong to ' +
            'their workspace adapter (ADR-003 §16.2).',
        },
        COMPOSITION_ROOT_DENIAL,
        SERVER_STATE_DENIAL,
      ],
    ),

    // 4. Relaxations — must come last (see the ordering note above).

    // Repository seam: the only place in a workspace that may touch the library.
    ...WORKSPACES.map((w) =>
      block(
        [`src/domains/${w}/repository/**/*.{ts,tsx}`],
        [...crossWorkspacePatterns(w), COMPOSITION_ROOT_DENIAL],
      ),
    ),

    // QueryClient configuration (ADR-003 §16.1).
    block(
      ['src/state/**/*.{ts,tsx}'],
      [
        {
          group: [...layerSpecifiers('@domains'), ...layerSpecifiers('@design-system')],
          message:
            'ADR-003 §16.1: src/state holds QueryClient configuration and global defaults. ' +
            'It may not import workspaces or the design system.',
        },
        COMPOSITION_ROOT_DENIAL,
      ],
    ),

    // The provider itself, and test utilities that need a QueryClient wrapper.
    block(['src/app/providers/**/*.{ts,tsx}'], []),
    block(['src/tests/**/*.{ts,tsx}'], []),
  ]
}

export default architectureBoundaries
