"""
Science Pipeline Orchestrator v3.4 (OneFormer Edition).
Integrates DepthAnalyzer and updated SegmentationAnalyzer using OneFormer.
"""
import logging
from typing import Optional
import numpy as np
from sqlalchemy.orm import Session

from backend.database.core import SessionLocal

try:
    import cv2
except ImportError:
    cv2 = None

from backend.models.assets import Image
from backend.models.annotation import Validation
from backend.science.core import AnalysisFrame

# v3.4 Modular Imports
from backend.science.math.color import ColorAnalyzer
from backend.science.math.complexity import ComplexityAnalyzer
from backend.science.math.glcm import TextureAnalyzer
from backend.science.math.fractals import FractalAnalyzer
from backend.science.math.symmetry import SymmetryAnalyzer
from backend.science.math.naturalness import NaturalnessAnalyzer
from backend.science.math.fluency import FluencyAnalyzer
from backend.science.biophilia import BiophiliaAnalyzer
from backend.science.spatial.depth import DepthAnalyzer  # Replaces Isovist
from backend.science.context.cognitive import CognitiveStateAnalyzer
from backend.science.context.affordance import AffordanceAnalyzer
from backend.science.semantics.semantic_tags_vlm import SemanticTagAnalyzer
from backend.science.vision.segmentation import SegmentationAnalyzer  # Now uses OneFormer
from backend.science.vision.materials import MaterialAnalyzer, GeminiMaterialAnalyzer

logger = logging.getLogger(__name__)

SCIENCE_SOURCE = "science_pipeline_v3.4"


class SciencePipelineConfig:
    def __init__(self, enable_all: bool = True):
        self.enable_color = enable_all
        self.enable_complexity = enable_all
        self.enable_texture = enable_all
        self.enable_fractals = enable_all
        self.enable_spatial = enable_all
        # Expensive L2 analyzers are explicit opt-ins.
        self.enable_cognitive = False  # Cognitive VLM (Kaplan-style dimensions)
        self.enable_semantic = False   # Semantic VLM (style.*, room_function.*)
        # OneFormer segmentation — opt-in (runs full semantic+panoptic merge pipeline)
        self.enable_segmentation = False
        self.segmentation_use_semantic = True   # include semantic coverage metrics
        self.segmentation_use_panoptic = True   # include instance metrics + merged masks
        # Cheap heuristic materials pass — enabled by default for canonical runs.
        self.enable_materials_basic = True
        # Gemini Flash material detection (VLM) — opt-in
        self.enable_materials_vlm = False
        # OneFormer + SigLIP2 material identification — opt-in
        # Requires enable_segmentation=True (reuses cached detections from frame.metadata)
        self.enable_clip_materials = False
        # Affordance prediction (environmental activity suitability) — opt-in
        # Prefers Mask2Former COCO panoptic segmentation; falls back to OneFormer.
        self.enable_affordance = False

    @classmethod
    def from_mapping(cls, data: dict | None) -> "SciencePipelineConfig":
        cfg = cls(enable_all=True)
        for key, value in (data or {}).items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        return cfg

    def to_dict(self) -> dict:
        return {
            "enable_color": self.enable_color,
            "enable_complexity": self.enable_complexity,
            "enable_texture": self.enable_texture,
            "enable_fractals": self.enable_fractals,
            "enable_spatial": self.enable_spatial,
            "enable_cognitive": self.enable_cognitive,
            "enable_semantic": self.enable_semantic,
            "enable_segmentation": self.enable_segmentation,
            "segmentation_use_semantic": self.segmentation_use_semantic,
            "segmentation_use_panoptic": self.segmentation_use_panoptic,
            "enable_materials_basic": self.enable_materials_basic,
            "enable_materials_vlm": self.enable_materials_vlm,
            "enable_clip_materials": self.enable_clip_materials,
            "enable_affordance": self.enable_affordance,
        }

class SciencePipeline:
    def __init__(
        self, 
        db: Optional[Session] = None, 
        session: Optional[Session] = None, 
        config: Optional[SciencePipelineConfig] = None
    ):
        self.db = db or session or SessionLocal()
        self._owns_session = (db is None and session is None)
        self.config = config or SciencePipelineConfig()
        
        # Init Analyzers
        self.color = ColorAnalyzer()
        self.complexity = ComplexityAnalyzer()
        self.texture = TextureAnalyzer()
        self.fractals = FractalAnalyzer()
        self.symmetry = SymmetryAnalyzer()
        self.naturalness = NaturalnessAnalyzer()
        self.fluency = FluencyAnalyzer()
        self.biophilia = BiophiliaAnalyzer()
        self.spatial = DepthAnalyzer()  # The new Spatial Engine
        self.cognitive = CognitiveStateAnalyzer()
        self.semantic = SemanticTagAnalyzer()
        self.segmentation = SegmentationAnalyzer()  # OneFormer semantic+panoptic
        self.materials_basic = MaterialAnalyzer()
        self.materials_vlm = GeminiMaterialAnalyzer()
        self.affordance = AffordanceAnalyzer()
        # clip_material is instantiated lazily on first use (heavy model load)
        self._clip_material_pipeline = None

    def process_image(self, image_id: int) -> bool:
        image_record = self.db.query(Image).get(image_id)
        if not image_record:
            logger.warning(f"Image {image_id} not found.")
            return False

        # Load Image
        rgb = self._load_image(image_record)
        if rgb is None:
            return False

        # Init Frame
        frame = AnalysisFrame(image_id=image_id, original_image=rgb)

        try:
            # L0: Physics & Basic Stats
            if self.config.enable_color:
                self.color.analyze(frame)
            if self.config.enable_complexity:
                self.complexity.analyze(frame)
            if self.config.enable_texture:
                self.texture.analyze(frame)
            if self.config.enable_fractals:
                self.fractals.analyze(frame)
            if self.config.enable_spatial:
                self.symmetry.analyze(frame)
                self.naturalness.analyze(frame)
                self.spatial.analyze(frame)  # Runs Depth/Clutter

            # L1: Perceptual (Dependent on L0)
            if self.config.enable_spatial:
                self.fluency.analyze(frame)
                self.biophilia.analyze(frame)

            # L1.5: Vision (OneFormer semantic + panoptic segmentation)
            if self.config.enable_segmentation:
                self.segmentation.analyze(
                    frame,
                    use_semantic=self.config.segmentation_use_semantic,
                    use_panoptic=self.config.segmentation_use_panoptic,
                )

            # L1.55: Materials — cheap heuristic pass, depth-aware when available
            if self.config.enable_materials_basic:
                self.materials_basic.analyze(frame)

            # L1.6: Materials — Gemini Flash VLM
            if self.config.enable_materials_vlm:
                self.materials_vlm.analyze(frame)

            # L1.7: Materials — OneFormer + SigLIP2 (clip_material pipeline)
            # Reuses cached OneFormer detections from L1.5; skips re-inference.
            if self.config.enable_clip_materials:
                if not self.config.enable_segmentation:
                    logger.warning(
                        "enable_clip_materials=True but enable_segmentation=False; "
                        "running segmentation first."
                    )
                    self.segmentation.analyze(frame, use_semantic=True, use_panoptic=True)
                from backend.science.vision.clip_material import MaterialIdentificationPipeline
                if self._clip_material_pipeline is None:
                    self._clip_material_pipeline = MaterialIdentificationPipeline.from_frame_models(frame)
                    if self._clip_material_pipeline is None:
                        self._clip_material_pipeline = MaterialIdentificationPipeline.from_pretrained()
                mat_results = self._clip_material_pipeline.run_from_frame(
                    frame, show_voting_report=False
                )
                # Store top material score per instance as pipeline attributes
                for r in mat_results:
                    safe = r["class_name"].replace(" ", "_")
                    frame.add_attribute(
                        f"material.{safe}_{r['instance_idx']}_top", r["top_score"]
                    )

            # L1.8: Affordance prediction (requires L1.5 segmentation)
            if self.config.enable_affordance:
                self.affordance.analyze(frame)

            # L2: Cognitive (VLM)
            if self.config.enable_cognitive:
                self.cognitive.analyze(frame)

        except Exception:
            logger.exception(f"Analysis failed for image {image_id}")
            return False

        self._save_results(image_id, frame.attributes)
        return True

    def _load_image(self, image_record: Image) -> Optional[np.ndarray]:
        import os
        storage_path = image_record.storage_path or ""

        # HTTP/HTTPS URLs
        if storage_path.startswith("http://") or storage_path.startswith("https://"):
            try:
                import requests
                resp = requests.get(storage_path, timeout=15)
                resp.raise_for_status()
                arr = np.frombuffer(resp.content, dtype=np.uint8)
                bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if bgr is None:
                    return None
                return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            except Exception as exc:
                logger.warning("Could not fetch image URL %s: %s", storage_path, exc)
                return None

        # Local filesystem — try several candidate paths
        candidates = [
            storage_path,
            f"data_store/{storage_path}",
            os.path.join(os.getenv("IMAGE_STORAGE_ROOT", ""), storage_path),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                bgr = cv2.imread(candidate)
                if bgr is not None:
                    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        logger.warning("Image file not found for path: %s", storage_path)
        return None

    def _save_results(self, image_id: int, attributes: dict) -> None:
        from backend.models.attribute import Attribute
        # Fetch valid attribute keys to avoid FK violations
        valid_keys = {
            row[0] for row in self.db.query(Attribute.key).all()
        }
        for key, value in attributes.items():
            if key not in valid_keys:
                logger.debug("Skipping unknown attribute key: %s", key)
                continue
            if value != value:  # NaN check
                value = 0.0
            val = Validation(
                image_id=image_id,
                attribute_key=key,
                value=float(value),
                source=SCIENCE_SOURCE,
            )
            self.db.add(val)
        self.db.commit()

    def process_image_canonical(
        self,
        image_id: int,
        trigger_source: str = "manual_admin",
    ) -> bool:
        """Run canonical science pipeline and persist structured outputs.

        Unlike process_image(), this method:
        - Creates / updates a ScienceRun lifecycle record.
        - Runs affordance and room detection in addition to the core analyzers.
        - Derives canonical tags (affordance, room type, semantic attributes).
        - Persists structured summaries as ScienceArtifacts.
        - Persists canonical tags to ScienceTags.
        - Returns True on success, False on failure.
        """
        from backend.science.run_context import ScienceRunContext
        from backend.science.tag_derivation import derive_all_tags
        from backend.services.science_runs import (
            ACTIVE_SCIENCE_VERSION,
            get_config_fingerprint,
            ensure_science_run,
            mark_run_started,
            mark_run_completed,
            mark_run_failed,
            persist_science_tags,
            persist_science_artifact,
        )

        # ── 1. Ensure a run record exists ──────────────────────────────────
        run = ensure_science_run(self.db, image_id, trigger_source=trigger_source)
        if run.status == "COMPLETED":
            logger.info("Image %d already has a completed canonical run.", image_id)
            return True

        mark_run_started(self.db, run.id)

        try:
            image_record = self.db.query(Image).get(image_id)
            if not image_record:
                mark_run_failed(self.db, run.id, f"Image {image_id} not found")
                return False

            rgb = self._load_image(image_record)
            if rgb is None:
                mark_run_failed(self.db, run.id, "Could not load image file")
                return False

            frame = AnalysisFrame(image_id=image_id, original_image=rgb)

            # ── 2. Core analyzers (same as process_image) ─────────────────
            if self.config.enable_color:
                self.color.analyze(frame)
            if self.config.enable_complexity:
                self.complexity.analyze(frame)
            if self.config.enable_texture:
                self.texture.analyze(frame)
            if self.config.enable_fractals:
                self.fractals.analyze(frame)
            if self.config.enable_spatial:
                self.symmetry.analyze(frame)
                self.naturalness.analyze(frame)
                self.spatial.analyze(frame)
                self.fluency.analyze(frame)
                self.biophilia.analyze(frame)

            if self.config.enable_segmentation:
                self.segmentation.analyze(
                    frame,
                    use_semantic=self.config.segmentation_use_semantic,
                    use_panoptic=self.config.segmentation_use_panoptic,
                )

            if self.config.enable_materials_basic:
                self.materials_basic.analyze(frame)

            if self.config.enable_materials_vlm:
                self.materials_vlm.analyze(frame)

            if self.config.enable_cognitive:
                self.cognitive.analyze(frame)

            if self.config.enable_semantic:
                self.semantic.analyze(frame)

            # ── 3. Canonical: affordance ───────────────────────────────────
            affordance_summary: dict | None = None
            self.affordance.analyze(frame)
            if any(f"affordance.{aff}" in frame.attributes for aff in ["L059", "L079", "L091", "L130", "L141"]):
                from backend.science.context.affordance import AFFORDANCE_IDS, AFFORDANCE_NAMES
                scores = {
                    aff: frame.attributes.get(f"affordance.{aff}", 0.0)
                    for aff in AFFORDANCE_IDS
                    if f"affordance.{aff}" in frame.attributes
                }
                affordance_summary = {
                    "scores": {k: round(float(v), 3) for k, v in scores.items()},
                    "method": frame.metadata.get("affordance.method", "unknown"),
                    "n_segments": frame.metadata.get("affordance.n_segments", 0),
                    "segment_classes": frame.metadata.get("affordance.segment_classes", []),
                    "segmentation_backend": frame.metadata.get("affordance.segmentation_backend", "unknown"),
                }

            # ── 4. Canonical: room detection ───────────────────────────────
            room_summary: dict | None = None
            try:
                from backend.science.vision.room_detection import RoomDetectionAnalyzer
                room_result = RoomDetectionAnalyzer.analyze(frame, top_k=5)
                if room_result:
                    # top_coarse / top_fine are dicts: {"label": ..., "probability": ...}
                    top_coarse = room_result.get("top_coarse")
                    top_fine = room_result.get("top_fine")
                    room_summary = {
                        "top_coarse": (
                            [top_coarse["label"], float(top_coarse["probability"])]
                            if top_coarse else None
                        ),
                        "top_fine": (
                            [top_fine["label"], float(top_fine["probability"])]
                            if top_fine else None
                        ),
                        "coarse_probs": {
                            k: round(float(v), 4)
                            for k, v in room_result.get("room_type_coarse", {}).items()
                        },
                        "fine_predictions": [
                            [label, round(float(prob), 4)]
                            for label, prob in room_result.get("room_type_fine", [])
                        ],
                    }
            except Exception as exc:
                logger.info("Room detection skipped: %s", exc)

            # ── 5. Persist scalar attributes to Validation ─────────────────
            self._save_results(image_id, frame.attributes)

            # ── 6. Build and persist canonical artifacts ───────────────────
            ctx = ScienceRunContext(
                image_id=image_id,
                science_version=ACTIVE_SCIENCE_VERSION,
                config_fingerprint=get_config_fingerprint(self.config.to_dict()),
            )

            materials_summary = (
                frame.metadata.get("material_detection")
                if isinstance(frame.metadata.get("material_detection"), dict)
                and not frame.metadata.get("material_detection", {}).get("stub")
                else frame.metadata.get("material_detection_basic")
            )

            if affordance_summary:
                persist_science_artifact(
                    self.db,
                    run_id=run.id,
                    image_id=image_id,
                    artifact_type="affordance_json",
                    meta_json=affordance_summary,
                    content_type="application/json",
                )

            if room_summary:
                persist_science_artifact(
                    self.db,
                    run_id=run.id,
                    image_id=image_id,
                    artifact_type="room_json",
                    meta_json=room_summary,
                    content_type="application/json",
                )

            if materials_summary:
                persist_science_artifact(
                    self.db,
                    run_id=run.id,
                    image_id=image_id,
                    artifact_type="materials_json",
                    meta_json=materials_summary,
                    content_type="application/json",
                )

            # ── 7. Derive and persist canonical tags ───────────────────────
            derive_all_tags(
                attributes=frame.attributes,
                affordance_summary=affordance_summary,
                room_summary=room_summary,
                segmentation_summary=None,  # segmentation off by default
                materials_summary=materials_summary,
                ctx=ctx,
            )

            persist_science_tags(
                self.db,
                run_id=run.id,
                image_id=image_id,
                tags=[t.as_dict() for t in ctx.tags],
            )

            mark_run_completed(self.db, run.id)
            logger.info(
                "Canonical run %d complete for image %d: %d tags, %d artifacts.",
                run.id, image_id, len(ctx.tags), len(ctx.artifacts),
            )
            return True

        except Exception as exc:
            logger.exception("Canonical pipeline failed for image %d", image_id)
            mark_run_failed(self.db, run.id, str(exc))
            return False
