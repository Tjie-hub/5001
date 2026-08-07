/**
 * URL normalization guard — Phase 9 Workstream B (B7).
 *
 * Applies the canonical-URL rules from Phase 4 P4-13 §12 to every navigation.
 *
 * Uses history REPLACE, never PUSH (P4-06 §13: "Replace History — URL
 * normalization"). Pushing would put the non-canonical URL in the back stack,
 * so Back would bounce the user between /ticker/bbca and /ticker/BBCA forever.
 *
 * The pure rule lives in url-normalization.ts; this is only the React binding.
 */
import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router'
import { normalizePathname } from './url-normalization'

export function UrlNormalizationGuard() {
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    const canonical = normalizePathname(location.pathname)

    if (canonical === null) return

    void navigate(
      { pathname: canonical, search: location.search, hash: location.hash },
      { replace: true },
    )
  }, [location.pathname, location.search, location.hash, navigate])

  return null
}
