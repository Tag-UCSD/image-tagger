# run_mmsformer.py

import torch
import numpy as np
from torchvision import transforms as T
from PIL import Image

def run_mmsformer(image: Image.Image, model, device="cpu") -> dict:
    """
    Wrapper for MMSFormer image processing/segmentation.

    Returns:
        {
            "classes": list of class names,
            "masks": list of HxW boolean masks (per class),
            "scores": list of floats (mean prob per class region),
            "meta": {
                "logits": np array [C,H,W]
            }
        }
    """

    tf = T.Compose([
        T.ToTensor(),
        T.Normalize((0.485,0.456,0.406),(0.229,0.224,0.225))
    ])

    img_tensor = tf(image).unsqueeze(0).to(device)

    with torch.no_grad():
        output = model([img_tensor])[0]

    logits = output.detach().cpu()
    H, W = logits.shape[1:]

    # get probabilities & class labels using softmax fn & argmax
    probs = torch.softmax(logits, dim=0).numpy() 
    seg_map = logits.argmax(dim=0).numpy()

    classes = [
        'asphalt','concrete','metal','road_marking','fabric','glass','plaster',
        'plastic','rubber','sand','gravel','ceramic','cobblestone','brick',
        'grass','wood','leaf','water','human','sky'
    ]

    masks = []
    scores = []

    for class_id, class_name in enumerate(classes):
        mask = (seg_map == class_id)

        if mask.sum() == 0:
            continue

        # average class probability over pixels in this mask
        class_prob = probs[class_id][mask].mean().item()

        masks.append(mask)
        scores.append(class_prob)

    return {
        "classes": classes,
        "masks": masks,
        "scores": scores,
        "meta": {
            "logits": logits.numpy()
        }
    }
