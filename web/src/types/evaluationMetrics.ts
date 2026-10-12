export interface EvaluationMetric {
  id: string
  label: string
  value: number | null
  unit: 'seconds' | 'tokens' | '%' | 'score'
  samples: number
  status: 'available' | 'partial' | 'unavailable'
  definition: string
  reason: string
  numerator: number | null
  denominator: number | null
}

export interface EvaluationSnapshot {
  schema_version: 1
  generated_at: string
  population: { started: number; completed: number; failed: number; cancelled: number; incomplete: number; timed_successes: number; complete_usage_runs: number; labeled_runs: number }
  window: { start: string | null; end: string | null }
  groups: Array<{ id: string; label: string; metrics: EvaluationMetric[] }>
  stages: Array<{ stage: string; started: number; completed: number; failed: number; degraded: number; mean_seconds: number | null; p50_seconds: number | null; p95_seconds: number | null; p99_seconds: number | null }>
  notes: string[]
}

export function parseEvaluationSnapshot(value: unknown): EvaluationSnapshot {
  const data = value as Partial<EvaluationSnapshot> | null
  const count = (item: unknown) => typeof item === 'number' && Number.isFinite(item) && item >= 0
  const populationFields = ['started', 'completed', 'failed', 'cancelled', 'incomplete', 'timed_successes', 'complete_usage_runs', 'labeled_runs'] as const
  if (!data || data.schema_version !== 1 || typeof data.generated_at !== 'string' || !data.population ||
    !populationFields.every(key => count(data.population?.[key])) ||
    !data.window || !Array.isArray(data.groups) || !Array.isArray(data.stages) || !Array.isArray(data.notes) || !data.notes.every(note => typeof note === 'string')) throw new Error('invalid snapshot')
  for (const group of data.groups) {
    if (!group || typeof group.id !== 'string' || typeof group.label !== 'string' || !Array.isArray(group.metrics)) throw new Error('invalid group')
    for (const metric of group.metrics) {
      if (!metric || typeof metric.id !== 'string' || typeof metric.label !== 'string' || !count(metric.samples) ||
        !(metric.value === null || count(metric.value)) || !['seconds', 'tokens', '%', 'score'].includes(metric.unit) ||
        !['available', 'partial', 'unavailable'].includes(metric.status) || typeof metric.definition !== 'string' || typeof metric.reason !== 'string') throw new Error('invalid metric')
    }
  }
  for (const stage of data.stages) {
    if (!stage || typeof stage.stage !== 'string' || ![stage.started, stage.completed, stage.failed, stage.degraded].every(count) ||
      ![stage.mean_seconds, stage.p50_seconds, stage.p95_seconds, stage.p99_seconds].every(item => item === null || count(item))) throw new Error('invalid stage')
  }
  return data as EvaluationSnapshot
}
