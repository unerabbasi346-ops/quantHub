// Doc 08 §API Layer: centralized client
import { apiClient } from '@/lib/api/client'
import type { UserPreference } from '../types'

export const settingsService = {
  getPreferences: () => apiClient.get<UserPreference[]>('/v1/users/me/preferences'),
  setPreference: (key: string, value: unknown) =>
    apiClient.put<UserPreference>(`/v1/users/me/preferences/${key}`, { value }),
}
