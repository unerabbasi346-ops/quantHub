// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: centralized client — Doc 08 §API Layer
// Typed request/response models, auth header, retry, error handling — Doc 08 §API Layer
// Security: never expose secrets in client — Doc 08 §Security
// Per Doc 00 §14.11
import type { ErrorEnvelope, ResponseEnvelope } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Doc 08 §API Layer: standardized error processing. Carries the Doc 10 §9
// error_code (Step 4.1 backend) alongside the HTTP status so callers can
// branch on the stable code, not just the numeric status.
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly errorCode?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

function getAuthHeaders(): Record<string, string> {
  // Doc 08 §Security: authentication tokens handled here, never in component layer
  // Token retrieval from secure storage implemented in a later step
  return {}
}

async function request<T>(
  path: string,
  init?: RequestInit,
  retries = 2,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...init?.headers,
    },
  })

  // Doc 08 §API Layer: retry transient server errors
  if (response.status >= 500 && retries > 0) {
    return request<T>(path, init, retries - 1)
  }

  // Doc 10 envelope: parse once, then branch on ok. A body that fails to
  // parse (empty/non-JSON) becomes null and is handled per-branch below.
  const body: unknown = await response.json().catch(() => null)

  if (!response.ok) {
    // Doc 10 error envelope: { error: { error_code, message, ... } }.
    const err = (body as ErrorEnvelope | null)?.error
    throw new ApiError(
      response.status,
      err?.message ?? response.statusText,
      err?.error_code,
    )
  }

  // Doc 10 success envelope: unwrap `.data`. Every /v1 data endpoint
  // envelopes per Doc 10; the /health liveness probe is the one documented
  // exception and is not consumed through this typed client.
  return (body as ResponseEnvelope<T>).data
}

// Doc 08 §API Layer: typed request helpers consumed by feature services
export const apiClient = {
  get:    <T>(path: string)                   => request<T>(path),
  post:   <T>(path: string, body: unknown)    => request<T>(path, { method: 'POST',   body: JSON.stringify(body) }),
  put:    <T>(path: string, body: unknown)    => request<T>(path, { method: 'PUT',    body: JSON.stringify(body) }),
  delete: <T>(path: string)                   => request<T>(path, { method: 'DELETE' }),
}
