/**
 * Architecture boundary guard tests — Phase 9 Workstream A (task A4).
 *
 * Phase 9 Workstream A exit criteria require that "import-boundary lint
 * demonstrably fails a deliberate violation". This suite is that proof: it
 * runs the real ESLint configuration against deliberately-illegal source and
 * asserts the guard reports an error, and against legal source and asserts it
 * does not.
 *
 * Rules under test derive from:
 *   - ADR-001 §4  — domain dependency edge list
 *   - ADR-003 N-3 — Server State confined to the Repository seam
 *   - Phase 7 v1.1 §8/§9 — layer direction and DTO isolation
 *
 * If a guard is removed or weakened, a test here fails. That is the point.
 */
import { describe, expect, it } from 'vitest'
import { ESLint } from 'eslint'

// cwd defaults to the process working directory, which is the frontend package
// root under `npm test`. Left implicit so this file needs no Node type globals.
const eslint = new ESLint()

/** Lint a source string as if it lived at `filePath`; return rule IDs reported. */
async function lintAs(filePath: string, code: string): Promise<string[]> {
  const results = await eslint.lintText(code, { filePath, warnIgnored: false })
  return results.flatMap((r) => r.messages.map((m) => m.ruleId ?? 'unknown'))
}

const RESTRICTED = '@typescript-eslint/no-restricted-imports'

async function expectBlocked(filePath: string, code: string) {
  const ruleIds = await lintAs(filePath, code)
  expect(ruleIds, `expected ${filePath} to be blocked for:\n${code}`).toContain(RESTRICTED)
}

async function expectAllowed(filePath: string, code: string) {
  const ruleIds = await lintAs(filePath, code)
  expect(ruleIds, `expected ${filePath} to be allowed for:\n${code}`).not.toContain(RESTRICTED)
}

describe('ADR-001 §4 — cross-workspace imports', () => {
  it('blocks a workspace importing another workspace (market → portfolio)', async () => {
    await expectBlocked(
      'src/domains/market/market-view.ts',
      `import { holdings } from '@domains/portfolio'\nexport const x = holdings\n`,
    )
  })

  it('blocks the reverse of the one permitted edge (market → decision)', async () => {
    await expectBlocked(
      'src/domains/market/market-view.ts',
      `import { queue } from '@domains/decision'\nexport const x = queue\n`,
    )
  })

  it('blocks a deep import into another workspace even along a permitted edge', async () => {
    await expectBlocked(
      'src/domains/decision/decision-view.ts',
      `import { thing } from '@domains/market/repository/market-queries'\nexport const x = thing\n`,
    )
  })

  it('blocks a relative path escape into another workspace', async () => {
    await expectBlocked(
      'src/domains/watchlist/watchlist-view.ts',
      `import { x } from '../portfolio/holdings'\nexport const y = x\n`,
    )
  })

  it('allows the permitted edge decision → market public surface', async () => {
    await expectAllowed(
      'src/domains/decision/decision-view.ts',
      `import { marketContext } from '@domains/market'\nexport const x = marketContext\n`,
    )
  })

  it('allows a workspace importing its own internals', async () => {
    await expectAllowed(
      'src/domains/market/market-view.ts',
      `import { x } from './repository/market-queries'\nexport const y = x\n`,
    )
  })

  it('allows any workspace importing shared models', async () => {
    await expectAllowed(
      'src/domains/settings/settings-view.ts',
      `import type { Instrument } from '@models/instrument'\nexport type X = Instrument\n`,
    )
  })
})

describe('ADR-003 N-3 — Server State confined to the Repository seam', () => {
  it('blocks @tanstack/react-query in a workspace component', async () => {
    await expectBlocked(
      'src/domains/watchlist/components/candidate-list.ts',
      `import { useQuery } from '@tanstack/react-query'\nexport const x = useQuery\n`,
    )
  })

  it('blocks @tanstack/react-query in a design-system component', async () => {
    await expectBlocked(
      'src/design-system/components/table.ts',
      `import { useQuery } from '@tanstack/react-query'\nexport const x = useQuery\n`,
    )
  })

  it('blocks @tanstack/react-query in a domain adapter', async () => {
    await expectBlocked(
      'src/domains/market/adapters/use-market.ts',
      `import { useQuery } from '@tanstack/react-query'\nexport const x = useQuery\n`,
    )
  })

  it('allows @tanstack/react-query inside a domain repository', async () => {
    await expectAllowed(
      'src/domains/market/repository/market-queries.ts',
      `import { useQuery } from '@tanstack/react-query'\nexport const x = useQuery\n`,
    )
  })

  it('allows @tanstack/react-query in state (QueryClient configuration)', async () => {
    await expectAllowed(
      'src/state/query-client.ts',
      `import { QueryClient } from '@tanstack/react-query'\nexport const x = QueryClient\n`,
    )
  })

  it('allows @tanstack/react-query in app providers', async () => {
    await expectAllowed(
      'src/app/providers/query-provider.ts',
      `import { QueryClientProvider } from '@tanstack/react-query'\nexport const x = QueryClientProvider\n`,
    )
  })
})

describe('Phase 7 v1.1 §8 — layer direction', () => {
  it('blocks design-system importing a workspace', async () => {
    await expectBlocked(
      'src/design-system/components/card.ts',
      `import { x } from '@domains/portfolio'\nexport const y = x\n`,
    )
  })

  it('blocks design-system importing the api layer', async () => {
    await expectBlocked(
      'src/design-system/components/card.ts',
      `import { client } from '@api/client'\nexport const y = client\n`,
    )
  })

  it('blocks the api layer importing a workspace', async () => {
    await expectBlocked(
      'src/api/client.ts',
      `import { x } from '@domains/decision'\nexport const y = x\n`,
    )
  })

  it('blocks models importing the api layer', async () => {
    await expectBlocked(
      'src/models/recommendation.ts',
      `import { client } from '@api/client'\nexport const y = client\n`,
    )
  })

  it('blocks utils importing a workspace', async () => {
    await expectBlocked(
      'src/utils/format.ts',
      `import { x } from '@domains/ticker'\nexport const y = x\n`,
    )
  })

  it('blocks a workspace importing the composition root', async () => {
    await expectBlocked(
      'src/domains/ticker/ticker-view.ts',
      `import { providers } from '@app/providers'\nexport const y = providers\n`,
    )
  })

  it('allows a workspace importing the design system', async () => {
    await expectAllowed(
      'src/domains/ticker/ticker-view.ts',
      `import { Card } from '@design-system/components'\nexport const y = Card\n`,
    )
  })

  it('allows the api layer importing models', async () => {
    await expectAllowed(
      'src/api/client.ts',
      `import type { Dto } from '@models/dto'\nexport type X = Dto\n`,
    )
  })
})
