// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: centralized client — Doc 08 §API Layer
// Typed request/response models, auth header, retry, error handling — Doc 08 §API Layer
// Security: never expose secrets in client — Doc 08 §Security
// Per Doc 00 §14.11

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Doc 08 §API Layer: standardized error processing
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
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

  if (!response.ok) {
    const message = await response.text().catch(() => response.statusText)
    throw new ApiError(response.status, message)
  }

  return response.json() as Promise<T>
}

// Doc 08 §API Layer: typed request helpers consumed by feature services
export const apiClient = {
  get:    <T>(path: string)                   => request<T>(path),
  post:   <T>(path: string, body: unknown)    => request<T>(path, { method: 'POST',   body: JSON.stringify(body) }),
  put:    <T>(path: string, body: unknown)    => request<T>(path, { method: 'PUT',    body: JSON.stringify(body) }),
  delete: <T>(path: string)                   => request<T>(path, { method: 'DELETE' }),
}
