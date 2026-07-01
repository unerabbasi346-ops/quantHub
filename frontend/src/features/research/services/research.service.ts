// Doc 08 §API Layer: centralized client
import { apiClient } from '@/lib/api/client'
import type { ResearchProject, Experiment } from '../types'

export const researchService = {
  getProjects: () => apiClient.get<ResearchProject[]>('/v1/research/projects'),
  getExperiments: (projectId: string) =>
    apiClient.get<Experiment[]>(`/v1/research/projects/${projectId}/experiments`),
}
