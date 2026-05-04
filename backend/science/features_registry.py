"""
Canonical feature registry for Image Tagger.

This module loads the forward-looking CNfA feature/attribute list from
a JSONL file produced from David's v7 and Goldilocks spreadsheets.

It is intentionally file-backed (not DB-backed) for now, so that the
Feature Navigator GUI can browse the ontology without schema churn.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.science.trust import (
    DEFAULT_UNTESTED_NOTES,
    LEGACY_MODEL_ID,
    EvaluationStatus,
    TrustEnvelope,
    untested_envelope,
)


FEATURES_PATH = Path(__file__).with_name("features_canonical.jsonl")


@dataclass
class FeatureDefinition:
    key: str
    category: str
    tier: str
    label: str
    status: str = "active"
    type: str = "continuous"  # binary | ordinal | categorical | continuous
    group: Optional[str] = None
    description: Optional[str] = None
    cfa_relevance: Optional[str] = None
    source: Optional[str] = None
    scale: Optional[Dict[str, Any]] = None
    methods: Optional[List[Dict[str, Any]]] = None

    # Trust-envelope metadata (Phase 1, Task A-7). Optional in the JSONL
    # because the canonical feature file predates the trust contract;
    # entries without these fields fall back to "untested" so the UI
    # renders an honest warning badge rather than a missing one.
    evaluation_status: EvaluationStatus = "untested"
    model_id: Optional[str] = None
    n_training: int = 0
    confidence_interval_95: Optional[Tuple[float, float]] = None
    trust_notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureDefinition":
        ci = data.get("confidence_interval_95")
        if isinstance(ci, list) and len(ci) == 2:
            ci_tuple: Optional[Tuple[float, float]] = (float(ci[0]), float(ci[1]))
        elif isinstance(ci, tuple) and len(ci) == 2:
            ci_tuple = (float(ci[0]), float(ci[1]))
        else:
            ci_tuple = None

        status_raw = data.get("evaluation_status", "untested")
        if status_raw not in ("validated", "proxy_validated", "untested"):
            status_raw = "untested"

        return cls(
            key=data.get("key", ""),
            category=data.get("category", "unknown"),
            tier=data.get("tier", "L4"),
            label=data.get("label", data.get("key", "")),
            status=data.get("status", "active"),
            type=data.get("type", "continuous"),
            group=data.get("group"),
            description=data.get("description"),
            cfa_relevance=data.get("cfa_relevance"),
            source=data.get("source"),
            scale=data.get("scale"),
            methods=data.get("methods"),
            evaluation_status=status_raw,  # type: ignore[arg-type]
            model_id=data.get("model_id"),
            n_training=int(data.get("n_training", 0) or 0),
            confidence_interval_95=ci_tuple,
            trust_notes=data.get("trust_notes"),
        )


@lru_cache(maxsize=1)
def load_features() -> List[FeatureDefinition]:
    feats: List[FeatureDefinition] = []
    if not FEATURES_PATH.exists():
        return feats
    import json

    with FEATURES_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            feats.append(FeatureDefinition.from_dict(data))
    return feats


def list_features(
    tier: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
) -> List[FeatureDefinition]:
    feats = load_features()
    result: List[FeatureDefinition] = []
    for feat in feats:
        if tier and feat.tier != tier:
            continue
        if category and feat.category != category:
            continue
        if status and feat.status != status:
            continue
        result.append(feat)
    return result


def get_feature(key: str) -> Optional[FeatureDefinition]:
    for feat in load_features():
        if feat.key == key:
            return feat
    return None


def get_trust_envelope(key: str, value: float) -> TrustEnvelope:
    """Wrap a feature output in its registry-defined trust envelope.

    Falls back to an "untested" envelope when the feature has no registry
    entry or has not yet been promoted out of the default. This is the
    single seam where pipeline outputs become trust-stamped, per Task A-7.
    """
    feat = get_feature(key)
    if feat is None:
        return untested_envelope(
            float(value),
            model_id=LEGACY_MODEL_ID,
            notes=DEFAULT_UNTESTED_NOTES,
        )

    if feat.evaluation_status == "untested":
        return untested_envelope(
            float(value),
            model_id=feat.model_id or LEGACY_MODEL_ID,
            notes=feat.trust_notes or DEFAULT_UNTESTED_NOTES,
        )

    return TrustEnvelope(
        value=float(value),
        model_id=feat.model_id or f"feature_{key.replace('.', '_')}_v0",
        evaluation_status=feat.evaluation_status,
        confidence_interval_95=feat.confidence_interval_95,
        n_training=feat.n_training,
        notes=feat.trust_notes or "",
    )
