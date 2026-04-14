# Biophilic Index Module

A small, modular pipeline that scores an image on a biophilic index (0–1). Each “factor” produces a score in [0,1], and a weighted, normalized sum of enabled factors yields the final index.

Current factors:

- **Plant presence** (Mask R-CNN on COCO “potted plant”), optional saved overlay.
- **Natural texture presence** (MMSFormer material segmentation over a subset of natural classes), optional superpixel refinement, optional saved overlay.

## What it does

- Loads the models once per device/config via caching.
- Runs the enabled factors against an input image.
- Normalizes factor weights to sum to 1 and aggregates `sum(weight_i * score_i)`.
- Returns both the final index and a per-factor breakdown (scores, weights, and factor-specific details).

## How it works

1. **Config-driven factors**: `biophilia_config.yaml` lists factors, toggles, and weights. Only enabled factors participate; weights are renormalized.
2. **Plant presence**: Mask R-CNN finds COCO label 64 (“potted plant”), merges overlapping masks, filters by confidence, and computes weighted mask area / total pixels. Uncertainty = `1 - mean(score of detections)`. Optional overlay saved to disk when enabled.
3. **Natural textures**: MMSFormer logits → softmax; probability mass over “natural” classes (`NATURAL_LABELS`) is summed and averaged over all pixels to produce a score. Optional superpixel refinement gates regions by per-superpixel fraction/conf thresholds; overlays can be saved with refined masks. Also returns per-class presence.
4. **Aggregation**: `compute_biophilic_index` runs each factor, applies normalized weights, and sums to the final index.

## Files

- `biophilia.py` — aggregator/CLI.
- `biophilia_config.yaml` — toggles + weights + factor params.
- `plant_presence.py` — Mask R-CNN scorer with optional overlay save.
- `natural_texture_presence.py` — MMSFormer scorer + overlay helper; supports superpixel refinement and overlay save.
- `run_mmsformer.py` — MMSFormer inference wrapper.
- `visual_helpers.py`, `palette.py` — rendering utils and palette.

## Simple step-through (input -> output)

Input: an image path and a config YAML.

Pipeline:

1) `compute_biophilic_index(image, config)` loads config and normalizes weights.
2) For plant presence:
   - Load/cached Mask R-CNN (if not already).
   - Run inference with Mask R-CNN -> drop all non-plant masks -> merge/filter overalapping masks -> compute area ratio.
   - Produce `score` and `uncertainty`.
3) For natural textures:
   - Load/cached MMSFormer (if not already).
   - Run segmentation -> run softmax to get probabilities -> sum probability mass over natural classes.
   - If enabled, refine masks with superpixels using the SEEDS algorithm that meet a certain overlapping w/ mask threshold and confidence threshold (defined in `biophilia_config.yaml`).
   - Produce `score`, per-class presence, and optional overlay.
4) Combine: `final_index = sum(weight_i * score_i)` across enabled factors. Overlays are saved to the output directory if toggled.

Output:

- `final_index` (float 0–1)
- `breakdown` dict per factor (score, weight, plus details like `uncertainty` or `per_class_presence`).

## How to use

CLI:

```bash
python tools/biophilia.py --image /path/to/image.jpg \
    --config MMSFormer/tools/biophilia_config.yaml
```

Programmatic:

```python
from MMSFormer.tools.biophilia import compute_biophilic_index

score, breakdown = compute_biophilic_index(
    "sample.jpg",
    config_path="MMSFormer/tools/biophilia_config.yaml",
)
print("Biophilic index:", score)
print("Plant presence:", breakdown["plant_presence"]["score"])
print("Natural textures:", breakdown["natural_texture_presence"]["score"])
```

## Customizing and tuning

- Enabling/disabling factors: use the `enabled` parameter in the config to turn on and off specific factors.
- Adjust relative influence: change `weight` values; they will auto-normalize depending on the number of factors enabled.
- Plant detection: tune `confidence_threshold`, switch `device`, enable `visualize`, and set `viz_dir` for overlays.
- Natural textures: change `natural_labels`, point `config_path` to different MMSFormer weights, switch `device`, enable `visualize`/`viz_dir`, and toggle superpixel refinement with thresholds and SEEDS params.

## Visual diagnostics

- Run `bottom_up_test.py` for an easy 4-panel diagnostic (original, leaf mask, refined mask via superpixels, natural textures overlay) if the output doesn't seem right.
- Use per-factor `visualize`/`viz_dir` in config to save plant and natural overlays during the main biophilia run.
- Build overlays yourself with `build_natural_overlay` + `draw_legend` if you need custom visuals.

## Notes & assumptions

- Plant proxy is COCO class 64 (“potted plant”).
- Natural texture score uses probability mass (softmax expectation), not just hard mask area.
- Models are cached per device/config to avoid reload overhead.
- Ensure referenced checkpoints/configs exist at the paths in `biophilia_config.yaml` and MMSFormer configs.

## Citations

If you use MMSFormer for the natural texture factor, please cite:

```
@ARTICLE{Reza2024MMSFormer,
    author={Reza, Md Kaykobad and Prater-Bennette, Ashley and Asif, M. Salman},
    journal={IEEE Open Journal of Signal Processing},
    title={MMSFormer: Multimodal Transformer for Material and Semantic Segmentation},
    year={2024},
    volume={},
    number={},
    pages={1-12},
    keywords={Image segmentation;Feature extraction;Transformers;Task analysis;Fuses;Semantic segmentation;Decoding;multimodal image segmentation;material segmentation;semantic segmentation;multimodal fusion;transformer},
    doi={10.1109/OJSP.2024.3389812}
}