import yaml
import numpy as np
import torch
import cv2
from pathlib import Path
from PIL import Image
from scipy.special import softmax

from run_mmsformer import run_mmsformer
from palette import palette
from visual_helpers import draw_legend

# Ensure semseg models are importable when running as script
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from semseg.models import *  # noqa: F403

# Natural texture classes included in the score
NATURAL_LABELS = {
    "fabric",
    "sand",
    "cobblestone",
    "grass",
    "wood",
    "leaf",
    "water",
}

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CFG_PATH = BASE_DIR.parent / "configs" / "mcubes_rgbadn.yaml"

_MMS_MODEL_CACHE = {}


def load_mmsformer_model(config_path=DEFAULT_CFG_PATH, device="cpu"):
    """
    Load the MMSFormer segmentation model using the provided config.
    Resolves relative paths by first trying the current working directory
    and then falling back to the repo root (parent of tools).
    Cached per (config_path, device) so downstream callers can reuse it.

    Returns:
        model, config_dict
    """
    cfg_path = Path(config_path)
    if not cfg_path.is_absolute():
        candidate = Path.cwd() / cfg_path
        cfg_path = candidate if candidate.exists() else BASE_DIR.parent / cfg_path
    cfg_path = cfg_path.resolve()

    cache_key = (cfg_path, device)

    if cache_key in _MMS_MODEL_CACHE:
        return _MMS_MODEL_CACHE[cache_key]

    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    modals = cfg["DATASET"]["MODALS"]
    model = eval(cfg["MODEL"]["NAME"])(cfg["MODEL"]["BACKBONE"], len(palette), modals)  # noqa: F405
    state = torch.load(cfg["EVAL"]["MODEL_PATH"], map_location=device)
    model.load_state_dict(state)
    model = model.to(device)
    model.eval()

    _MMS_MODEL_CACHE[cache_key] = (model, cfg)
    return model, cfg


def calc_natural_texture_presence(
    image_path: str,
    device="cpu",
    model=None,
    config_path=DEFAULT_CFG_PATH,
    natural_labels=None,
    visualize=False,
    viz_path=None,
    refine_with_superpixels=False,
    min_fraction=0.05,
    min_conf=0.2,
    num_superpixels=300,
    num_levels=4,
    prior=2,
    num_histogram_bins=5,
    num_iterations=10,
):
    """
    Compute the proportion of the image attributed to natural textures.

    Score is calculated as the mean probability mass assigned to the
    selected natural texture classes (softmax expectation over pixels).
    """
    labels = set(natural_labels) if natural_labels is not None else NATURAL_LABELS

    if model is None:
        model, _ = load_mmsformer_model(config_path=config_path, device=device)

    img = Image.open(image_path).convert("RGB")
    mms = run_mmsformer(img, model, device=device)

    logits = mms["meta"]["logits"]  # shape [C, H, W], numpy array
    probs = softmax(logits, axis=0)
    H, W = probs.shape[1:]

    segmap = logits.argmax(axis=0)

    natural_indices = [i for i, cls in enumerate(mms["classes"]) if cls in labels]
    if not natural_indices:
        return 0.0, {
            "per_class_presence": {},
            "natural_labels": sorted(labels),
        }

    refined_masks = None

    if refine_with_superpixels:
        np_img = np.array(img)
        bgr_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

        seeds = cv2.ximgproc.createSuperpixelSEEDS(
            bgr_img.shape[1],
            bgr_img.shape[0],
            bgr_img.shape[2],
            num_superpixels,
            num_levels,
            prior,
            num_histogram_bins,
        )
        seeds.iterate(bgr_img, num_iterations)
        superpixels = seeds.getLabels()

        refined_masks = {}
        for class_id, cls in enumerate(mms["classes"]):
            if cls not in labels:
                continue
            mask = np.zeros_like(segmap, dtype=bool)
            for sp_id in np.unique(superpixels):
                sp_region = (superpixels == sp_id)
                fraction = (segmap[sp_region] == class_id).mean()
                conf = probs[class_id][sp_region].mean()
                if fraction >= min_fraction and conf >= min_conf:
                    mask[sp_region] = True
            refined_masks[cls] = mask

    natural_prob_map = np.zeros_like(probs[0])
    per_class_presence = {}

    for cls in labels:
        if cls not in mms["classes"]:
            continue
        cid = mms["classes"].index(cls)
        if refine_with_superpixels and refined_masks is not None:
            class_mask = refined_masks.get(cls)
            if class_mask is None:
                continue
            prob_mass = (probs[cid] * class_mask).sum()
            natural_prob_map += probs[cid] * class_mask
        else:
            prob_mass = probs[cid].sum()
            natural_prob_map += probs[cid]

        per_class_presence[cls] = float(np.clip(prob_mass / (H * W), 0, 1))

    score = float(np.clip(natural_prob_map.sum() / (H * W), 0, 1))

    if visualize:
        if viz_path is None:
            viz_path = Path(image_path).with_suffix(".natural_overlay.png")

        overlay_masks = mms["masks"]
        if refine_with_superpixels and refined_masks is not None:
            # Replace masks for natural labels with refined versions; keep originals for others
            overlay_masks = [
                refined_masks.get(cls, mask) for mask, cls in zip(mms["masks"], mms["classes"])
            ]

        overlay, legend_entries = build_natural_overlay(
            mms,
            np.array(img),
            labels=labels,
            masks_override=overlay_masks,
        )
        out_img = Image.fromarray(overlay)
        out_img = draw_legend(out_img, legend_entries)
        Path(viz_path).parent.mkdir(parents=True, exist_ok=True)
        out_img.save(viz_path)

    return score, {
        "per_class_presence": per_class_presence,
        "natural_labels": sorted(labels),
        "viz_path": str(viz_path) if visualize else None,
    }


def build_natural_overlay(mms_output, base_image, labels=None, rng_seed=123, masks_override=None):
    """
    Create an overlay image highlighting natural textures and legend entries.
    """
    target_labels = set(labels) if labels is not None else NATURAL_LABELS
    np_img = np.array(base_image).astype(float)

    legend_entries = []
    rng = np.random.default_rng(rng_seed)

    masks_iter = masks_override if masks_override is not None else mms_output["masks"]

    for mask, cls in zip(masks_iter, mms_output["classes"]):
        if cls in target_labels:
            color = tuple(rng.integers(60, 255, size=3).tolist())
            np_img[mask] = 0.55 * np.array(color) + 0.45 * np_img[mask]
            legend_entries.append((cls, color))

    overlay = np.clip(np_img, 0, 255).astype(np.uint8)
    return overlay, legend_entries
