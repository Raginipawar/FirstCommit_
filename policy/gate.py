"""
The Cedar policy gate: the one place a signature is allowed to cross from
"private to this site" to "eligible for the shared pattern store".

Person 3's orchestration loop should call `PolicyGate.evaluate_share_request`
exactly once per candidate signature, right before writing to OpenSearch, and
only forward payloads whose decision is ALLOW. Every call is logged
regardless of outcome — see decision_log.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cedarpy

from .decision_log import DecisionLogger
from .signature import Signature

_POLICY_DIR = Path(__file__).parent / "policies"
_DEFAULT_POLICY_FILE = _POLICY_DIR / "sharing.cedar"
_DEFAULT_SCHEMA_FILE = _POLICY_DIR / "sharing.cedarschema"
_DEFAULT_LOG_FILE = Path(__file__).parent / "logs" / "decisions.jsonl"

_SITE_ENTITY_TYPE = "Site"
_PAYLOAD_ENTITY_TYPE = "Payload"
_ACTION_ID = "share"


class PolicyLoadError(RuntimeError):
    """Raised when the Cedar policy set or schema fails to load or validate."""


@dataclass(frozen=True)
class PolicyDecision:
    """The outcome of one authorization check, ready to log and to act on."""

    allowed: bool
    decision: str  # "Allow" or "Deny"
    site_id: str
    resource_id: str
    kind: str
    granularity: int
    matched_policies: tuple[str, ...]
    errors: tuple[str, ...]
    reasons: tuple[str, ...]
    checked_at: str
    payload_attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked_at": self.checked_at,
            "decision": self.decision,
            "allowed": self.allowed,
            "site_id": self.site_id,
            "resource_id": self.resource_id,
            "kind": self.kind,
            "granularity": self.granularity,
            "matched_policies": list(self.matched_policies),
            "errors": list(self.errors),
            "reasons": list(self.reasons),
            "payload_attrs": self.payload_attrs,
        }

    def __str__(self) -> str:  # pragma: no cover - console formatting only
        tag = "ALLOW" if self.allowed else "DENY "
        matched = ",".join(self.matched_policies) or "none"
        return (
            f"[{tag}] {self.site_id} -> {self.resource_id} "
            f"(kind={self.kind}, granularity={self.granularity}) matched={matched}"
        )


def _explain(decision: PolicyDecision) -> str:
    """Human-readable reason, derived from which flags/kind actually triggered it."""
    attrs = decision.payload_attrs
    if decision.allowed:
        return "signature is clean and within the granularity threshold"

    leaked = [k for k in ("has_meter_id", "has_consumer_id", "has_raw_series",
                          "has_household_field", "has_location") if attrs.get(k)]
    if leaked:
        return f"identifying field(s) present: {', '.join(leaked)}"
    if attrs.get("kind") != "signature":
        return f"payload kind is {attrs.get('kind')!r}, not an abstracted signature"
    return f"granularity {decision.granularity} exceeds the sharing threshold"


class PolicyGate:
    """Loads the TRIPWIRE sharing policy once and evaluates share requests against it."""

    def __init__(
        self,
        policy_file: str | Path = _DEFAULT_POLICY_FILE,
        schema_file: str | Path = _DEFAULT_SCHEMA_FILE,
        log_file: str | Path = _DEFAULT_LOG_FILE,
    ) -> None:
        policy_text = Path(policy_file).read_text(encoding="utf-8")
        schema_text = Path(schema_file).read_text(encoding="utf-8")

        validation = cedarpy.validate_policies(policy_text, schema_text)
        if not validation.validation_passed:
            raise PolicyLoadError(f"sharing.cedar failed schema validation: {validation.errors}")

        self._schema = cedarpy.Schema.from_str(schema_text)
        self._policies = cedarpy.PolicySet.from_str(policy_text)
        self._logger = DecisionLogger(log_file)

    def evaluate_share_request(self, site_id: str, signature: Signature) -> PolicyDecision:
        """Ask Cedar whether `site_id` may share this signature (or raw payload).

        Always logs the decision before returning it, so a denied request is
        just as inspectable afterwards as a permitted one.
        """
        payload_attrs = signature.to_payload_attrs()

        request = {
            "principal": {"type": _SITE_ENTITY_TYPE, "id": site_id},
            "action": {"type": "Action", "id": _ACTION_ID},
            "resource": {"type": _PAYLOAD_ENTITY_TYPE, "id": signature.signature_id},
            "context": {},
        }
        entities = [
            {"uid": {"type": _SITE_ENTITY_TYPE, "id": site_id}, "attrs": {}, "parents": []},
            {
                "uid": {"type": _PAYLOAD_ENTITY_TYPE, "id": signature.signature_id},
                "attrs": payload_attrs,
                "parents": [],
            },
        ]

        result = cedarpy.is_authorized(request, self._policies, entities, schema=self._schema)

        decision = PolicyDecision(
            allowed=bool(result.allowed),
            decision=result.decision.name,
            site_id=site_id,
            resource_id=signature.signature_id,
            kind=payload_attrs["kind"],
            granularity=payload_attrs["granularity"],
            matched_policies=tuple(result.diagnostics.reasons),
            errors=tuple(str(e) for e in result.diagnostics.errors),
            reasons=(),
            checked_at=datetime.now(timezone.utc).isoformat(),
            payload_attrs=payload_attrs,
        )
        decision = _with_explanation(decision)

        self._logger.log(decision)
        return decision

    @property
    def log_path(self) -> Path:
        return self._logger.log_path

    def read_decisions(self) -> list[dict[str, Any]]:
        """Every decision this gate has logged so far, oldest first."""
        return self._logger.read_all()


def _with_explanation(decision: PolicyDecision) -> PolicyDecision:
    explanation = _explain(decision)
    return PolicyDecision(
        allowed=decision.allowed,
        decision=decision.decision,
        site_id=decision.site_id,
        resource_id=decision.resource_id,
        kind=decision.kind,
        granularity=decision.granularity,
        matched_policies=decision.matched_policies,
        errors=decision.errors,
        reasons=(explanation,),
        checked_at=decision.checked_at,
        payload_attrs=decision.payload_attrs,
    )
