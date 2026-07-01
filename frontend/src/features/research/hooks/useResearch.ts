// Doc 08 §State Management: TanStack Query for server state
import { useQuery } from '@tanstack/react-query'
import { researchService } from '../services/research.service'

export function useResearchProjects() {
  return useQuery({ queryKey: ['research-projects'], queryFn: researchService.getProjects })
}

export function useExperiments(projectId: string) {
  return useQuery({
    queryKey: ['experiments', projectId],
    queryFn: () => researchService.getExperiments(projectId),
    enabled: Boolean(projectId),
  })
}
