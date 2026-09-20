import type {
  DecisionsResult,
  GateResult,
  SeedRecord,
  SwarmResult,
  ValidationAggregate,
} from '../lib/api'

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
        flagged: 60,
        true_positives: 56,
        detection_rate: 0.9333333333333333,
        precision: 0.9333333333333333,
        false_positive_rate: 0.007407407407407408,
      },
      pooled: {
        total_consumers: 600,
        total_theft: 60,
        flagged: 64,
        true_positives: 60,
        detection_rate: 1.0,
        precision: 0.9375,
        false_positive_rate: 0.007407407407407408,
      },
      share: { flagged: 60, drift_candidates: 56, shared: 56, denied: 0, skipped: 0 },
    },
    site_b: {
      n_consumers: 450,
      isolated: {
        total_consumers: 450,
        total_theft: 36,
        flagged: 36,
        true_positives: 35,
        detection_rate: 0.9722222222222222,
        precision: 0.9722222222222222,
        false_positive_rate: 0.0024154589371980675,
      },
      pooled: {
        total_consumers: 450,
        total_theft: 36,
        flagged: 37,
        true_positives: 36,
        detection_rate: 1.0,
        precision: 0.972972972972973,
        false_positive_rate: 0.0024154589371980675,
      },
      share: { flagged: 36, drift_candidates: 35, shared: 35, denied: 0, skipped: 0 },
    },
    site_c_low_data: {
      n_consumers: 90,
      isolated: {
        total_consumers: 90,
        total_theft: 6,
        flagged: 2,
        true_positives: 2,
        detection_rate: 0.3333333333333333,
        precision: 1.0,
        false_positive_rate: 0,
      },
      pooled: {
        total_consumers: 90,
        total_theft: 6,
        flagged: 4,
        true_positives: 4,
        detection_rate: 0.6666666666666666,
        precision: 1.0,
        false_positive_rate: 0,
      },
      share: { flagged: 2, drift_candidates: 2, shared: 2, denied: 0, skipped: 0 },
    },
  },
  pool_size: 93,
  seed_offset: 0,
}

// A real response from /api/decisions, captured the same session — the
// exact three rows the block-then-pass demo above produced, read back
// from the persistent decision log.
export const CAPTURED_DECISIONS: DecisionsResult = {
  records: [
    {
      checked_at: '2026-09-18T13:08:16.805091+00:00',
      decision: 'Deny',
      allowed: false,
      site_id: 'site_c_low_data',
      resource_id: 'raw-46cc8cfd29a7',
      kind: 'raw_record',
      granularity: 175,
      reasons: [
        'identifying field(s) present: has_meter_id, has_consumer_id, has_raw_series, has_household_field, has_location',
      ],
    },
    {
      checked_at: '2026-09-18T13:08:16.808947+00:00',
      decision: 'Deny',
      allowed: false,
      site_id: 'site_c_low_data',
      resource_id: 'sig-63c60eacac72',
      kind: 'signature',
      granularity: 31,
      reasons: ['identifying field(s) present: has_meter_id'],
    },
    {
      checked_at: '2026-09-18T13:08:16.816059+00:00',
      decision: 'Allow',
      allowed: true,
      site_id: 'site_c_low_data',
      resource_id: 'sig-67068c093601',
      kind: 'signature',
      granularity: 6,
      reasons: ['signature is clean and within the granularity threshold'],
    },
  ],
  summary: {
    total: 3,
    allowed: 1,
    denied: 2,
    allow_rate: 0.3333333333333333,
    by_site: { site_c_low_data: 3 },
    denial_reasons: {
      'identifying field(s) present: has_meter_id, has_consumer_id, has_raw_series, has_household_field, has_location': 1,
      'identifying field(s) present: has_meter_id': 1,
    },
  },
}

// A real 5-seed run of scripts/validate_across_seeds.py's method, captured
// the same session via /api/validate/stream?n_seeds=5.
export const CAPTURED_VALIDATION_SEEDS: SeedRecord[] = [
  {
    seed_offset: 0,
    sites: {
      site_a: { isolated_detection_rate: 0.9333333333333333, pooled_detection_rate: 1.0, improvement: 0.06666666666666665, isolated_false_positive_rate: 0.007407407407407408, pooled_false_positive_rate: 0.007407407407407408 },
      site_b: { isolated_detection_rate: 0.9722222222222222, pooled_detection_rate: 1.0, improvement: 0.02777777777777779, isolated_false_positive_rate: 0.0024154589371980675, pooled_false_positive_rate: 0.0024154589371980675 },
      site_c_low_data: { isolated_detection_rate: 0.3333333333333333, pooled_detection_rate: 0.6666666666666666, improvement: 0.3333333333333333, isolated_false_positive_rate: 0, pooled_false_positive_rate: 0 },
    },
    low_data_improvement: 0.3333333333333333,
  },
  {
    seed_offset: 1,
    sites: {
      site_a: { isolated_detection_rate: 0.85, pooled_detection_rate: 0.9166666666666666, improvement: 0.06666666666666665, isolated_false_positive_rate: 0.016666666666666666, pooled_false_positive_rate: 0.016666666666666666 },
      site_b: { isolated_detection_rate: 0.9722222222222222, pooled_detection_rate: 1.0, improvement: 0.02777777777777779, isolated_false_positive_rate: 0.0024154589371980675, pooled_false_positive_rate: 0.0024154589371980675 },
      site_c_low_data: { isolated_detection_rate: 0.3333333333333333, pooled_detection_rate: 0.8333333333333334, improvement: 0.5, isolated_false_positive_rate: 0, pooled_false_positive_rate: 0 },
    },
    low_data_improvement: 0.5,
  },
  {
    seed_offset: 2,
    sites: {
      site_a: { isolated_detection_rate: 0.95, pooled_detection_rate: 1.0, improvement: 0.050000000000000044, isolated_false_positive_rate: 0.005555555555555556, pooled_false_positive_rate: 0.005555555555555556 },
      site_b: { isolated_detection_rate: 0.9166666666666666, pooled_detection_rate: 0.9722222222222222, improvement: 0.05555555555555558, isolated_false_positive_rate: 0.007246376811594203, pooled_false_positive_rate: 0.007246376811594203 },
      site_c_low_data: { isolated_detection_rate: 0.3333333333333333, pooled_detection_rate: 0.8333333333333334, improvement: 0.5, isolated_false_positive_rate: 0, pooled_false_positive_rate: 0 },
    },
    low_data_improvement: 0.5,
  },
  {
    seed_offset: 3,
    sites: {
      site_a: { isolated_detection_rate: 0.9666666666666667, pooled_detection_rate: 1.0, improvement: 0.033333333333333326, isolated_false_positive_rate: 0.003703703703703704, pooled_false_positive_rate: 0.003703703703703704 },
      site_b: { isolated_detection_rate: 1.0, pooled_detection_rate: 1.0, improvement: 0, isolated_false_positive_rate: 0, pooled_false_positive_rate: 0 },
      site_c_low_data: { isolated_detection_rate: 0.3333333333333333, pooled_detection_rate: 1.0, improvement: 0.6666666666666667, isolated_false_positive_rate: 0, pooled_false_positive_rate: 0 },
    },
    low_data_improvement: 0.6666666666666667,
  },
  {
    seed_offset: 4,
    sites: {
      site_a: { isolated_detection_rate: 0.95, pooled_detection_rate: 0.9833333333333333, improvement: 0.033333333333333326, isolated_false_positive_rate: 0.005555555555555556, pooled_false_positive_rate: 0.005555555555555556 },
      site_b: { isolated_detection_rate: 0.9444444444444444, pooled_detection_rate: 1.0, improvement: 0.05555555555555558, isolated_false_positive_rate: 0.004830917874396135, pooled_false_positive_rate: 0.004830917874396135 },
      site_c_low_data: { isolated_detection_rate: 0.3333333333333333, pooled_detection_rate: 1.0, improvement: 0.6666666666666667, isolated_false_positive_rate: 0, pooled_false_positive_rate: 0 },
    },
    low_data_improvement: 0.6666666666666667,
  },
]

export const CAPTURED_VALIDATION_AGGREGATE: ValidationAggregate = {
  n_seeds: 5,
  low_data_site: 'site_c_low_data',
  mean_improvement: 0.5333333333333334,
  min_improvement: 0.3333333333333333,
  max_improvement: 0.6666666666666667,
  false_positive_rate_ever_worse_pooled: false,
}
