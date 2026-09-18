// Talks to server.py (../../tripwire/server.py), which imports the exact
// same detection/policy/orchestration modules the CLI scripts use and
// re-runs them fresh on every call. Nothing here is a mock endpoint.

const API_BASE = 'http://localhost:8000'

export type PolicyDecision = {
  allowed: boolean
  decision: string
  resource_id: string
  kind: string
  granularity: number
  reasons: string[]
}

export type GateResult = {
  site_id: string
  raw_attempt: PolicyDecision
  leaky_signature: { granularity: number; decision: PolicyDecision }
  clean_signature: {
    granularity: number
    load_drop_magnitude_bucket: number
    timing_bucket: string
    recovery_shape: string
    decision: PolicyDecision
  }
  summary: { total: number; allowed: number; denied: number }
}

export type SiteMetrics = {
  total_consumers: number
  total_theft: number
  flagged: number
  true_positives: number
  detection_rate: number
  precision: number
  false_positive_rate: number
}

export type SwarmSite = {
  n_consumers: number
  isolated: SiteMetrics
  pooled: SiteMetrics
  share: { flagged: number; drift_candidates: number; shared: number; denied: number; skipped: number }
}

export type SwarmResult = {
  sites: Record<'site_a' | 'site_b' | 'site_c_low_data', SwarmSite>
  pool_size: number
  seed_offset?: number
}

async function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), ms)
  try {
    return await promise
  } finally {
    clearTimeout(timer)
  }
}

export async function checkBackendOnline(): Promise<boolean> {
  try {
    const res = await withTimeout(
      fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(1500) }),
      1600,
    )
    return res.ok
  } catch {
    return false
  }
}

export async function runGate(): Promise<GateResult> {
  const res = await fetch(`${API_BASE}/api/run/gate`, { method: 'POST' })
  if (!res.ok) throw new Error(`gate run failed: ${res.status}`)
  return res.json()
}

export async function runSwarm(): Promise<SwarmResult> {
  const res = await fetch(`${API_BASE}/api/run/swarm`, { method: 'POST' })
  if (!res.ok) throw new Error(`swarm run failed: ${res.status}`)
  return res.json()
}

// --- Decision log / audit trail --------------------------------------

export type DecisionRecord = {
  checked_at: string
  decision: string
  allowed: boolean
  site_id: string
  resource_id: string
  kind: string
  granularity: number
  reasons: string[]
}

export type DecisionSummary = {
  total: number
  allowed: number
  denied: number
  allow_rate: number
  by_site: Record<string, number>
  denial_reasons: Record<string, number>
}

export type DecisionsResult = {
  records: DecisionRecord[]
  summary: DecisionSummary
}

export async function getDecisions(): Promise<DecisionsResult> {
  const res = await fetch(`${API_BASE}/api/decisions`)
  if (!res.ok) throw new Error(`decisions fetch failed: ${res.status}`)
  return res.json()
}

export async function clearDecisions(): Promise<void> {
  await fetch(`${API_BASE}/api/decisions/clear`, { method: 'POST' })
}

// --- Live pipeline stream (SSE) ---------------------------------------

export type PipelineEvent =
  | { phase: 'detect'; site_id: string; flagged: number }
  | { phase: 'share'; site_id: string; drift_candidates: number; shared: number; denied: number }
  | { phase: 'recheck'; site_id: string; pooled_flagged: number }
  | { phase: 'done'; result: SwarmResult }

export function streamSwarm(
  onEvent: (e: PipelineEvent) => void,
  onError: (err: unknown) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/api/run/swarm/stream`)
  source.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data) as PipelineEvent
      onEvent(parsed)
      if (parsed.phase === 'done') source.close()
    } catch (err) {
      onError(err)
      source.close()
    }
  }
  source.onerror = (err) => {
    onError(err)
    source.close()
  }
  return () => source.close()
}

// --- Multi-seed validation (SSE) ---------------------------------------

export type SeedRecord = {
  seed_offset: number
  sites: Record<
    string,
    {
      isolated_detection_rate: number
      pooled_detection_rate: number
      improvement: number
      isolated_false_positive_rate: number
      pooled_false_positive_rate: number
    }
  >
  low_data_improvement: number
}

export type ValidationAggregate = {
  n_seeds: number
  low_data_site: string
  mean_improvement: number
  min_improvement: number
  max_improvement: number
  false_positive_rate_ever_worse_pooled: boolean
}

export type ValidationEvent =
  | ({ phase: 'seed' } & SeedRecord)
  | { phase: 'done'; per_seed: SeedRecord[]; aggregate: ValidationAggregate }

export function streamValidation(
  nSeeds: number,
  onEvent: (e: ValidationEvent) => void,
  onError: (err: unknown) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/api/validate/stream?n_seeds=${nSeeds}`)
  source.onmessage = (msg) => {
    try {
      const parsed = JSON.parse(msg.data) as ValidationEvent
      onEvent(parsed)
      if (parsed.phase === 'done') source.close()
    } catch (err) {
      onError(err)
      source.close()
    }
  }
  source.onerror = (err) => {
    onError(err)
    source.close()
  }
  return () => source.close()
}
