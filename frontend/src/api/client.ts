/**
 * API v1 client — thin fetch wrapper over the `{ok, data, meta}` /
 * `{ok:false, error, meta}` envelope every `/api/v1/*` route shares
 * (routes/v1/envelope.py). Sits below the Repository seam (Phase 7 v1.1 §8);
 * it may not import workspaces, the design system or server state (see
 * tools/eslint/architecture-boundaries.js).
 *
 * Deliberately not wired to @tanstack/react-query here — ADR-003 (Server
 * State via TanStack Query) is still PROPOSED, not approved, and the library
 * isn't a project dependency yet. This client is the transport a future
 * Repository layer would call; consumers today call it directly via
 * domain-local hooks (see domains/operations/use-operations-data.ts).
 */

export interface ApiMeta {
  readonly api_version: string
  readonly request_id: string
  readonly timestamp: string
}

interface ApiSuccessEnvelope<T> {
  readonly ok: true
  readonly data: T
  readonly meta: ApiMeta
}

interface ApiErrorEnvelope {
  readonly ok: false
  readonly error: {
    readonly code: string
    readonly message: string
    readonly details: Record<string, unknown>
  }
  readonly meta: ApiMeta
}

type ApiEnvelope<T> = ApiSuccessEnvelope<T> | ApiErrorEnvelope

export class ApiRequestError extends Error {
  readonly code: string
  readonly status: number
  readonly details: Record<string, unknown>

  constructor(code: string, status: number, message: string, details: Record<string, unknown>) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.status = status
    this.details = details
  }
}

/**
 * GET one `/api/v1/*` path and unwrap the envelope. Throws `ApiRequestError`
 * for both transport-level failures (network error, non-JSON response) and
 * envelope-level errors (`ok: false`) so callers have one error type to
 * handle regardless of failure mode.
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(path, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value))
    }
  }

  let response: Response
  try {
    response = await fetch(url.pathname + url.search, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    })
  } catch (cause) {
    throw new ApiRequestError('NETWORK_ERROR', 0, 'network request failed', {
      cause: String(cause),
    })
  }

  let envelope: ApiEnvelope<T>
  try {
    envelope = (await response.json()) as ApiEnvelope<T>
  } catch {
    throw new ApiRequestError(
      'INVALID_RESPONSE',
      response.status,
      'response was not valid JSON',
      {},
    )
  }

  if (!envelope.ok) {
    throw new ApiRequestError(
      envelope.error.code,
      response.status,
      envelope.error.message,
      envelope.error.details,
    )
  }

  return envelope.data
}
