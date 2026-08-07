/**
 * URL normalization — Phase 9 Workstream B (B7).
 *
 * Phase 4 P4-13 §12: "Only one canonical representation is permitted."
 * RM-01 / RU-01: every analytical resource has exactly one canonical URL.
 *
 * Two rules are frozen today:
 *   /ticker/bbca   →  /ticker/BBCA   (symbol format is uppercase, §6)
 *   /ticker/BBCA/  →  /ticker/BBCA   (trailing slash stripped)
 *
 * Normalization is applied with history REPLACE, never PUSH (P4-06 §13), so
 * a corrected URL never becomes a back-button stop.
 *
 * Deliberately a pure function: normalization is a URL rule, not a React
 * concern, and keeping it pure is what makes it exhaustively testable.
 */

/** Route prefixes whose next segment is a resource identifier to uppercase. */
const UPPERCASE_SYMBOL_PREFIXES = ['ticker'] as const

/**
 * Return the canonical form of `pathname`, or null when it is already canonical.
 *
 * Returning null rather than the unchanged input is intentional — callers can
 * treat null as "no navigation required" without a string comparison, which
 * removes any chance of a redirect loop.
 */
export function normalizePathname(pathname: string): string | null {
  if (pathname === '/') return null

  const withoutTrailingSlash = pathname.endsWith('/') ? pathname.slice(0, -1) : pathname

  const segments = withoutTrailingSlash.split('/').filter(Boolean)
  const [head, second, ...rest] = segments

  let normalized: string

  if (head !== undefined && second !== undefined) {
    const isSymbolRoute = (UPPERCASE_SYMBOL_PREFIXES as readonly string[]).includes(head)
    const canonicalSecond = isSymbolRoute ? second.toUpperCase() : second

    normalized = `/${[head, canonicalSecond, ...rest].join('/')}`
  } else {
    normalized = `/${segments.join('/')}`
  }

  return normalized === pathname ? null : normalized
}
