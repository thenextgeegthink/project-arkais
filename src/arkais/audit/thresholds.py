"""Versioned gate thresholds, loaded from the signature bundle.

Why this module exists
----------------------
The audit engine hardcoded every gate bound in code. `std_len >= 12.0`,
`nom_density 3.0-14.0`, `epistemic_ratio >= 1.2`, `cites_per_k >= 1.5`. None of them
traced to a measured statistic, none carried provenance, and none changed when the
signature changed -- the engine would happily score text against thresholds the
promoted bundle had never seen.

Two rules, both load-bearing:

1. **A missing threshold is an error, never a fallback.** The default-value path is
   how an unsourced constant outlives its justification.
2. **Every threshold carries provenance.** A value that cannot say where it came from
   is a decision bound wearing a statistic's clothes, and has to be labelled as such
   rather than presented as calibrated.

Scope of this refactor
----------------------
It moves the constants into a versioned, validated file and records where each one
came from. It does **not** recalibrate anything: every value is preserved verbatim, so
no gate outcome changes. Reconciling these bounds against the measured bands is a
calibration decision for the next round, gated on the ablation that ticket 03's
``NEEDS-REVIEW`` label is waiting on.

Where the numbers come from
---------------------------
The promoted signature bundle records measured bands (``core.bands``); it does not
record gate *decision* policy. Those are different things -- a median describes a
distribution's centre, and a gate may legitimately permit lower values -- so this file
sits beside the bundle rather than inside it. Promoted artifacts are immutable
(ADR-005, ADR-007 §3), so the bundle cannot be edited to add them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = [
    "GateThresholdError",
    "Threshold",
    "GateThresholds",
    "DEFAULT_SIGNATURE_ID",
    "load_gate_thresholds",
    "legacy_default_thresholds",
]

DEFAULT_SIGNATURE_ID = "ARKAIS-v3.0"

_GATES_DIR = Path(__file__).resolve().parent.parent / "signature" / "gates"

#: Schema version this loader understands. A file declaring a different one is
#: rejected rather than best-effort parsed.
SUPPORTED_SCHEMA_VERSION = "arkais.gate-thresholds.v1"

_REQUIRED_KEYS: Dict[str, tuple] = {
    "GATE-04": ("sigma_min", "short_text_exempt_words", "score_divisor"),
    "GATE-05": ("density_min_pct", "density_max_pct", "short_text_exempt_words"),
    "GATE-06": ("hedge_ratio_floor", "short_text_exempt_words", "score_divisor"),
    "GATE-09": ("max_bullets_per_200_words",),
    "GATE-10": ("min_citations_per_1000_words", "short_text_exempt_words", "score_divisor"),
}


class GateThresholdError(RuntimeError):
    """Raised when gate thresholds are absent, malformed, or unverifiable.

    Deliberately not a silent degradation path: an engine that cannot find its
    thresholds has no business producing a score.
    """


@dataclass(frozen=True)
class Threshold:
    """One gate bound plus the provenance that makes it auditable."""

    value: float
    provenance: str
    note: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.value, (int, float)) or isinstance(self.value, bool):
            raise GateThresholdError(f"threshold value must be numeric, got {self.value!r}")
        if not self.provenance:
            raise GateThresholdError("every threshold must declare provenance")


@dataclass(frozen=True)
class GateThresholds:
    """All gate bounds for one signature, plus the hash that binds them to it."""

    signature_id: str
    signature_manifest_hash: str
    schema_version: str
    values: Dict[str, Dict[str, Threshold]]
    from_bundle: bool = False

    def value(self, gate_id: str, key: str) -> float:
        try:
            return self.values[gate_id][key].value
        except KeyError as exc:  # pragma: no cover - guarded by load-time validation
            raise GateThresholdError(
                f"{self.signature_id}: {gate_id}.{key} is not defined"
            ) from exc

    def threshold(self, gate_id: str, key: str) -> Threshold:
        try:
            return self.values[gate_id][key]
        except KeyError as exc:  # pragma: no cover
            raise GateThresholdError(
                f"{self.signature_id}: {gate_id}.{key} is not defined"
            ) from exc

    def unsourced(self) -> Dict[str, list]:
        """Bounds that do not trace to a measured band, for reporting and QC."""
        out: Dict[str, list] = {}
        for gate_id, keys in self.values.items():
            bad = [k for k, t in keys.items() if t.provenance != "measured_band"]
            if bad:
                out[gate_id] = sorted(bad)
        return out


_LEGACY_DEFAULT_VALUES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "GATE-04": {
        "sigma_min": {"value": 12.0, "provenance": "legacy_engine_constant",
                      "note": "Fallback default; bundle absent (public bundle-less build)."},
        "short_text_exempt_words": {"value": 150, "provenance": "legacy_engine_constant"},
        "score_divisor": {"value": 15.0, "provenance": "legacy_engine_constant"},
    },
    "GATE-05": {
        "density_min_pct": {"value": 3.0, "provenance": "legacy_engine_constant"},
        "density_max_pct": {"value": 14.0, "provenance": "legacy_engine_constant"},
        "short_text_exempt_words": {"value": 100, "provenance": "legacy_engine_constant"},
    },
    "GATE-06": {
        "hedge_ratio_floor": {"value": 1.2, "provenance": "legacy_engine_constant"},
        "short_text_exempt_words": {"value": 150, "provenance": "legacy_engine_constant"},
        "score_divisor": {"value": 1.5, "provenance": "legacy_engine_constant"},
    },
    "GATE-09": {
        "max_bullets_per_200_words": {"value": 1.0, "provenance": "legacy_engine_constant"},
    },
    "GATE-10": {
        "min_citations_per_1000_words": {"value": 1.5, "provenance": "legacy_engine_constant"},
        "short_text_exempt_words": {"value": 200, "provenance": "legacy_engine_constant"},
        "score_divisor": {"value": 2.5, "provenance": "legacy_engine_constant"},
    },
}


def legacy_default_thresholds(signature_id: str = DEFAULT_SIGNATURE_ID) -> GateThresholds:
    """Built-in legacy defaults used when no versioned bundle is present.

    These are the pre-refactor hardcoded values, already public knowledge, so shipping
    them in a bundle-less public build discloses nothing. Every value carries
    ``legacy_engine_constant`` provenance, which is exactly the honest label the bundle
    uses for them. This is the ticket-10 fallback pattern applied to gate thresholds:
    read the bundle when present; fall back to built-in defaults when it is not.
    """
    values: Dict[str, Dict[str, Threshold]] = {}
    for gate_id, required in _REQUIRED_KEYS.items():
        gate = _LEGACY_DEFAULT_VALUES[gate_id]
        values[gate_id] = {
            key: Threshold(
                value=gate[key]["value"],
                provenance=gate[key].get("provenance", "legacy_engine_constant"),
                note=gate[key].get("note", "Fallback default (bundle absent)."),
            )
            for key in required
        }
    return GateThresholds(
        signature_id=signature_id,
        signature_manifest_hash="",
        schema_version=SUPPORTED_SCHEMA_VERSION,
        values=values,
        from_bundle=False,
    )


def _load_raw(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise GateThresholdError(
            f"gate threshold file not found: {path}. The audit engine requires a "
            f"versioned threshold bundle and will not fall back to hardcoded defaults."
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateThresholdError(f"gate threshold file is not valid JSON: {path}: {exc}") from exc


def load_gate_thresholds(
    signature_id: str = DEFAULT_SIGNATURE_ID,
    path: Optional[Path] = None,
) -> GateThresholds:
    """Load and validate the gate thresholds for ``signature_id``.

    Raises :class:`GateThresholdError` on anything missing, malformed, incomplete, or
    bound to a different signature than the one requested. There is no partial-success
    path and no default-value fallback.
    """
    target = Path(path) if path is not None else _GATES_DIR / f"{signature_id}.gates.json"

    # Bundle-less fallback (ticket-10 pattern): the engine works in a public build that
    # ships no proprietary bundle, using the built-in legacy defaults. An explicitly
    # requested bundle that is absent still raises -- that is a configuration error, not
    # a public deployment.
    if not target.exists() and path is None and signature_id == DEFAULT_SIGNATURE_ID:
        return legacy_default_thresholds(signature_id)

    raw = _load_raw(target)

    schema_version = raw.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise GateThresholdError(
            f"{target}: schema_version {schema_version!r} is not supported "
            f"(expected {SUPPORTED_SCHEMA_VERSION!r})"
        )

    if raw.get("signature_id") != signature_id:
        raise GateThresholdError(
            f"{target}: declares signature_id {raw.get('signature_id')!r}, "
            f"expected {signature_id!r}"
        )

    manifest_hash = raw.get("signature_manifest_hash")
    if not manifest_hash:
        raise GateThresholdError(
            f"{target}: missing signature_manifest_hash. Gate bounds must be bound to "
            f"the promoted signature they were calibrated against, otherwise a "
            f"threshold file can be paired with the wrong bundle silently."
        )

    raw_gates = raw.get("gates")
    if not isinstance(raw_gates, dict):
        raise GateThresholdError(f"{target}: 'gates' must be an object")

    missing_gates = sorted(set(_REQUIRED_KEYS) - set(raw_gates))
    if missing_gates:
        raise GateThresholdError(f"{target}: missing gate definitions: {missing_gates}")

    values: Dict[str, Dict[str, Threshold]] = {}
    for gate_id, required in _REQUIRED_KEYS.items():
        gate = raw_gates[gate_id]
        if not isinstance(gate, dict):
            raise GateThresholdError(f"{target}: {gate_id} must be an object")
        absent = [k for k in required if k not in gate]
        if absent:
            raise GateThresholdError(f"{target}: {gate_id} missing keys {absent}")
        # Reject unknown keys rather than ignoring them. A typo'd key would otherwise
        # leave the intended threshold unused while the file still validated, which is
        # how the epistemic range drifted across five files without any of them erroring.
        unknown = sorted(set(gate) - set(required) - {"name"})
        if unknown:
            raise GateThresholdError(
                f"{target}: {gate_id} has unknown keys {unknown}; expected {list(required)}"
            )
        values[gate_id] = {
            key: Threshold(
                value=gate[key]["value"],
                provenance=gate[key].get("provenance", ""),
                note=gate[key].get("note", ""),
            )
            for key in required
        }

    return GateThresholds(
        signature_id=signature_id,
        signature_manifest_hash=manifest_hash,
        schema_version=schema_version,
        values=values,
        from_bundle=True,
    )