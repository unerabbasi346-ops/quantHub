// Doc 08 §API Layer: typed models mirroring backend/src/quant_hub/hermes/
// api/hermes_router.py's Pydantic response schemas field-for-field. Every
// rate/return/fraction here is the RAW unformatted number the backend
// returns (see that router's module docstring) — components apply
// @/lib/utils/format.ts's formatters at render time, never here.
import type { ISOTimestamp } from '@/types'

export type ServiceStatusName = 'UP' | 'DOWN' | 'NOT_CONFIGURED'

export interface HermesServiceStatus {
  name: string
  status: ServiceStatusName
  latency_ms: number | null
  detail: string
}

export type FreshnessStatus = 'FRESH' | 'STALE' | 'DEAD'

export interface AssetFreshness {
  asset_id: string
  symbol: string
  instrument_type: string
  last_bar_ts: ISOTimestamp | null
  bar_count: number
  staleness_seconds: number | null
  status: FreshnessStatus
}

export interface FundingFreshness {
  asset_id: string
  symbol: string
  last_funding_ts: ISOTimestamp | null
  staleness_seconds: number | null
  status: FreshnessStatus
}

export interface StrategyLifecycle {
  strategy_id: string
  name: string
  status: string
  last_signal_ts: ISOTimestamp | null
  signals_24h: number
  valid_rate_24h: number | null
  latest_backtest_status: string | null
  latest_backtest_completed_at: ISOTimestamp | null
}

export interface MLModelStatus {
  model_id: string
  name: string
  model_type: string
  status: string
  accuracy: number | null
  // Majority-class baseline the deploy gate compared against (api/ml.py) —
  // null for models trained before baseline gating existed.
  baseline: number | null
  deployed_at: ISOTimestamp | null
  created_at: ISOTimestamp
}

export interface TrainingJob {
  job_id: string
  model_type: string
  status: string
  created_at: string
  completed_at: string | null
}

export interface SystemStatus {
  health_score: number
  services: HermesServiceStatus[]
  assets: AssetFreshness[]
  funding: FundingFreshness[]
  strategies: StrategyLifecycle[]
  models: MLModelStatus[]
  training_jobs: TrainingJob[]
  generated_at: ISOTimestamp
}

export interface StrategyEngineSummary {
  active_count: number
  signals_24h: number
}

export interface DataPipelineSummary {
  fresh_count: number
  stale_count: number
  dead_count: number
}

export interface MLEngineSummary {
  trained_count: number
  last_accuracy: number | null
}

export interface ExecutionEngineSummary {
  orders_today: number
  fill_rate_today: number | null
}

export interface HealthSummary {
  health_score: number
  services: HermesServiceStatus[]
  strategy_engine: StrategyEngineSummary
  data_pipeline: DataPipelineSummary
  ml_engine: MLEngineSummary
  execution_engine: ExecutionEngineSummary
  generated_at: ISOTimestamp
}

export interface PipelineStatus {
  assets: AssetFreshness[]
  funding: FundingFreshness[]
}

export interface StrategiesStatus {
  strategies: StrategyLifecycle[]
}

export interface MLStatus {
  models: MLModelStatus[]
  training_jobs: TrainingJob[]
}
