import torch
import numpy as np
import cv2
from torchvision.models.detection import maskrcnn_resnet50_fpn
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
from pathlib import Path

_MODEL_CACHE = {}

def load_rcnn(device="cpu"):
    """
    Load a pretrained COCO Mask R-CNN model.
    Cached per-device to avoid repeated heavyweight loads.
    """
    if device in _MODEL_CACHE:
        return _MODEL_CACHE[device]

    model = maskrcnn_resnet50_fpn(weights="COCO_V1")
    model.to(device)
    model.eval()
    _MODEL_CACHE[device] = model
    return model

# --- image load and preprocessing

def get_image(image_path: str) -> Image.Image:
    """Load an image from a local filesystem path."""
    return Image.open(image_path).convert("RGB")

def preprocess_image(img: Image.Image):
    """Convert to tensor and return both transform & tensor."""
    transform = transforms.ToTensor()
    img_tensor = transform(img)
    return img_tensor

# --- mask utility fns.

def merge_overlapping_masks(masks, iou_thresh=0.3, dilate=True):
    """
    Merge masks that have IoU overlap greater than threshold.
    Uses a small dilation step to encourage merging of close regions.
    """
    merged, used = [], set()
    n = len(masks)

    if dilate:
        kernel = np.ones((5, 5), np.uint8)
        masks = [cv2.dilate((m > 0.5).astype(np.uint8), kernel, 1) for m in masks]
    else:
        masks = [(m > 0.5).astype(np.uint8) for m in masks]

    for i in range(n):
        if i in used:
            continue

        cur = masks[i].copy()

        # Try merging with later masks
        for j in range(i + 1, n):
            if j in used:
                continue

            inter = np.logical_and(cur, masks[j]).sum()
            union = np.logical_or(cur, masks[j]).sum()
            iou = inter / union if union > 0 else 0.0

            if iou > iou_thresh:
                cur = np.logical_or(cur, masks[j])
                used.add(j)

        used.add(i)
        merged.append(cur.astype(float))

    return merged

# --- visualization utility fns

def _visualize_detection(img, masks, scores, presence, uncertainty, save_path=None):
    """Simple overlay visualization. Saves if save_path is provided."""
    overlay = np.array(img) / 255.0
    combined = np.clip(np.sum(masks, axis=0), 0, 1)

    # Highlight plant in green channel
    overlay[..., 1] = np.clip(overlay[..., 1] + 0.5 * combined, 0, 1)

    plt.figure(figsize=(8, 6))
    plt.imshow((overlay * 255).astype(np.uint8))
    plt.title(f"Plant presence={presence:.2f}, uncertainty={uncertainty:.2f}")
    plt.axis("off")

    # Add text labels per region
    for m, s in zip(masks, scores):
        ys, xs = np.where(m > 0.5)
        if len(xs) == 0:
            continue
        cx, cy = int(np.mean(xs)), int(np.mean(ys))
        plt.text(
            cx, cy,
            f"{s:.2f}",
            color="white",
            fontsize=8,
            ha="center", va="center",
            bbox=dict(facecolor="black", alpha=0.5, edgecolor="none"),
        )

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, bbox_inches="tight", dpi=200)
        plt.close()
    else:
        plt.show()

# --- main

def calc_plant_presence(
    image_url: str,
    confidence_threshold=0.5,
    visualize=False,
    viz_path=None,
    device="cpu",
    model=None,
):
    """
    Compute plant presence score and uncertainty from an image.

    Returns:
        plant_presence (float),
        uncertainty (float),
        keep_indices (List[int]) – indices of plant detections before merging
    """
    if model is None:
        model = load_rcnn(device)

    image_path = Path(image_url)

    # Download + preprocess
    img = get_image(str(image_path))
    img_tensor = preprocess_image(img).to(device)
    H, W = img_tensor.shape[1:]

    PLANT_LABEL_ID = 64

    # Inference
    with torch.no_grad():
        pred = model([img_tensor])[0]

    # Filter detections for plant label
    keep = [i for i, l in enumerate(pred["labels"]) if l.item() == PLANT_LABEL_ID]

    if not keep:
        return 0.0, 1.0, []

    masks = pred["masks"][keep, 0].cpu().numpy()
    scores = [pred["scores"][i].item() for i in keep]
    merged_masks = merge_overlapping_masks(masks)

    # Confidence filtering
    filtered = [(m, s) for m, s in zip(merged_masks, scores) if s >= confidence_threshold]

    if not filtered:
        return 0.0, 1.0, keep

    merged_masks, scores = zip(*filtered)
    merged_masks, scores = list(merged_masks), list(scores)

    # Weighted area using the original masks before merge
    weighted_area = sum(m.sum() * s for m, s in zip(masks, scores))
    total_area = H * W

    plant_presence = float(np.clip(weighted_area / total_area, 0, 1))
    uncertainty = float(1.0 - np.mean(scores))

    if visualize:
        if viz_path is None:
            viz_path = Path(image_path).with_suffix(".plant_overlay.png")
        _visualize_detection(img, merged_masks, scores, plant_presence, uncertainty, save_path=viz_path)

    return plant_presence, uncertainty, keep

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Compute plant presence score.")
    parser.add_argument("--image", type=str, required=True, help="URL of the image")
    parser.add_argument("--conf", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--viz", action="store_true", help="Enable visualization")

    args = parser.parse_args()

    presence, uncertainty, keep = calc_plant_presence(
        args.image,
        confidence_threshold=args.conf,
        visualize=args.viz,
    )

    print("Plant presence:", presence)
    print("Uncertainty:", uncertainty)
    print("Detections kept:", keep)


if __name__ == "__main__":
    main()
