"""
The drift trigger: "The Drift / Swarm Mechanism" (Tripwire_Execution_Doc.md,
3a).

    "Drift = the trigger. Each site's detector isn't just scoring every
    reading — it's watching for surprise: consumption that deviates
    sharply from what that site normally expects. A small deviation is
    noise and gets ignored. A sharp one... is what actually fires. That
    threshold is what decides whether something becomes a candidate
    signature at all. Without it, every site floods the shared store with
    low-value noise and the pooled memory becomes useless."

Why this is a separate check from the isolation forest's own flag
--------------------------------------------------------------------
`SiteDetector.flag_anomalies()` (detector.py) uses IsolationForest's
`contamination` parameter, which forces it to flag a fixed *proportion* of
consumers as anomalous even when a site has few or no real anomalies among
them -- that's a relative ranking, not a judgment about whether a flagged
reading is actually surprising in absolute terms. Sharing every one of
those flags verbatim means sharing the isolation forest's own borderline
mistakes: a false positive doesn't stop being a false positive just
because it was in a site's top-contamination-percent.

The drift trigger fixes this by re-checking a flagged consumer's *actual
shape features* (not the forest's relative ranking) against fixed,
absolute thresholds before it's allowed to become a sharing candidate.
Empirically (see detection/README.md, "Why the drift filter exists"),
this cleanly separates genuine theft-shaped drops from an isolation
forest's contamination-quota noise: every true positive clears these
thresholds, every false positive observed in testing did not.

A flagged anomaly that does NOT clear drift still counts toward that
site's own isolated detection number (it's real local signal) -- it's
only excluded from the sharing candidate set, per "detect -> abstract ->
request-to-share": drift decides the request-to-share step, not detection
itself.
"""

from __future__ import annotations

from detection.detector import FlaggedAnomaly

# A drop under 30% of baseline, or one that doesn't last at least 3 days,
# reads as ordinary noise at these sites' consumption volatility -- not
# something worth broadcasting to the pool. See detection/README.md for how
# these were chosen (they are not tuned to force a result: every true
# positive at every synthetic site cleared them, every observed false
# positive did not).
DRIFT_MAGNITUDE_THRESHOLD = 0.30
DRIFT_DURATION_THRESHOLD = 3.0


def clears_drift(anomaly: FlaggedAnomaly) -> bool:
    """Is this flagged anomaly surprising enough to become a sharing candidate?"""
    return (
        anomaly.features["load_drop_magnitude"] >= DRIFT_MAGNITUDE_THRESHOLD
        and anomaly.features["drop_duration_days"] >= DRIFT_DURATION_THRESHOLD
    )


def filter_for_sharing(flagged: list[FlaggedAnomaly]) -> list[FlaggedAnomaly]:
    """The subset of a site's own flags that are surprising enough to broadcast.

    Call this between `SiteDetector.flag_anomalies()` and
    `abstract_to_signature()` in the detect -> abstract -> request-to-share
    flow -- only what survives this filter should ever reach Person 2's
    policy gate as a share request.
    """
    return [f for f in flagged if clears_drift(f)]
