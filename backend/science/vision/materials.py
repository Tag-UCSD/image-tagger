"""
Material analysis module for v3 Science Pipeline.

This module provides two levels of material detection:

1. **MaterialAnalyzer** (L0 heuristic): Fast HSV/luminance-based coverage
   estimation for wood, metal, glass, stone, plaster, and tile. No model
   download or API key required.

2. **GeminiMaterialAnalyzer** (L2 VLM): Uses Gemini Flash to identify
   materials, finishes, and textures in interior/architectural images.
   Requires a GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable.
   Falls back to StubEngine when no key is configured.

Both analyzers follow the AnalysisFrame pattern and can be used
independently or together in the science pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Any, Optional

import numpy as np
import cv2

from backend.science.core import AnalysisFrame
from backend.services.vlm import get_vlm_engine, StubEngine

logger = logging.getLogger("v3.science.materials")

# ============================================================================
# MATERIAL TAXONOMY
# Canonical material categories for interior/architectural images
# ============================================================================

MATERIAL_CATEGORIES = [
    "wood",
    "stone",
    "marble",
    "granite",
    "concrete",
    "brick",
    "glass",
    "metal",
    "steel",
    "brass",
    "copper",
    "aluminum",
    "ceramic",
    "tile",
    "porcelain",
    "fabric",
    "leather",
    "vinyl",
    "laminate",
    "plaster",
    "drywall",
    "wallpaper",
    "carpet",
    "paint",
    "plastic",
    "rubber",
    "terrazzo",
    "travertine",
]

# Coarse grouping for summary tags
MATERIAL_GROUPS = {
    "natural_stone": ["stone", "marble", "granite", "travertine", "terrazzo"],
    "wood": ["wood", "laminate"],
    "metal": ["metal", "steel", "brass", "copper", "aluminum"],
    "glass": ["glass"],
    "ceramic": ["ceramic", "tile", "porcelain"],
    "masonry": ["concrete", "brick", "plaster", "drywall"],
    "soft": ["fabric", "leather", "carpet", "vinyl", "rubber"],
    "synthetic": ["plastic", "laminate", "vinyl", "rubber"],
    "finish": ["paint", "wallpaper"],
}

# Gemini Flash prompt for material detection
_GEMINI_MATERIAL_PROMPT = """You are an expert architectural materials analyst. Analyze this interior/architectural image and identify all visible materials, finishes, and textures.

For each material detected, provide:
- "material": the material name (e.g. "hardwood", "marble", "stainless_steel", "ceramic_tile")
- "location": where in the image (e.g. "floor", "countertop", "wall", "ceiling", "cabinet", "door", "window_frame")
- "coverage": estimated percentage of image area (0.0 to 1.0)
- "confidence": your confidence in the identification (0.0 to 1.0)
- "finish": surface finish if applicable (e.g. "matte", "glossy", "brushed", "polished", "textured", "satin")
- "color_tone": dominant color/tone (e.g. "warm oak", "cool gray", "white", "dark walnut")

Also provide:
- "dominant_material": the single most prominent material in the scene
- "material_palette": list of the top 3-5 material categories present (from: wood, stone, marble, granite, concrete, brick, glass, metal, steel, brass, copper, aluminum, ceramic, tile, porcelain, fabric, leather, vinyl, laminate, plaster, drywall, wallpaper, carpet, paint, plastic, rubber, terrazzo, travertine)
- "style_note": one sentence describing the overall material palette style (e.g. "Modern industrial with exposed concrete and steel accents")

Return STRICT JSON with this exact structure:
{
  "materials": [
    {"material": "...", "location": "...", "coverage": 0.0, "confidence": 0.0, "finish": "...", "color_tone": "..."}
  ],
  "dominant_material": "...",
  "material_palette": ["...", "..."],
  "style_note": "..."
}"""

_MATERIAL_ALIASES = {
    "hardwood": "wood",
    "oak": "wood",
    "walnut": "wood",
    "plywood": "wood",
    "wood_paneling": "wood",
    "stainless_steel": "steel",
    "steel": "steel",
    "brushed_steel": "steel",
    "aluminium": "aluminum",
    "aluminum": "aluminum",
    "chrome": "metal",
    "nickel": "metal",
    "ceramic_tile": "tile",
    "porcelain_tile": "porcelain",
    "gypsum": "plaster",
    "drywall": "drywall",
    "painted_drywall": "paint",
    "upholstered_fabric": "fabric",
    "linen": "fabric",
    "cotton": "fabric",
    "wool": "fabric",
    "boucle": "fabric",
    "plastic_laminate": "laminate",
    "quartz": "stone",
    "limestone": "stone",
}


def _slugify_material(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name.strip().lower()).strip("_")


def _normalize_material_name(name: str) -> str:
    slug = _slugify_material(name)
    if slug in _MATERIAL_ALIASES:
        return _MATERIAL_ALIASES[slug]
    for canonical in MATERIAL_CATEGORIES:
        if canonical in slug:
            return canonical
    return slug or "unknown"


def _orient_depth_map(depth_map: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Normalise depth semantics to 0=near, 1=far.

    Depth backends are inconsistent about whether larger values mean "nearer"
    or "farther". For interiors, the lower part of the frame is usually closer
    than the upper part, so we use that as a weak orientation prior.
    """
    if depth_map is None:
        return None

    arr = np.asarray(depth_map, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[..., 0]
    if arr.ndim != 2 or arr.size == 0:
        return None

    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    arr = np.clip(arr, 0.0, 1.0)

    h = arr.shape[0]
    if h < 8:
        return arr

    top_mean = float(arr[: max(1, h // 5), :].mean())
    bottom_mean = float(arr[int(h * 0.8):, :].mean())
    if bottom_mean > top_mean:
        arr = 1.0 - arr
    return arr


def _surface_weight_map(frame: AnalysisFrame) -> Optional[np.ndarray]:
    depth = _orient_depth_map(getattr(frame, "depth_map", None))
    if depth is None:
        return None
    # Approximate projected-to-surface scaling under perspective:
    # farther visible surfaces represent more real area per screen pixel.
    return (1.0 + 1.5 * np.power(depth, 1.35)).astype(np.float32)


def _coverage_stats(frame: AnalysisFrame, mask: np.ndarray) -> dict[str, float]:
    mask_bool = np.asarray(mask, dtype=bool)
    total_pixels = float(mask_bool.size or 1)
    coverage_2d = float(mask_bool.sum() / total_pixels)

    depth = _orient_depth_map(getattr(frame, "depth_map", None))
    weights = _surface_weight_map(frame)
    if depth is None or weights is None:
        return {
            "coverage_2d": coverage_2d,
            "coverage_3d": coverage_2d,
            "depth_mean": 0.0,
            "depth_factor": 1.0,
        }

    masked_weights = float(weights[mask_bool].sum())
    total_weights = float(weights.sum()) or 1.0
    coverage_3d = masked_weights / total_weights
    depth_mean = float(depth[mask_bool].mean()) if mask_bool.any() else 0.0
    depth_factor = float(coverage_3d / coverage_2d) if coverage_2d > 0 else 1.0
    return {
        "coverage_2d": coverage_2d,
        "coverage_3d": coverage_3d,
        "depth_mean": depth_mean,
        "depth_factor": depth_factor,
    }


def _location_mask(location: str, shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    loc = location.lower()
    mask = np.zeros((h, w), dtype=bool)

    def fill(y0: float, y1: float, x0: float = 0.0, x1: float = 1.0) -> None:
        ys = slice(max(0, int(h * y0)), min(h, int(h * y1)))
        xs = slice(max(0, int(w * x0)), min(w, int(w * x1)))
        mask[ys, xs] = True

    if any(token in loc for token in ("floor", "rug", "carpet")):
        fill(0.62, 1.0)
    elif any(token in loc for token in ("ceiling", "light", "pendant", "fixture")):
        fill(0.0, 0.24)
    elif any(token in loc for token in ("wall", "backsplash")):
        fill(0.18, 0.78)
    elif any(token in loc for token in ("counter", "countertop", "island", "tabletop")):
        fill(0.45, 0.7, 0.15, 0.85)
    elif any(token in loc for token in ("cabinet", "millwork", "shelf", "bookcase")):
        fill(0.3, 0.85, 0.0, 1.0)
    elif any(token in loc for token in ("window", "glass", "glazing", "window_frame")):
        fill(0.08, 0.7, 0.1, 0.9)
    elif any(token in loc for token in ("door", "frame")):
        fill(0.15, 0.88, 0.05, 0.95)
    elif any(token in loc for token in ("sofa", "chair", "upholstery", "bed", "headboard")):
        fill(0.32, 0.88, 0.08, 0.92)
    else:
        mask[:, :] = True

    if not mask.any():
        mask[:, :] = True
    return mask


def _aggregate_material_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = _normalize_material_name(str(entry.get("material", "unknown")))
        grouped.setdefault(
            name,
            {
                "material": name,
                "coverage_2d": 0.0,
                "coverage_3d": 0.0,
                "confidence": 0.0,
                "locations": [],
                "finishes": [],
                "color_tones": [],
                "depth_mean": 0.0,
                "depth_factor": 1.0,
                "_depth_weight": 0.0,
            },
        )
        bucket = grouped[name]
        cov2d = float(entry.get("coverage_2d", entry.get("coverage", 0.0)))
        cov3d = float(entry.get("coverage_3d", cov2d))
        bucket["coverage_2d"] += cov2d
        bucket["coverage_3d"] += cov3d
        bucket["confidence"] = max(bucket["confidence"], float(entry.get("confidence", 0.0)))
        location = str(entry.get("location", "")).strip()
        finish = str(entry.get("finish", "")).strip()
        color_tone = str(entry.get("color_tone", "")).strip()
        if location and location not in bucket["locations"]:
            bucket["locations"].append(location)
        if finish and finish not in bucket["finishes"]:
            bucket["finishes"].append(finish)
        if color_tone and color_tone not in bucket["color_tones"]:
            bucket["color_tones"].append(color_tone)
        depth_mean = float(entry.get("depth_mean", 0.0))
        bucket["_depth_weight"] += cov3d
        bucket["depth_mean"] += depth_mean * cov3d

    aggregated = []
    for bucket in grouped.values():
        weight = bucket.pop("_depth_weight", 0.0)
        if weight > 0:
            bucket["depth_mean"] = float(bucket["depth_mean"] / weight)
        bucket["coverage_2d"] = min(1.0, float(bucket["coverage_2d"]))
        bucket["coverage_3d"] = min(1.0, float(bucket["coverage_3d"]))
        if bucket["coverage_2d"] > 0:
            bucket["depth_factor"] = float(bucket["coverage_3d"] / bucket["coverage_2d"])
        aggregated.append(bucket)

    total_2d = sum(float(entry.get("coverage_2d", 0.0)) for entry in aggregated)
    total_3d = sum(float(entry.get("coverage_3d", 0.0)) for entry in aggregated)
    if total_2d > 1.0:
        for entry in aggregated:
            entry["coverage_2d"] = float(entry["coverage_2d"] / total_2d)
    if total_3d > 1.0:
        for entry in aggregated:
            entry["coverage_3d"] = float(entry["coverage_3d"] / total_3d)
    for entry in aggregated:
        cov2d = float(entry.get("coverage_2d", 0.0))
        cov3d = float(entry.get("coverage_3d", cov2d))
        entry["depth_factor"] = float(cov3d / cov2d) if cov2d > 0 else 1.0

    aggregated.sort(key=lambda x: x.get("coverage_3d", x.get("coverage_2d", 0.0)), reverse=True)
    return aggregated


class MaterialAnalyzer:
    """
    Heuristic-based material classification (L0).

    Uses simple HSV and luminance/texture rules to estimate coverage
    of wood, metal, and glass in the scene. Values are normalized
    coverage ratios in [0, 1].
    """

    @staticmethod
    def analyze(frame: AnalysisFrame) -> None:
        img = frame.original_image
        if img is None:
            return

        # Convert to uint8 RGB for OpenCV operations
        if img.dtype == np.float32 or img.dtype == np.float64:
            image_uint8 = (img * 255).astype(np.uint8)
        else:
            image_uint8 = img

        # Convert to HSV for material heuristics
        hsv = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2HSV)

        # --- Wood heuristic (ported from v2 logic) ---
        # Brown-ish hues (approx 5–30 in OpenCV HSV),
        # with reasonable saturation and value.
        wood_mask = (
            (hsv[:, :, 0] >= 5)
            & (hsv[:, :, 0] <= 30)
            & (hsv[:, :, 1] > 30)
            & (hsv[:, :, 2] > 50)
        )
        wood_stats = _coverage_stats(frame, wood_mask)
        frame.add_attribute("material.wood_coverage", wood_stats["coverage_2d"])

        # --- Metal heuristic (simplified from v2) ---
        # Low saturation, mid-to-high value → shiny / metallic regions.
        metal_mask = (hsv[:, :, 1] < 30) & (hsv[:, :, 2] > 150)
        metal_stats = _coverage_stats(frame, metal_mask)
        frame.add_attribute("material.metal_coverage", metal_stats["coverage_2d"])

        # --- Glass heuristic (ported from v2) ---
        # High luminance + low local variance → smooth bright panes.
        gray = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2GRAY)
        bright_mask = gray > 200

        # Local variance proxy using a smoothing kernel
        kernel = np.ones((5, 5), np.float32) / 25.0
        local_mean = cv2.filter2D(gray.astype(float), -1, kernel)
        local_var = (gray.astype(float) - local_mean) ** 2
        smooth_mask = local_var < 100.0

        glass_mask = bright_mask & smooth_mask
        glass_stats = _coverage_stats(frame, glass_mask)
        frame.add_attribute("material.glass_coverage", glass_stats["coverage_2d"])
        # --- L1 material cues (read-only; support higher tiers) ---
        # Normalized brightness (0-1) from grayscale.
        gray_float = gray.astype(float) / 255.0
        brightness_mean = float(gray_float.mean())
        frame.add_attribute("materials.cues.brightness_mean", brightness_mean, confidence=0.7)

        # Global texture variance (roughness proxy).
        texture_variance = float(gray_float.var())
        frame.add_attribute("materials.cues.texture_variance", min(texture_variance * 10.0, 1.0), confidence=0.6)

        # Mean saturation and value in HSV.
        sat_mean = float(hsv[:, :, 1].mean() / 255.0)
        val_mean = float(hsv[:, :, 2].mean() / 255.0)
        frame.add_attribute("materials.cues.saturation_mean", sat_mean, confidence=0.7)
        frame.add_attribute("materials.cues.value_mean", val_mean, confidence=0.7)

        # Specularity proxy: proportion of high-value, low-saturation pixels.
        spec_mask = (hsv[:, :, 1] < 40) & (hsv[:, :, 2] > 200)
        specularity_proxy = float(spec_mask.sum() / spec_mask.size)
        frame.add_attribute("materials.cues.specularity_proxy", specularity_proxy, confidence=0.6)

        # --- Substrate heuristics beyond wood/metal/glass ---
        # Stone/Concrete: low saturation, mid value, higher roughness.
        stone_mask = (
            (hsv[:, :, 1] < 60) &
            (hsv[:, :, 2] > 60) &
            (hsv[:, :, 2] < 200)
        )
        stone_stats = _coverage_stats(frame, stone_mask)
        frame.add_attribute("materials.substrate.stone_concrete", stone_stats["coverage_2d"], confidence=0.5)

        # Plaster/Gypsum: very low saturation, high value, low variance.
        plaster_mask = (
            (hsv[:, :, 1] < 30) &
            (hsv[:, :, 2] > 180)
        )
        plaster_stats = _coverage_stats(frame, plaster_mask)
        frame.add_attribute("materials.substrate.plaster_gypsum", plaster_stats["coverage_2d"], confidence=0.5)

        # Tile/Ceramic: bright and moderately saturated with elevated local variance.
        # We reuse local_var from the glass heuristic as a crude texture cue.
        tile_mask = (
            (hsv[:, :, 2] > 150) &
            (hsv[:, :, 1] > 40) &
            (local_var > 50.0)
        )
        tile_stats = _coverage_stats(frame, tile_mask)
        frame.add_attribute("materials.substrate.tile_ceramic", tile_stats["coverage_2d"], confidence=0.4)

        entries = [
            {"material": "wood", "confidence": 0.7, **wood_stats},
            {"material": "metal", "confidence": 0.6, **metal_stats},
            {"material": "glass", "confidence": 0.7, **glass_stats},
            {"material": "stone_concrete", "confidence": 0.5, **stone_stats},
            {"material": "plaster_gypsum", "confidence": 0.5, **plaster_stats},
            {"material": "tile_ceramic", "confidence": 0.4, **tile_stats},
        ]
        entries = [
            entry for entry in entries
            if entry["coverage_2d"] >= 0.01 or entry["coverage_3d"] >= 0.01
        ]
        entries = _aggregate_material_entries(entries)
        frame.metadata["material_detection_basic"] = {
            "mode": "heuristic",
            "engine": "HSV+Depth",
            "coverage_basis": "depth_3d_estimate" if getattr(frame, "depth_map", None) is not None else "2d",
            "depth_available": getattr(frame, "depth_map", None) is not None,
            "materials": entries,
            "dominant_material": entries[0]["material"] if entries else "unknown",
            "material_palette": [entry["material"] for entry in entries[:5]],
            "style_note": "Heuristic material estimate from color, luminance, texture, and depth cues.",
        }


# ============================================================================
# GEMINI FLASH MATERIAL ANALYZER (L2 VLM)
# ============================================================================

class GeminiMaterialAnalyzer:
    """
    VLM-based material detection using Gemini Flash.

    Uses the configured VLM engine (defaults to Gemini Flash when
    GEMINI_API_KEY is set) to identify materials, finishes, and textures
    in interior/architectural images.

    Output:
    - Frame attributes: material.vlm.dominant, material.vlm.material_count, etc.
    - Frame metadata: material_detection (full result), material_tags (tag list)
    - Tags: "material:wood (85%)", "material_finish:matte hardwood (floor)", etc.

    Falls back gracefully to StubEngine when no API key is configured.
    """

    @staticmethod
    def analyze(
        frame: AnalysisFrame,
        provider_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run Gemini Flash material detection on the image.

        Args:
            frame: AnalysisFrame containing the image to analyze
            provider_override: Force a specific VLM provider (e.g. "gemini", "openai")

        Returns:
            Dictionary containing materials, tags, and style analysis.
            Returns a stub result if no VLM provider is configured.
        """
        img = frame.original_image
        if img is None:
            logger.warning("No image in frame, skipping material VLM analysis")
            return {"stub": True, "error": "no_image"}

        # Encode image as JPEG bytes for VLM
        if img.dtype == np.float32 or img.dtype == np.float64:
            image_uint8 = (img * 255).astype(np.uint8)
        else:
            image_uint8 = img

        # Convert RGB to BGR for OpenCV encoding
        image_bgr = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2BGR)
        ok, buffer = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            logger.error("Failed to encode image for VLM material analysis")
            return {"stub": True, "error": "encode_failed"}

        image_bytes = buffer.tobytes()

        # Get VLM engine
        engine = get_vlm_engine(provider_override=provider_override)

        # Check for stub mode
        if isinstance(engine, StubEngine):
            logger.info("VLM in stub mode - no material VLM analysis available")
            stub_result = {
                "stub": True,
                "engine": "StubEngine",
                "note": "Configure GEMINI_API_KEY to enable Gemini Flash material detection.",
            }
            frame.metadata["material_detection"] = stub_result
            frame.metadata["material_tags"] = []
            return stub_result

        # Call VLM
        try:
            logger.info(f"Running material detection via {type(engine).__name__}...")
            raw_result = engine.analyze_image(image_bytes, _GEMINI_MATERIAL_PROMPT)
        except Exception as e:
            logger.error(f"VLM material detection failed: {e}")
            error_result = {
                "stub": True,
                "error": str(e),
                "engine": type(engine).__name__,
            }
            frame.metadata["material_detection"] = error_result
            frame.metadata["material_tags"] = []
            return error_result

        # Parse and structure the result
        result = GeminiMaterialAnalyzer._parse_vlm_result(raw_result)
        result = GeminiMaterialAnalyzer._apply_depth_scaling(frame, result)

        # Generate tags from the parsed result
        tags = GeminiMaterialAnalyzer._generate_tags(result)

        # Store in frame attributes
        materials_list = result.get("materials_aggregated", result.get("materials", []))
        dominant = result.get("dominant_material", "unknown")
        palette = result.get("material_palette", [])

        frame.add_attribute("material.vlm.dominant", hash(dominant) % 1000 / 1000.0)
        frame.add_attribute("material.vlm.material_count", float(len(materials_list)))
        frame.add_attribute("material.vlm.palette_size", float(len(palette)))

        # Store coverage for top materials
        for mat_entry in materials_list[:5]:
            mat_name = mat_entry.get("material", "unknown").replace(" ", "_").lower()
            coverage = float(mat_entry.get("coverage_3d", mat_entry.get("coverage", 0.0)))
            confidence = float(mat_entry.get("confidence", 0.0))
            frame.add_attribute(
                f"material.vlm.{mat_name}_coverage",
                coverage,
                confidence=confidence,
            )

        # Store full result and tags in metadata
        result["tags"] = tags
        result["engine"] = type(engine).__name__
        result["coverage_basis"] = (
            "depth_3d_estimate" if getattr(frame, "depth_map", None) is not None else "2d"
        )
        result["depth_available"] = getattr(frame, "depth_map", None) is not None
        frame.metadata["material_detection"] = result
        frame.metadata["material_tags"] = tags

        logger.info(
            f"Material detection: dominant={dominant}, "
            f"materials={len(materials_list)}, tags={len(tags)}"
        )

        return result

    @staticmethod
    def _parse_vlm_result(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate the VLM response into a structured result."""
        result = {
            "materials": [],
            "dominant_material": "unknown",
            "material_palette": [],
            "style_note": "",
        }

        if not isinstance(raw, dict):
            logger.warning(f"VLM returned non-dict type: {type(raw)}")
            return result

        # Extract materials list
        materials = raw.get("materials", [])
        if isinstance(materials, list):
            parsed_materials = []
            for mat in materials:
                if isinstance(mat, dict):
                    parsed_materials.append({
                        "material": str(mat.get("material", "unknown")),
                        "location": str(mat.get("location", "unknown")),
                        "coverage": min(1.0, max(0.0, float(mat.get("coverage", 0.0)))),
                        "confidence": min(1.0, max(0.0, float(mat.get("confidence", 0.0)))),
                        "finish": str(mat.get("finish", "")),
                        "color_tone": str(mat.get("color_tone", "")),
                    })
            # Sort by coverage descending
            parsed_materials.sort(key=lambda x: x["coverage"], reverse=True)
            result["materials"] = parsed_materials

        # Extract dominant material
        dominant = raw.get("dominant_material", "unknown")
        if isinstance(dominant, str) and dominant:
            result["dominant_material"] = dominant

        # Extract palette
        palette = raw.get("material_palette", [])
        if isinstance(palette, list):
            result["material_palette"] = [str(p) for p in palette if isinstance(p, str)]

        # Extract style note
        style_note = raw.get("style_note", "")
        if isinstance(style_note, str):
            result["style_note"] = style_note

        return result

    @staticmethod
    def _apply_depth_scaling(frame: AnalysisFrame, result: Dict[str, Any]) -> Dict[str, Any]:
        materials = result.get("materials", [])
        if not isinstance(materials, list):
            result["materials_aggregated"] = []
            return result

        adjusted = []
        shape = frame.original_image.shape[:2]
        for entry in materials:
            location = str(entry.get("location", ""))
            stats = _coverage_stats(frame, _location_mask(location, shape))
            coverage_2d = float(entry.get("coverage", 0.0))
            entry = dict(entry)
            entry["coverage_2d"] = coverage_2d
            entry["coverage_3d"] = min(1.0, coverage_2d * stats["depth_factor"])
            entry["depth_mean"] = stats["depth_mean"]
            entry["depth_factor"] = stats["depth_factor"]
            adjusted.append(entry)

        aggregated = _aggregate_material_entries(adjusted)
        if aggregated:
            result["dominant_material"] = aggregated[0]["material"]
            result["material_palette"] = [entry["material"] for entry in aggregated[:5]]
        result["materials"] = adjusted
        result["materials_aggregated"] = aggregated
        return result

    @staticmethod
    def _generate_tags(result: Dict[str, Any]) -> List[str]:
        """Generate human-readable tags from the parsed material detection result."""
        tags = []

        # Dominant material tag
        dominant = result.get("dominant_material", "unknown")
        if dominant and dominant != "unknown":
            tags.append(f"material:{dominant}")

        # Individual material tags with confidence
        for mat in result.get("materials_aggregated", result.get("materials", []))[:6]:
            material_name = mat.get("material", "unknown")
            confidence = mat.get("confidence", 0.0)
            location = ", ".join(mat.get("locations", [])) or mat.get("location", "")
            finish = ", ".join(mat.get("finishes", [])) or mat.get("finish", "")
            conf_pct = int(confidence * 100)
            cov_pct = int(round(float(mat.get("coverage_3d", mat.get("coverage", 0.0))) * 100))

            if conf_pct >= 50 or cov_pct >= 4:
                # High confidence: include location
                tag = f"material:{material_name} ({cov_pct}%)"
                if tag not in tags:
                    tags.append(tag)

                # Add finish tag if available
                if finish and finish not in ("", "unknown", "None"):
                    finish_tag = f"finish:{finish} {material_name} ({location})"
                    tags.append(finish_tag)

        # Palette tags
        for palette_mat in result.get("material_palette", [])[:5]:
            palette_tag = f"palette:{palette_mat}"
            if palette_tag not in tags:
                tags.append(palette_tag)

        # Style note as a tag
        style_note = result.get("style_note", "")
        if style_note and len(style_note) < 80:
            tags.append(f"material_style:{style_note}")

        return tags

    @staticmethod
    def get_tags(frame: AnalysisFrame) -> List[str]:
        """
        Get the material detection tags from a frame that has been analyzed.

        Args:
            frame: AnalysisFrame that has been processed by analyze()

        Returns:
            List of tag strings
        """
        return frame.metadata.get("material_tags", [])

    @staticmethod
    def update_image_tags(
        db_session,
        image_id: int,
        tags: List[str],
        replace_material_tags: bool = True,
    ) -> bool:
        """
        Update an image's meta_data tags with material detection results.

        Args:
            db_session: SQLAlchemy database session
            image_id: ID of the image to update
            tags: List of material tags to add
            replace_material_tags: If True, removes existing material:* tags first

        Returns:
            True if successful, False otherwise
        """
        from backend.models.assets import Image

        try:
            image = db_session.query(Image).filter(Image.id == image_id).first()
            if not image:
                logger.warning(f"Image {image_id} not found for tag update")
                return False

            # Get existing meta_data or create new
            meta_data = image.meta_data or {}
            existing_tags = meta_data.get("tags", [])

            if replace_material_tags:
                # Remove existing material tags
                existing_tags = [
                    t for t in existing_tags
                    if not t.startswith("material:")
                    and not t.startswith("finish:")
                    and not t.startswith("palette:")
                    and not t.startswith("material_style:")
                ]

            # Add new material tags
            existing_tags.extend(tags)

            # Update meta_data
            meta_data["tags"] = existing_tags
            image.meta_data = meta_data

            db_session.commit()
            logger.info(f"Updated image {image_id} with material tags: {tags}")
            return True

        except Exception as e:
            logger.error(f"Failed to update image {image_id} tags: {e}")
            db_session.rollback()
            return False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def detect_materials_vlm(
    image: np.ndarray,
    provider_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to detect materials from a single image using Gemini Flash.

    Args:
        image: RGB numpy array (H, W, 3)
        provider_override: Force a specific VLM provider

    Returns:
        Dictionary with material detection results including 'tags' key
    """
    frame = AnalysisFrame(image_id=-1, original_image=image)
    return GeminiMaterialAnalyzer.analyze(frame, provider_override=provider_override)
