// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: typed request/response models — Doc 08 §API Layer
// Types mirror the backend's Doc 10 response envelope (api/envelope.py,
// Step 4.1): every /v1 data endpoint returns ResponseEnvelope on success and
// ErrorEnvelope on failure. Reconciled in Step 4.2 from the Step 0.5
// speculative shapes (which assumed a `{detail}` error + a pagination
// wrapper that no real endpoint returns) to the shapes the backend actually
// emits.
// Per Doc 00 §14.11

// Doc 10 §6 error body: error_code + message (+ optional details).
export interface ApiErrorDetail {
  error_code: string
  message: string
  details?: unknown
}

// Doc 10 success envelope — "every response contains request_id, timestamp,
// status, version, data or error envelope."
export interface ResponseEnvelope<T> {
  status: 'success'
  version: string
  request_id: string
  timestamp: string
  data: T
}

// Doc 10 error envelope — same top-level shape, `error` in place of `data`.
export interface ErrorEnvelope {
  status: 'error'
  version: string
  request_id: string
  timestamp: string
  error: ApiErrorDetail
}
