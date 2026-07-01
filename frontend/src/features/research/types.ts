// Doc 08 §API Layer: typed models — anchored to analytics.research_projects schema
import type { UUID, ISOTimestamp } from '@/types'

export interface ResearchProject {
  id: UUID
  name: string
  status: 'ACTIVE' | 'COMPLETED' | 'ARCHIVED'
  createdAt: ISOTimestamp
}

export interface Experiment {
  id: UUID
  projectId: UUID
  name: string
  status: 'DRAFT' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  createdAt: ISOTimestamp
}
