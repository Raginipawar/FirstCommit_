// TRIPWIRE sharing policy — the block-then-pass boundary.
//
// Default Cedar behaviour is implicit deny, so a raw_record payload is
// already rejected by having no matching permit. The two rules below make
// the boundary explicit and inspectable instead of relying on that default:
//
//   Rule 1 (forbid) — an identifying field present anywhere, for any reason,
//   is an automatic, unconditional deny. forbid always wins over permit in
//   Cedar regardless of rule order, so this cannot be accidentally overridden
//   by a looser permit rule added later.
//
//   Rule 2 (permit) — a properly abstracted signature is allowed to share
//   only if it is also coarse enough. This catches payloads that cleared
//   Rule 1 (no named identifier present) but are still too fine-grained to
//   be safe to pool, e.g. a raw un-bucketed anomaly score.
//
// GRANULARITY_THRESHOLD = 10 here must match
// policy/signature.py::GRANULARITY_THRESHOLD.

forbid (
    principal,
    action == Action::"share",
    resource
) when {
    resource.has_meter_id ||
    resource.has_consumer_id ||
    resource.has_raw_series ||
    resource.has_household_field ||
    resource.has_location
};

permit (
    principal,
    action == Action::"share",
    resource
) when {
    resource.kind == "signature" &&
    resource.granularity <= 10
};
