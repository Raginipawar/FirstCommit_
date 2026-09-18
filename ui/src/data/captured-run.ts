import type { GateResult, SwarmResult } from '../lib/api'

// A real response from server.py, captured on 2026-09-17 so the section has
// something honest to show before the backend has been started this
// session. Shape is identical to what /api/run/gate and /api/run/swarm
// return live. This is not reconstructed or rounded, it's one saved reply.

export const CAPTURED_GATE: GateResult = {
  site_id: 'site_c_low_data',
  raw_attempt: {
    allowed: false,
    decision: 'Deny',
    resource_id: 'raw-8bed6bfad362',
    kind: 'raw_record',
    granularity: 175,
    reasons: [
      'identifying field(s) present: has_meter_id, has_consumer_id, has_raw_series, has_household_field, has_location',
    ],
  },
  leaky_signature: {
    granularity: 31,
    decision: {
      allowed: false,
      decision: 'Deny',
      resource_id: 'sig-ac1e2f722d2b',
      kind: 'signature',
      granularity: 31,
      reasons: ['identifying field(s) present: has_meter_id'],
    },
  },
  clean_signature: {
    granularity: 6,
    load_drop_magnitude_bucket: 4,
    timing_bucket: 'mid-cycle',
    recovery_shape: 'none',
    decision: {
      allowed: true,
      decision: 'Allow',
      resource_id: 'sig-36755cd86a1c',
      kind: 'signature',
      granularity: 6,
      reasons: ['signature is clean and within the granularity threshold'],
    },
  },
  summary: { total: 3, allowed: 1, denied: 2 },
}

export const CAPTURED_SWARM: SwarmResult = {
  sites: {
    site_a: {
      n_consumers: 600,
      isolated: {
        total_consumers: 600,
        total_theft: 60,
        detection_rate: 0.9333333333333333,
        false_positive_rate: 0.007407407407407408,
      },
      pooled: {
        total_consumers: 600,
        total_theft: 60,
        detection_rate: 1.0,
        false_positive_rate: 0.007407407407407408,
      },
      share: { flagged: 60, drift_candidates: 56, shared: 56 },
    },
    site_b: {
      n_consumers: 450,
      isolated: {
        total_consumers: 450,
        total_theft: 36,
        detection_rate: 0.9722222222222222,
        false_positive_rate: 0.0024154589371980675,
      },
      pooled: {
        total_consumers: 450,
        total_theft: 36,
        detection_rate: 1.0,
        false_positive_rate: 0.0024154589371980675,
      },
      share: { flagged: 36, drift_candidates: 35, shared: 35 },
    },
    site_c_low_data: {
      n_consumers: 90,
      isolated: {
        total_consumers: 90,
        total_theft: 6,
        detection_rate: 0.3333333333333333,
        false_positive_rate: 0,
      },
      pooled: {
        total_consumers: 90,
        total_theft: 6,
        detection_rate: 0.6666666666666666,
        false_positive_rate: 0,
      },
      share: { flagged: 2, drift_candidates: 2, shared: 2 },
    },
  },
  pool_size: 93,
}
