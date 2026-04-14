"""Lightweight biophilia composite for the main science pipeline."""

from __future__ import annotations

from backend.science.core import AnalysisFrame


PLANT_PRESENCE_WEIGHT = 0.3
NATURAL_TEXTURE_WEIGHT = 0.7


def _clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


class BiophiliaAnalyzer:
    """Compute a biophilia index from existing Image Tagger science signals."""

    def analyze(self, frame: AnalysisFrame) -> None:
        attrs = frame.attributes

        plant_presence = _clamp01(attrs.get("naturalness.green_ratio", 0.0))

        natural_texture_components: list[float] = []
        for key in ("naturalness.earth_ratio", "naturalness.blue_ratio", "fractal.D"):
            if key in attrs:
                natural_texture_components.append(_clamp01(attrs[key]))
        if not natural_texture_components and "naturalness.score" in attrs:
            natural_texture_components.append(_clamp01(attrs["naturalness.score"]))

        if not natural_texture_components and "naturalness.green_ratio" not in attrs:
            return

        natural_texture = (
            sum(natural_texture_components) / len(natural_texture_components)
            if natural_texture_components
            else 0.0
        )

        biophilia_index = (
            (PLANT_PRESENCE_WEIGHT * plant_presence)
            + (NATURAL_TEXTURE_WEIGHT * natural_texture)
        ) / (PLANT_PRESENCE_WEIGHT + NATURAL_TEXTURE_WEIGHT)

        frame.add_attribute("biophilia.index", _clamp01(biophilia_index), confidence=0.75)
        frame.metadata["biophilia"] = {
            "plant_presence_proxy": round(plant_presence, 4),
            "natural_texture_proxy": round(natural_texture, 4),
            "weights": {
                "plant_presence": PLANT_PRESENCE_WEIGHT,
                "natural_texture": NATURAL_TEXTURE_WEIGHT,
            },
            "source": "lightweight_proxy_v1",
        }
