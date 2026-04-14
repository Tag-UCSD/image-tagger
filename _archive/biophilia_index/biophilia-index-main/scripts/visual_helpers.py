# visual_helpers.py

import numpy as np
from PIL import Image, ImageDraw, ImageFont

def overlay_mask(image, mask, color=(0,255,0), alpha=0.4):
    """Simple visualization helper."""
    base = np.array(image).astype(float)
    overlay = base.copy()
    overlay[mask] = color
    out = (alpha * overlay + (1-alpha) * base).astype(np.uint8)
    return Image.fromarray(out)

def draw_legend(img, entries, start_xy=(10, 10)):
    """
    entries = list of (label, color)
    """
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("Verdana.ttf", 16)
    except:
        font = ImageFont.load_default()

    x0, y0 = start_xy
    box = 22
    pad = 6

    for i, (name, col) in enumerate(entries):
        y = y0 + i * (box + pad)
        draw.rectangle([(x0, y), (x0+box, y+box)], fill=col, outline="white")
        draw.text((x0+box+8, y), name, fill="white", font=font)

    return img

def create_side_by_side(*images, labels):
    """
    images: list of PIL images of same size
    labels: same length list of titles
    """
    w, h = images[0].size
    N = len(images)

    canvas = Image.new("RGB", (w*N, h), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype("Verdana.ttf", 24)
    except:
        font = ImageFont.load_default()

    for i, im in enumerate(images):
        canvas.paste(im, (i*w, 0))
        draw.text((i*w + 10, 10), labels[i], fill="white", font=font)

    return canvas