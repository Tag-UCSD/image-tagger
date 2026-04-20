from __future__ import annotations

import numpy as np

from backend.science.biophilia import BiophiliaAnalyzer
from backend.science.core import AnalysisFrame
from backend.science.math.naturalness import NaturalnessAnalyzer


def test_naturalness_reads_original_image() -> None:
    image = np.zeros((16, 16, 3), dtype=np.uint8)
    image[..., 1] = 255
    frame = AnalysisFrame(image_id=1, original_image=image)

    NaturalnessAnalyzer().analyze(frame)

    assert frame.attributes["naturalness.green_ratio"] > 0.9
    assert frame.attributes["naturalness.score"] > 0.4


def test_biophilia_index_uses_reference_weights() -> None:
    frame = AnalysisFrame(
        image_id=1,
        original_image=np.zeros((8, 8, 3), dtype=np.uint8),
    )
    frame.attributes.update(
        {
            "naturalness.green_ratio": 0.8,
            "naturalness.earth_ratio": 0.3,
            "naturalness.blue_ratio": 0.6,
            "fractal.D": 0.9,
        }
    )

    BiophiliaAnalyzer().analyze(frame)

    expected_natural_texture = (0.3 + 0.6 + 0.9) / 3.0
    expected_index = (0.3 * 0.8) + (0.7 * expected_natural_texture)
    assert frame.attributes["biophilia.index"] == expected_index
    assert frame.metadata["biophilia"]["weights"]["plant_presence"] == 0.3
