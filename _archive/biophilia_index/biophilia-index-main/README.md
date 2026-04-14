# Biophilic Index Calculator

This repo provides a basic, modular framework for using computer vision to calculate a biophilia value (called "biophilic index") for a given view. The current pipeline combines a Mask R-CNN for indoor plant detection and MMSFormer (see citation below) for natural texture segmentation and detection. These factors are weighted (in `scripts/biophilia_config.yaml`) and summed to yield a biophilic index in [0,1].

## Feature set

- Each factor outputs a score in [0,1]; weights are normalized by number of factors for proper weighting
- `plant_presence` factor: calculates area of view taken up by indoor plants

  - Current implementation uses a pretrained Mask R-CNN for speed, but is open to a more fine tuned model
- `natural_texture_presence` factor: calculates area of view taken up by various natural textures

  - Current implementation uses MMSFormer with caching per device/config for repetitive trials
  - Optionally supports superpixel refinement for the natural texture masks
- Outputs both the aggregated index and a per-factor breakdown (scores, weights, and per-class presence for natural textures)

## Quick start

1) Install dependencies (can use `conda`, or `bash`)

```bash
pip install -r requirements.txt
```

2) Make sure model assets are available
   - Mask R-CNN weights download automatically via `torchvision`.
   - MMSFormer weights: point `configs/mcubes_rgbadn.yaml:EVAL.MODEL_PATH` to your checkpoint (see Model assets below).
3) Run the aggregation function in `scripts/biophilia.py`

```bash
python scripts/biophilia.py --image /path/to/image.jpg \
    --config scripts/biophilia_config.yaml
```

The script prints the index and saves overlays to `out/` when `visualize: true` in the config.

Programmatic use:

```python
from scripts.biophilia import compute_biophilic_index

score, breakdown = compute_biophilic_index(
    "sample.jpg",
    config_path="scripts/biophilia_config.yaml",
)
print(score, breakdown["plant_presence"]["score"], breakdown["natural_texture_presence"]["score"])
```

## Configuration

`scripts/biophilia_config.yaml` lists factors, weights, and params. From here you can enable and disable specific factors, and the weights will automatically renormalize themselves based on the number of factors enabled.

- **plant_presence**: `confidence_threshold`, `device`, `visualize`, `viz_dir`.
- **natural_texture_presence**: MMSFormer `config_path`, `natural_labels` to include, `visualize`/`viz_dir`, and optional SEEDS superpixel refinement (`refine_with_superpixels`, `min_fraction`, `min_conf`, `num_superpixels`, etc.).

## Model assets

- To obtain MMSFormer config/weights for natural textures, update `configs/mcubes_rgbadn.yaml:EVAL.MODEL_PATH` to the checkpoint you want to use. 
  - This requires the checkpoint for the backbone model, in this case SegFormer. You can get it from [here](https://drive.google.com/drive/folders/10XgSW8f7ghRs9fJ0dE-EV8G2E_guVsT5), and by default, the config is set up to use `mit_b4.pth`. Store this in `checkpoints/pretrained/segformer/`.
  - Then, pretrained weights are available from the original MMSFormer release ([Google Drive](https://drive.google.com/drive/folders/1OPr7PUrL7hkBXogmHFzHuTJweHuJmlP-?usp=sharing)), which you can put anywhere but (for example) may be in `checkpoints/mcubes_rgb`. **Make sure to download the MCubeS weights**, and more specifically, you can download `MiT-B4-B1-RGB-MCubeS-50.44.pth`.
- The Mask R-CNN weights are Pytorch defaults and are downloaded automatically the first time from `torchvision`.

## Script file structure

```python
scripts
├── biophilia_config.yaml            # config file
├── biophilia_docs.md                # more detailed docs for biophilic index calculation process
├── biophilia.py                     # aggregation function/CLI
├── natural_texture_presence.py      # code for natural_texture_presence factor
├── palette.py                       # color palette tensor for creating overlays for natural_texture_presence
├── plant_presence.py                # code for plant_presence factor
├── run_mmsformer.py                 # wrapper to run inference using MMSFormer
└── visual_helpers.py                # additional helpers for creating visual overlays
```

## Notes and tips

- Make sure OpenCV has `ximgproc` for SEEDS superpixels function.
- The natural texture score uses probability mass (softmax expectation) instead of hard mask area.
- If you change factor weights or enable/disable factors, you do not need to renormalize manually.

## Citation

Since MMSFormer is used for this implementation of the natural texture factor, the credit for the model weights goes to:

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
```

If continuing to use MMSFormer in derivative works, please maintain this citation in a directory associated with the model weights of MMSFormer.
