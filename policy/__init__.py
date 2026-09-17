"""
Person 2's component: Policy & Abstraction.

Public surface other modules should import:

    from policy.signature import abstract_to_signature, abstract_to_signature_leaky, to_raw_payload
    from policy.gate import PolicyGate, PolicyDecision
    from policy.decision_log import DecisionLogger, iter_records, filter_records, summarize

See policy/README.md for the full interface contract with Person 1
(detection) and Person 3 (orchestration & memory).
"""

from .decision_log import DecisionLogger, filter_records, iter_records, summarize
from .gate import PolicyDecision, PolicyGate, PolicyLoadError
from .signature import (
    AbstractionError,
    Signature,
    abstract_to_signature,
    abstract_to_signature_leaky,
    compute_granularity,
    derive_shape_features,
    shape_key_from_dict,
    to_raw_payload,
)

__all__ = [
    "DecisionLogger",
    "filter_records",
    "iter_records",
    "summarize",
    "PolicyDecision",
    "PolicyGate",
    "PolicyLoadError",
    "AbstractionError",
    "Signature",
    "abstract_to_signature",
    "abstract_to_signature_leaky",
    "compute_granularity",
    "derive_shape_features",
    "shape_key_from_dict",
    "to_raw_payload",
]
