"""
Mask2Former panoptic segmentation for affordance inference.

This module mirrors the research pipeline's segmentation family:
facebook/mask2former-swin-large-coco-panoptic

It intentionally stays separate from the app's existing OneFormer analyzer so
the Explorer debug/UI surfaces remain unchanged while affordance scoring can use
the COCO-native segments that the LightGBM models were trained on.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
from PIL import Image


logger = logging.getLogger("v3.science.mask2former")

MODEL_ID = "facebook/mask2former-swin-large-coco-panoptic"
PANOPTIC_THING_ID_CUTOFF = 80

_PROCESSOR = None
_MODEL = None
_DEVICE = None
_ID2LABEL = None


def _resolve_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _preferred_dtype(device: torch.device) -> torch.dtype:
    return torch.float16 if device.type == "cuda" else torch.float32


def load_model() -> Tuple[Any, Any, torch.device, Dict[int, str]]:
    global _PROCESSOR, _MODEL, _DEVICE, _ID2LABEL
    if _MODEL is not None:
        return _PROCESSOR, _MODEL, _DEVICE, _ID2LABEL

    from transformers import Mask2FormerForUniversalSegmentation, Mask2FormerImageProcessor

    device = _resolve_device()
    dtype = _preferred_dtype(device)
    processor = Mask2FormerImageProcessor.from_pretrained(MODEL_ID)
    try:
        model = Mask2FormerForUniversalSegmentation.from_pretrained(
            MODEL_ID,
            torch_dtype=dtype,
            use_safetensors=False,
        )
    except Exception:
        logger.exception("Mask2Former load failed with preferred dtype; retrying with float32.")
        model = Mask2FormerForUniversalSegmentation.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float32,
            use_safetensors=False,
        )

    model.to(device)
    model.eval()

    _PROCESSOR = processor
    _MODEL = model
    _DEVICE = device
    _ID2LABEL = {int(k): v for k, v in model.config.id2label.items()}
    logger.info("Mask2Former loaded: model=%s device=%s", MODEL_ID, device)
    return _PROCESSOR, _MODEL, _DEVICE, _ID2LABEL


def _compute_box(mask: np.ndarray) -> List[int]:
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]


def _compute_centroid(mask: np.ndarray) -> List[float]:
    ys, xs = np.nonzero(mask)
    height, width = mask.shape
    return [float(xs.mean() / max(width - 1, 1)), float(ys.mean() / max(height - 1, 1))]


def segment_image(image: np.ndarray) -> Dict[str, Any]:
    """
    Run Mask2Former panoptic segmentation on an RGB numpy image.

    Returns:
      {
        "segments": [
          {
            "segment_id": int,
            "coco_class_id": int,
            "coco_class_label": str,
            "centroid": [x_norm, y_norm],
            "area_fraction": float,
            "is_thing": bool,
            "bounding_box": [x1, y1, x2, y2],
            "confidence_score": float,
          },
          ...
        ],
        "panoptic_map": np.ndarray[int32],
        "id2label": {int: str},
        "device": str,
        "model_id": str,
      }
    """
    processor, model, device, id2label = load_model()
    image_pil = Image.fromarray(image.astype(np.uint8), mode="RGB")
    target_size = [image_pil.size[::-1]]

    inputs = processor(images=image_pil, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)

    result = processor.post_process_panoptic_segmentation(
        outputs,
        threshold=0.5,
        mask_threshold=0.5,
        overlap_mask_area_threshold=0.8,
        label_ids_to_fuse=set(),
        target_sizes=target_size,
    )[0]

    panoptic_map = result["segmentation"].detach().cpu().numpy().astype(np.int32)
    total_area = float(panoptic_map.shape[0] * panoptic_map.shape[1])
    segments: List[Dict[str, Any]] = []

    for segment in result.get("segments_info", []):
        segment_id = int(segment["id"])
        class_id = int(segment["label_id"])
        class_label = id2label.get(class_id, f"class_{class_id}")
        mask = panoptic_map == segment_id
        if not mask.any():
            continue
        segments.append({
            "segment_id": segment_id,
            "coco_class_id": class_id,
            "coco_class_label": class_label,
            "centroid": _compute_centroid(mask),
            "area_fraction": float(mask.sum() / total_area),
            "is_thing": class_id < PANOPTIC_THING_ID_CUTOFF,
            "bounding_box": _compute_box(mask),
            "confidence_score": float(segment.get("score", 0.0)),
        })

    return {
        "segments": segments,
        "panoptic_map": panoptic_map,
        "id2label": id2label,
        "device": str(device),
        "model_id": MODEL_ID,
    }
