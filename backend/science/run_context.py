"""
ScienceRunContext — accumulator passed through canonical pipeline runs.

Separate from AnalysisFrame to keep canonical persistence semantics out of
the core frame. Analyzers write their scalar outputs to AnalysisFrame as
before; this context collects the richer canonical outputs (tags, artifacts,
structured summaries) that go to science_tags and science_artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ScienceTagRecord:
    """A single canonical tag derived during a pipeline run."""
    tag_key: str          # e.g. "room_type.kitchen"
    label: str            # e.g. "Kitchen"
    namespace: str        # e.g. "room_type"
    confidence: Optional[float] = None
    source_analyzer: Optional[str] = None
    attribute_key: Optional[str] = None  # Link to Validation attribute

    def as_dict(self) -> dict:
        return {
            "tag_key": self.tag_key,
            "label": self.label,
            "namespace": self.namespace,
            "confidence": self.confidence,
            "source_analyzer": self.source_analyzer,
            "attribute_key": self.attribute_key,
        }


@dataclass
class ScienceArtifactRecord:
    """Metadata for a canonical artifact to be persisted."""
    artifact_type: str
    meta_json: Optional[dict] = None
    storage_path: Optional[str] = None
    content_type: Optional[str] = None


@dataclass
class ScienceRunContext:
    """Accumulates canonical outputs during a science pipeline run."""
    image_id: int
    science_version: str
    config_fingerprint: str
    tags: list[ScienceTagRecord] = field(default_factory=list)
    artifacts: list[ScienceArtifactRecord] = field(default_factory=list)
    summaries: dict[str, Any] = field(default_factory=dict)

    def add_tag(
        self,
        tag_key: str,
        label: str,
        namespace: str,
        confidence: Optional[float] = None,
        source_analyzer: Optional[str] = None,
        attribute_key: Optional[str] = None,
    ) -> None:
        self.tags.append(ScienceTagRecord(
            tag_key=tag_key,
            label=label,
            namespace=namespace,
            confidence=confidence,
            source_analyzer=source_analyzer,
            attribute_key=attribute_key,
        ))

    def add_artifact(
        self,
        artifact_type: str,
        meta_json: Optional[dict] = None,
        storage_path: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        self.artifacts.append(ScienceArtifactRecord(
            artifact_type=artifact_type,
            meta_json=meta_json,
            storage_path=storage_path,
            content_type=content_type,
        ))

    def tag_keys(self) -> set[str]:
        return {t.tag_key for t in self.tags}
