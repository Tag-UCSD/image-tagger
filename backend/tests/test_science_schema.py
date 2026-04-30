"""
Schema-level tests for the Phase 1 trust envelope (Task A-7).

These tests are deliberately pure-Pydantic: no database, no app boot, no
HTTP client. They validate the *shape* of the contract — that every
feature in `SciencePayload` is wrapped in a six-field `TrustEnvelope`,
that the legacy fallback marks unregistered features as "untested", and
that a payload missing `evaluation_status` fails validation rather than
silently shipping an undocumented field.

The pytest selector in the Phase 1 acceptance criteria is::

    pytest backend/tests/test_science_schema.py \\
        -k "trust_envelope or legacy_feature_untested or missing_evaluation_status" -v

Test names below are chosen so each branch of that ``-k`` filter matches.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.science import AffordancePrediction, SciencePayload
from backend.science.features_registry import get_trust_envelope
from backend.science.trust import TrustEnvelope


_REQUIRED_ENVELOPE_FIELDS = {
    "value",
    "model_id",
    "evaluation_status",
    "confidence_interval_95",
    "n_training",
    "notes",
}


def _sample_envelope(
    value: float = 0.65,
    *,
    status: str = "proxy_validated",
    model_id: str = "feature_symmetry_v1",
) -> TrustEnvelope:
    return TrustEnvelope(
        value=value,
        model_id=model_id,
        evaluation_status=status,  # type: ignore[arg-type]
        confidence_interval_95=(0.6, 0.7),
        n_training=120,
        notes="proxy validated against internal reference set",
    )


# ─── trust_envelope serialization shape ───────────────────────────────────


def test_trust_envelope_serialization_has_all_six_required_fields():
    """Every feature in `SciencePayload.features` must serialize as an
    object containing exactly the six envelope fields. The frontend's
    trust-badge renderer keys off these names."""
    payload = SciencePayload(
        run_id=42,
        run_status="completed",
        features={
            "fluency.symmetry_score_horizontal": _sample_envelope(),
            "light.daylight_ratio": _sample_envelope(
                value=0.84,
                status="proxy_validated",
                model_id="feature_daylight_ratio_v1",
            ),
        },
    )

    data = payload.model_dump()

    for feature_key, feature_obj in data["features"].items():
        assert (
            set(feature_obj.keys()) == _REQUIRED_ENVELOPE_FIELDS
        ), f"feature {feature_key!r} missing envelope fields"
        assert isinstance(feature_obj["model_id"], str)
        assert feature_obj["evaluation_status"] in {
            "validated",
            "proxy_validated",
            "untested",
        }
        assert isinstance(feature_obj["n_training"], int)
        assert isinstance(feature_obj["notes"], str)


def test_trust_envelope_payload_has_no_separate_confidence_map():
    """Per the contract, `SciencePayload` must NOT expose a top-level
    `confidence` map for features — the envelope is the confidence
    record. `extra="forbid"` enforces this so a future regression that
    re-adds a parallel map fails schema validation."""
    payload = SciencePayload(
        run_id=1,
        run_status="completed",
        features={"x": _sample_envelope()},
    )
    data = payload.model_dump()
    assert "confidence" not in data, (
        "SciencePayload must not expose a top-level `confidence` map; "
        "the trust envelope on each feature is the confidence record."
    )

    with pytest.raises(ValidationError) as excinfo:
        SciencePayload.model_validate(
            {
                "run_id": 1,
                "run_status": "completed",
                "features": {"x": _sample_envelope().model_dump()},
                "affordances": [],
                "confidence": {"x": 0.5},
            }
        )
    assert "extra" in str(excinfo.value).lower() or "forbid" in str(
        excinfo.value
    ).lower()


def test_trust_envelope_affordance_prediction_uses_same_envelope_shape():
    """`AffordancePrediction.confidence` must be a `TrustEnvelope` with
    the same six fields, scoped to the affordance score."""
    aff = AffordancePrediction(
        key="L059",
        label="Sleep Suitability",
        score=5.8,
        confidence=TrustEnvelope(
            value=5.8,
            model_id="affordance_L059_lgbm_v1",
            evaluation_status="validated",
            confidence_interval_95=(5.2, 6.1),
            n_training=1523,
            notes="held-out test R²=0.71; see ML_EVALUATION.md#L059",
        ),
    )
    confidence_obj = aff.model_dump()["confidence"]
    assert set(confidence_obj.keys()) == _REQUIRED_ENVELOPE_FIELDS


# ─── legacy_feature_untested fallback ─────────────────────────────────────


def test_legacy_feature_untested_when_key_not_in_registry():
    """A feature key that has no registry entry must round-trip through
    `get_trust_envelope` as `evaluation_status == "untested"` so the UI
    is never lied to about provenance we don't have."""
    env = get_trust_envelope("phase1.unknown_legacy_feature_v999", 0.42)

    assert env.evaluation_status == "untested"
    assert env.value == pytest.approx(0.42)
    assert env.confidence_interval_95 is None
    assert env.n_training == 0
    assert env.model_id, "legacy envelope must carry a non-empty model_id"
    assert env.notes, "legacy envelope must carry a non-empty notes string"


def test_legacy_feature_untested_serializes_inside_science_payload():
    """End-to-end: an unregistered feature key flowing through the
    response schema serializes with `evaluation_status == "untested"`."""
    legacy_env = get_trust_envelope("phase1.another_unknown_feature", 0.123)
    payload = SciencePayload(
        run_id=7,
        run_status="completed",
        features={"phase1.another_unknown_feature": legacy_env},
    )
    serialized = payload.model_dump()["features"][
        "phase1.another_unknown_feature"
    ]
    assert serialized["evaluation_status"] == "untested"
    assert serialized["confidence_interval_95"] is None


# ─── missing_evaluation_status fails schema validation ───────────────────


def test_missing_evaluation_status_fails_envelope_validation():
    """A trust-envelope-shaped dict missing the `evaluation_status` field
    must fail Pydantic validation; we never want a silent default."""
    bad = {
        "value": 0.5,
        "model_id": "phase1.test_v1",
        "n_training": 0,
        "notes": "",
    }
    with pytest.raises(ValidationError) as excinfo:
        TrustEnvelope.model_validate(bad)
    assert "evaluation_status" in str(excinfo.value)


def test_missing_evaluation_status_fails_inside_science_payload():
    """The same constraint must hold when the bad envelope is nested
    inside a `SciencePayload`. Catching this at the response-assembly
    boundary is the whole point of A-7."""
    bad_envelope = {
        "value": 0.5,
        "model_id": "phase1.test_v1",
        "n_training": 0,
        "notes": "",
    }
    bad_payload = {
        "run_id": 1,
        "run_status": "completed",
        "features": {"foo.bar": bad_envelope},
        "affordances": [],
    }
    with pytest.raises(ValidationError) as excinfo:
        SciencePayload.model_validate(bad_payload)
    assert "evaluation_status" in str(excinfo.value)
