"""
Instance and Semantic Segmentation Analyzer using OneFormer.

This module provides comprehensive segmentation capabilities for the science pipeline,
identifying and segmenting individual objects and semantic regions within architectural/interior images.

The OneFormer model provides:
- Semantic segmentation (scene understanding)
- Instance segmentation (individual object detection)
- Panoptic segmentation (combined semantic + instance)

Architecture:
- Uses Hugging Face OneFormer model (shi-labs/oneformer_ade20k_swin_tiny)
- Lazy loading pattern to minimize startup overhead
- Integrates with AnalysisFrame for pipeline compatibility
- Stores both counts and coverage metrics as attributes

Fixes vs previous version:
- Added error handling in load_model() with False sentinel to prevent retry loops
- Added null guard before accessing ONEFORMER_MODEL.config.id2label
- Fixed stuff-class count logic in _panoptic_to_metrics (was always 0)
- Moved `import torch` to top-level imports
- Fixed load_model() to check both model AND processor before skipping load
- Separated stuff vs thing counts into distinct dicts for clarity
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from PIL import Image
import torch

from backend.science.core import AnalysisFrame

warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")

# Lazy load globals — None = not yet attempted, False = attempted and failed
ONEFORMER_MODEL = None
ONEFORMER_PROCESSOR = None

logger = logging.getLogger("v3.science.segmentation")

MODEL_NAME = "shi-labs/oneformer_ade20k_swin_tiny"


class SegmentationAnalyzer:
    """
    Segmentation Analyzer using OneFormer.

    Performs semantic and panoptic segmentation on images to:
    1. Identify semantic regions (walls, floors, ceilings, furniture)
    2. Detect individual object instances with pixel-level masks
    3. Compute coverage metrics (what % of image is occupied by each class)
    4. Extract object counts by class
    5. Store segmentation masks for downstream analysis

    All class labels are dynamically determined from model.config.id2label.
    No hardcoded class lists or groupings.

    Attributes computed:
    - segmentation.{class_name}_count: Number of instances of each thing class
    - segmentation.{class_name}_coverage: Fraction of image covered by class
    - segmentation.total_objects: Total number of detected thing instances
    - segmentation.scene_coverage: Total fraction of image with detected objects
    - segmentation.semantic_{class_name}_coverage: Semantic region coverage
    """

    @staticmethod
    def load_model() -> bool:
        """
        Load the OneFormer model and processor (lazy loading).

        Uses shi-labs/oneformer_ade20k_swin_tiny for efficient segmentation.
        The model will be downloaded automatically on first use (~400MB).

        Returns:
            True if model is ready, False if loading failed.

        Alternative models:
        - shi-labs/oneformer_ade20k_swin_large (higher quality, ~1.5GB)
        - shi-labs/oneformer_coco_swin_large (COCO dataset classes)
        """
        global ONEFORMER_MODEL, ONEFORMER_PROCESSOR

        # Already loaded successfully
        if ONEFORMER_MODEL is not None and ONEFORMER_PROCESSOR is not None:
            return True

        # Previously failed — don't retry
        if ONEFORMER_MODEL is False or ONEFORMER_PROCESSOR is False:
            return False

        try:
            from transformers import OneFormerProcessor, OneFormerForUniversalSegmentation

            logger.info("Loading OneFormer model: %s", MODEL_NAME)
            ONEFORMER_PROCESSOR = OneFormerProcessor.from_pretrained(MODEL_NAME)
            ONEFORMER_MODEL = OneFormerForUniversalSegmentation.from_pretrained(MODEL_NAME)
            ONEFORMER_MODEL.eval()
            logger.info("OneFormer model loaded successfully")
            return True

        except Exception:
            logger.exception(
                "SegmentationAnalyzer: failed to load OneFormer model '%s'. "
                "Segmentation will be disabled for this session.",
                MODEL_NAME,
            )
            # Set sentinels so we don't retry on every image
            ONEFORMER_MODEL = False
            ONEFORMER_PROCESSOR = False
            return False

    @staticmethod
    def _semantic_to_metrics(
        semantic_map: np.ndarray, id2label: Dict
    ) -> Tuple[Dict, Dict]:
        """
        Convert semantic segmentation map to counts and coverage metrics.

        Args:
            semantic_map: HxW array of class IDs
            id2label: Mapping from class ID to label name

        Returns:
            counts: Dict of class -> 1 (semantic has one region per class)
            coverages: Dict of class -> coverage fraction
        """
        unique_classes = np.unique(semantic_map)
        total_pixels = semantic_map.size

        counts = {}
        coverages = {}

        for class_id in unique_classes:
            mask = semantic_map == class_id
            pixel_count = int(mask.sum())

            if pixel_count > 100:  # Filter tiny segments
                class_name = id2label.get(int(class_id), f"class_{class_id}")
                counts[class_name] = 1
                coverages[class_name] = pixel_count / total_pixels

        return counts, coverages

    @staticmethod
    def _panoptic_to_metrics(
        panoptic_result: Dict, id2label: Dict
    ) -> Tuple[Dict, Dict, Dict, List]:
        """
        Convert panoptic segmentation to instance/stuff counts and coverage metrics.

        Args:
            panoptic_result: Panoptic segmentation result from processor
            id2label: Mapping from class ID to label name

        Returns:
            thing_counts: Dict of class -> instance count (countable objects)
            stuff_counts: Dict of class -> 1 (uncountable regions like walls/floors)
            coverages: Dict of class -> total coverage fraction (things + stuff)
            masks_data: List of (class_name, mask, confidence, bbox, is_thing)
        """
        seg_map = panoptic_result["segmentation"].numpy()
        segments = panoptic_result["segments_info"]
        total_pixels = seg_map.size

        thing_counts: Dict[str, int] = {}
        stuff_counts: Dict[str, int] = {}
        coverages: Dict[str, float] = {}
        masks_data: List = []

        for segment in segments:
            mask = seg_map == segment["id"]
            pixel_count = int(mask.sum())

            if pixel_count <= 100:  # Filter tiny segments
                continue

            class_name = id2label.get(segment["label_id"], f"class_{segment['label_id']}")
            is_thing = segment.get("isthing", True)
            confidence = segment.get("score", 1.0)
            coverage = pixel_count / total_pixels

            if is_thing:
                # Countable objects: chairs, tables, lamps, etc.
                thing_counts[class_name] = thing_counts.get(class_name, 0) + 1
            else:
                # Uncountable stuff: walls, floors, ceilings, sky, etc.
                # Mark as present (1) rather than counting instances
                stuff_counts[class_name] = 1

            # Accumulate coverage for both things and stuff
            coverages[class_name] = coverages.get(class_name, 0.0) + coverage

            # Compute bounding box from mask
            ys, xs = np.where(mask)
            if len(ys) > 0:
                bbox = [
                    float(xs.min()), float(ys.min()),
                    float(xs.max()), float(ys.max()),
                ]
            else:
                bbox = [0.0, 0.0, 0.0, 0.0]

            masks_data.append(
                (class_name, mask.astype(np.uint8), confidence, bbox, is_thing)
            )

        return thing_counts, stuff_counts, coverages, masks_data

    @staticmethod
    def analyze(
        frame: AnalysisFrame,
        use_semantic: bool = True,
        use_panoptic: bool = True,
    ) -> Dict[str, Any]:
        """
        Run segmentation on the image and extract metrics.

        Args:
            frame: AnalysisFrame containing the image to analyze
            use_semantic: Whether to run semantic segmentation
            use_panoptic: Whether to run panoptic (instance + stuff) segmentation

        Returns:
            Dictionary containing:
            - semantic_counts: Dict of class -> 1 (semantic regions)
            - semantic_coverages: Dict of class -> coverage fraction
            - thing_counts: Dict of class -> instance count
            - stuff_counts: Dict of class -> 1 (present/absent)
            - coverages: Dict of class -> total coverage fraction
            - masks: List of mask data tuples
            - total_instances: Total number of detected thing instances
            - scene_coverage: Total image coverage fraction
            Returns empty dict if model is unavailable.
        """
        if not SegmentationAnalyzer.load_model():
            logger.warning(
                "SegmentationAnalyzer.analyze: model unavailable, skipping image_id=%s",
                frame.image_id,
            )
            return {}

        # Safe to access now — load_model() returned True
        id2label = ONEFORMER_MODEL.config.id2label
        results: Dict[str, Any] = {}

        # Convert numpy array to PIL Image if needed
        if isinstance(frame.original_image, np.ndarray):
            image_pil = Image.fromarray(frame.original_image)
        else:
            image_pil = frame.original_image

        try:
            # --- Semantic segmentation ---
            if use_semantic:
                logger.info("Running semantic segmentation for image_id=%s", frame.image_id)
                semantic_inputs = ONEFORMER_PROCESSOR(
                    images=image_pil,
                    task_inputs=["semantic"],
                    return_tensors="pt",
                )

                with torch.no_grad():
                    semantic_outputs = ONEFORMER_MODEL(**semantic_inputs)

                semantic_map = ONEFORMER_PROCESSOR.post_process_semantic_segmentation(
                    semantic_outputs, target_sizes=[image_pil.size[::-1]]
                )[0]

                semantic_counts, semantic_coverages = SegmentationAnalyzer._semantic_to_metrics(
                    semantic_map.numpy(), id2label
                )

                results["semantic_counts"] = semantic_counts
                results["semantic_coverages"] = semantic_coverages
                results["semantic_map"] = semantic_map.numpy()

                for class_name, coverage in semantic_coverages.items():
                    safe_name = class_name.replace(" ", "_")
                    frame.add_attribute(
                        f"segmentation.semantic_{safe_name}_coverage", coverage
                    )

            # --- Panoptic segmentation ---
            if use_panoptic:
                logger.info("Running panoptic segmentation for image_id=%s", frame.image_id)
                panoptic_inputs = ONEFORMER_PROCESSOR(
                    images=image_pil,
                    task_inputs=["panoptic"],
                    return_tensors="pt",
                )

                with torch.no_grad():
                    panoptic_outputs = ONEFORMER_MODEL(**panoptic_inputs)

                panoptic_result = ONEFORMER_PROCESSOR.post_process_panoptic_segmentation(
                    panoptic_outputs,
                    target_sizes=[image_pil.size[::-1]],
                    label_ids_to_fuse=set(),
                )[0]

                thing_counts, stuff_counts, coverages, masks_data = (
                    SegmentationAnalyzer._panoptic_to_metrics(panoptic_result, id2label)
                )

                seg_map = panoptic_result["segmentation"].numpy()
                combined_mask = (seg_map > 0).astype(np.uint8)
                scene_coverage = float(combined_mask.sum() / combined_mask.size)
                total_instances = sum(thing_counts.values())

                results["thing_counts"] = thing_counts
                results["stuff_counts"] = stuff_counts
                results["coverages"] = coverages
                results["masks"] = masks_data
                results["total_instances"] = total_instances
                results["scene_coverage"] = scene_coverage

                # Store thing counts and all coverages in frame attributes
                for class_name, count in thing_counts.items():
                    safe_name = class_name.replace(" ", "_")
                    frame.add_attribute(f"segmentation.{safe_name}_count", count)

                for class_name, count in stuff_counts.items():
                    safe_name = class_name.replace(" ", "_")
                    frame.add_attribute(f"segmentation.{safe_name}_present", float(count))

                for class_name, coverage in coverages.items():
                    safe_name = class_name.replace(" ", "_")
                    frame.add_attribute(f"segmentation.{safe_name}_coverage", coverage)

                frame.add_attribute("segmentation.total_objects", float(total_instances))
                frame.add_attribute("segmentation.scene_coverage", scene_coverage)

                frame.metadata["segmentation_masks"] = masks_data
                frame.metadata["segmentation_combined_mask"] = combined_mask

                logger.info(
                    "Segmentation complete for image_id=%s: %d things, %d stuff classes, "
                    "%.1f%% scene coverage",
                    frame.image_id,
                    total_instances,
                    len(stuff_counts),
                    scene_coverage * 100,
                )

        except Exception:
            logger.exception(
                "SegmentationAnalyzer.analyze failed for image_id=%s", frame.image_id
            )

        return results

    @staticmethod
    def get_segmentation_overlay(
        frame: AnalysisFrame,
        alpha: float = 0.5,
        show_labels: bool = True,
        show_confidence: bool = True,
        filter_stuff: bool = False,
    ) -> Optional[np.ndarray]:
        """
        Generate a visualization overlay showing segmentation masks.

        Args:
            frame: AnalysisFrame with segmentation results
            alpha: Transparency of mask overlay (0.0-1.0)
            show_labels: Whether to draw class labels
            show_confidence: Whether to show confidence scores
            filter_stuff: Only show thing segments (not semantic stuff)

        Returns:
            RGB image with segmentation overlay, or None if no masks available.
        """
        masks_data = frame.metadata.get("segmentation_masks")
        if not masks_data:
            return None

        import cv2

        overlay = frame.original_image.copy()

        # Deterministic color per class
        np.random.seed(42)
        class_colors: Dict[str, tuple] = {}

        for class_name, mask, confidence, bbox, is_thing in masks_data:
            if filter_stuff and not is_thing:
                continue

            if class_name not in class_colors:
                class_colors[class_name] = tuple(
                    int(c) for c in np.random.randint(100, 255, 3)
                )
            color = class_colors[class_name]

            colored_mask = np.zeros_like(overlay)
            colored_mask[mask > 0] = color
            overlay = cv2.addWeighted(overlay, 1, colored_mask, alpha, 0)

            if is_thing:
                x1, y1, x2, y2 = (int(c) for c in bbox)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)

                if show_labels:
                    label = (
                        f"{class_name} {confidence:.0%}" if show_confidence else class_name
                    )
                    (label_w, label_h), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                    )
                    cv2.rectangle(
                        overlay,
                        (x1, y1 - label_h - baseline - 5),
                        (x1 + label_w + 5, y1),
                        color,
                        -1,
                    )
                    cv2.putText(
                        overlay,
                        label,
                        (x1 + 2, y1 - baseline - 2),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        1,
                    )

        return overlay


def run_segmentation_on_image(image: np.ndarray, image_id: int = -1) -> Dict[str, Any]:
    """
    Convenience function to run segmentation on a single image.

    Args:
        image: RGB numpy array (H, W, 3)
        image_id: Optional image ID for tracking

    Returns:
        Dictionary with segmentation results, or empty dict if model unavailable.
    """
    frame = AnalysisFrame(image_id=image_id, original_image=image)
    return SegmentationAnalyzer.analyze(frame)