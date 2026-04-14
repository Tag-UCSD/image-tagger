# bottom_up_test.py

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import cv2

from scipy.special import softmax
from skimage.segmentation import mark_boundaries

# Local imports
from natural_texture_presence import (
    NATURAL_LABELS,
    build_natural_overlay,
    calc_natural_texture_presence,
    load_mmsformer_model,
)
from run_mmsformer import run_mmsformer
from visual_helpers import overlay_mask, draw_legend, create_side_by_side

DEVICE = "cpu"
MMS_MODEL, _ = load_mmsformer_model(device=DEVICE)

def run_test(image_path):

    print(f"Running 4-panel diagnostic on: {image_path}")

    # ------------------------------------------------------------
    # Load image
    # ------------------------------------------------------------
    img = Image.open(image_path).convert("RGB")
    np_img = np.array(img)

    # ------------------------------------------------------------
    # 1) MMSFormer segmentation
    # ------------------------------------------------------------
    mms = run_mmsformer(img, MMS_MODEL, device=DEVICE)

    # Get leaf class index
    leaf_idx = mms["classes"].index("grass")

    # Segmentation map (argmax)
    segmap = mms["meta"]["logits"].argmax(axis=0)

    # Extract probabilities
    logits = mms["meta"]["logits"]          # shape [C, H, W]
    probs  = softmax(logits, axis=0)        # pixel-level probabilities
    leaf_prob = probs[leaf_idx]             # shape [H, W]

    # Raw leaf mask
    leaf_mask = (segmap == leaf_idx)

    # Visualize raw leaf overlay
    leaf_overlay = overlay_mask(img,
                                leaf_mask,
                                (50,180,50),
                                alpha=0.55)
    leaf_overlay.show()

    # ------------------------------------------------------------
    # 2) Superpixel segmentation + refined propagation
    # ------------------------------------------------------------
    n_segments = 300
    # superpixels = slic(np_img, n_segments=n_segments, sigma=5)
    
    # Convert RGB → BGR for OpenCV
    bgr_img = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

    num_superpixels = 300
    num_levels = 4          # number of block levels (hierarchical)
    prior = 2               # histogram smoothing prior
    num_histogram_bins = 5  # color histogram bins per channel
    num_iterations = 10     # refinement steps

    seeds = cv2.ximgproc.createSuperpixelSEEDS(
        bgr_img.shape[1],     # width
        bgr_img.shape[0],     # height
        bgr_img.shape[2],     # channels (3)
        num_superpixels,
        num_levels,
        prior,
        num_histogram_bins
    )

    seeds.iterate(bgr_img, num_iterations)

    # Label map returned by SEEDS
    superpixels = seeds.getLabels()    # shape (H, W)

    # Show SLIC superpixels
    fig = plt.figure(f"Superpixels — {n_segments} segments")
    ax = fig.add_subplot(1, 1, 1)
    ax.imshow(mark_boundaries(np_img, superpixels))
    plt.axis("off")
    plt.show()

    # --- Superpixel refinement ---
    min_fraction = 0.05    # at least 10% of pixels predicted leaf
    min_conf     = 0.2    # mean probability in superpixel

    refined_leaf_mask = np.zeros_like(leaf_mask)

    for sp_id in np.unique(superpixels):
        sp_region = (superpixels == sp_id)

        fraction = leaf_mask[sp_region].mean()
        conf     = leaf_prob[sp_region].mean()

        if fraction >= min_fraction and conf >= min_conf:
            refined_leaf_mask[sp_region] = True

    refined_leaf_overlay = overlay_mask(
        np_img,
        refined_leaf_mask,
        (50,180,50),
        alpha=0.55
    )
    refined_leaf_overlay.show()

    # ------------------------------------------------------------
    # 3) MMSFormer natural textures panel (grass, wood, leaf, etc.)
    # ------------------------------------------------------------
    nat_score, _ = calc_natural_texture_presence(
        image_path,
        device=DEVICE,
        model=MMS_MODEL,
        natural_labels=NATURAL_LABELS,
    )
    print(f"Natural texture presence: {nat_score:.3f}")

    nat_overlay, legend_entries = build_natural_overlay(
        mms,
        np_img,
        labels=NATURAL_LABELS,
    )
    nat_img = Image.fromarray(nat_overlay)
    nat_img = draw_legend(nat_img, legend_entries)

    # ------------------------------------------------------------
    # 4-panel output
    # ------------------------------------------------------------
    out = create_side_by_side(
        img,
        leaf_overlay,
        refined_leaf_overlay,
        nat_img,
        labels=[
            "Original",
            "MMSFormer: Leaf Only",
            "Refined via Superpixels",
            "MMSFormer: Natural Textures"
        ]
    )

    out.save("diagnostic_4panel.png")
    print("Saved → diagnostic_4panel.png")


# -------------------------------------------------------------------
# CLI Entry
# -------------------------------------------------------------------
if __name__ == "__main__":
    run_test("data/in4.jpg")
