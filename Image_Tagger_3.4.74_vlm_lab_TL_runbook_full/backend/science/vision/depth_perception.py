"""
Depth perception using Depth Anything V2 (Hugging Face Transformers).

Provides monocular depth estimation and optional Spectral_r colormap
for debug visualization.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np

from backend.science.core import AnalysisFrame

logger = logging.getLogger(__name__)

# Lazy pipeline to avoid loading the model at import time
_pipe = None


def _get_pipeline():
    """Lazily create the depth-estimation pipeline (Depth Anything V2 Small)."""
    global _pipe
    if _pipe is not None:
        return _pipe
    try:
        from transformers import pipeline
        _pipe = pipeline(
            task="depth-estimation",
            model="depth-anything/Depth-Anything-V2-Small-hf",
        )
        logger.info("DepthAnythingAnalyzer: loaded Depth-Anything-V2-Small-hf")
    except Exception as e:
        logger.warning(
            "DepthAnythingAnalyzer: failed to load Depth Anything V2: %s. "
            "Install transformers and torch to enable.",
            e,
            exc_info=True,
        )
        _pipe = False  # mark as attempted
    return _pipe


def _image_to_pil(rgb: np.ndarray):
    """Convert RGB numpy (H,W,3) uint8 to PIL Image."""
    from PIL import Image
    return Image.fromarray(rgb)


def _depth_to_normalized_map(depth_output) -> np.ndarray:
    """Convert pipeline depth output to HxW float32 in [0, 1]."""
    import cv2
    depth_map = np.array(depth_output, dtype=np.float32)
    if depth_map.ndim == 3:
        depth_map = depth_map.squeeze()
    if depth_map.ndim != 2:
        raise ValueError("Depth map must be 2D")
    depth_norm = cv2.normalize(depth_map, None, 0, 1.0, cv2.NORM_MINMAX)
    return np.asarray(depth_norm, dtype=np.float32)


def depth_to_colormap_rgb(depth_norm: np.ndarray) -> np.ndarray:
    """
    Apply Spectral_r colormap to normalized depth [0,1].
    Returns RGB uint8 (H, W, 3), no alpha.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = np.clip(depth_norm.astype(np.float64), 0.0, 1.0)
    colormap = plt.colormaps["Spectral_r"]
    depth_color = (colormap(d) * 255).astype(np.uint8)[:, :, :3]
    return depth_color


class DepthAnythingAnalyzer:
    """Analyzer for depth perception using Depth Anything V2 (Hugging Face)."""

    name = "depth_perception"
    tier = "L1.5"
    requires = ["original_image"]
    provides = ["depth_map", "vision.depth_mean", "vision.depth_contrast"]

    def __init__(self, model_id: str = "depth-anything/Depth-Anything-V2-Small-hf"):
        self.model_id = model_id

    def analyze(self, frame: AnalysisFrame) -> None:
        """Run depth estimation and set frame.depth_map and summary attributes."""
        pipe = _get_pipeline()
        if pipe is None or pipe is False:
            return

        rgb = frame.original_image
        if rgb is None:
            return

        try:
            pil_image = _image_to_pil(rgb)
            out = pipe(pil_image)
            depth = out.get("depth")
            if depth is None:
                return
            depth_norm = _depth_to_normalized_map(depth)
            frame.depth_map = depth_norm

            # Summary attributes for BN/export
            mean_d = float(np.nanmean(depth_norm))
            std_d = float(np.nanstd(depth_norm))
            frame.add_attribute("vision.depth_mean", float(np.clip(mean_d, 0.0, 1.0)))
            frame.add_attribute(
                "vision.depth_contrast", float(np.clip(std_d * 0.5, 0.0, 1.0))
            )
        except Exception:
            logger.exception("DepthAnythingAnalyzer.analyze failed for image_id=%s", frame.image_id)


def compute_depth_colormap_png(rgb: np.ndarray) -> Optional[bytes]:
    """
    Compute depth map and return PNG bytes (Spectral_r colormap) for debug API.
    Returns None if the model is not available.
    """
    import cv2
    pipe = _get_pipeline()
    if pipe is None or pipe is False:
        return None
    try:
        pil_image = _image_to_pil(rgb)
        out = pipe(pil_image)
        depth = out.get("depth")
        if depth is None:
            return None
        depth_norm = _depth_to_normalized_map(depth)
        depth_color = depth_to_colormap_rgb(depth_norm)
        # OpenCV expects BGR for imencode
        depth_bgr = cv2.cvtColor(depth_color, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".png", depth_bgr)
        if not ok:
            return None
        return buf.tobytes()
    except Exception:
        logger.exception("compute_depth_colormap_png failed")
        return None
