// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { settingsService } from '../services/settings.service'

export function usePreferences() {
  return useQuery({ queryKey: ['preferences'], queryFn: settingsService.getPreferences })
}
