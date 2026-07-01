// Doc 08 §API Layer: typed models — anchored to core.user_preferences schema
import type { UUID } from '@/types'

export interface UserPreference {
  id: UUID
  userId: UUID
  preferenceKey: string
  preferenceValue: unknown
}
