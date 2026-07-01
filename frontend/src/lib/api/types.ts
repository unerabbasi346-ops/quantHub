// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
// API Layer: typed request/response models — Doc 08 §API Layer
// Types derived from Doc 11 cross-domain contracts and Doc 10 API Specification
// Per Doc 00 §14.11

// Doc 08 §API Layer: standardized error response shape
export interface ApiErrorBody {
  detail: string
  error_code?: string
}

// Shared pagination envelope — Doc 10 §API Standards
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}
