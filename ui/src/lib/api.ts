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
  detection_rate: number
  false_positive_rate: number
}

export type SwarmSite = {
  n_consumers: number
  isolated: SiteMetrics
  pooled: SiteMetrics
  share: { flagged: number; drift_candidates: number; shared: number }
}

export type SwarmResult = {
  sites: Record<'site_a' | 'site_b' | 'site_c_low_data', SwarmSite>
  pool_size: number
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
