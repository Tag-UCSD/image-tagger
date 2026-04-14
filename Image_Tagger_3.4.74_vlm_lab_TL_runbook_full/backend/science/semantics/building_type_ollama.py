"""
Classify building type from an image using a local Ollama LLaVA 13B model.

Sends an image to Ollama's LLaVA model and returns 1-3 building-type tags
from a fixed canonical list. Designed to run standalone or be imported into
the science pipeline.

Requirements:
    - Ollama running locally (default: http://localhost:11434)
    - LLaVA 13B pulled: `ollama pull llava:13b`

Usage:
    python -m backend.science.semantics.building_type_ollama path/to/image.jpg
    python -m backend.science.semantics.building_type_ollama path/to/image.jpg --url http://host:11434
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_DEFAULT_URL = "http://localhost:11434"
MODEL = "llava:13b"

BUILDING_TYPES = [
    "Residential",
    "Hospitality",
    "Workplace / Office",
    "Education",
    "Healthcare",
    "Retail / Commerce",
    "Food & Beverage",
    "Civic / Government",
    "Cultural / Museum / Gallery",
    "Religious / Spiritual",
    "Industrial / Workshop",
    "Transport / Mobility",
]

BUILDING_TYPE_LIST = "\n".join(f"- {bt}" for bt in BUILDING_TYPES)

PROMPT = (
    "You are an architectural classification expert.\n"
    "Look at this photograph and determine which building type(s) it depicts.\n\n"
    "Choose between 1 and 3 types from ONLY this list:\n"
    f"{BUILDING_TYPE_LIST}\n\n"
    "Return ONLY a JSON object with a single key \"building_types\" whose value "
    "is an array of 1 to 3 strings copied exactly from the list above.\n"
    "Example: {\"building_types\": [\"Residential\", \"Hospitality\"]}\n"
    "Do not add commentary or explanation."
)


def _encode_image(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def _parse_response(raw: str) -> List[str]:
    """Extract building_types array from model output, tolerating markdown fences."""
    cleaned = raw.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(cleaned[start : end + 1])
        else:
            raise

    types = data.get("building_types", [])
    if isinstance(types, str):
        types = [types]

    valid = [t for t in types if t in BUILDING_TYPES]
    return valid[:3]


def classify_building_type(
    image_path: Path,
    ollama_url: str = OLLAMA_DEFAULT_URL,
    model: str = MODEL,
) -> List[str]:
    """Send an image to Ollama LLaVA and return 1-3 building-type tags."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    b64_image = _encode_image(image_path)

    payload = {
        "model": model,
        "prompt": PROMPT,
        "images": [b64_image],
        "stream": False,
    }

    resp = requests.post(
        f"{ollama_url}/api/generate",
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()

    raw_text = resp.json().get("response", "")
    logger.debug("Ollama raw response: %s", raw_text)

    return _parse_response(raw_text)


def building_types_to_tags(types: List[str]) -> List[dict]:
    """Convert building-type strings to canonical tag dicts matching the repo format."""
    tags = []
    for bt in types:
        safe_key = bt.lower().replace(" / ", "_").replace(" & ", "_").replace(" ", "_")
        tags.append({
            "tag_key": f"building_type.{safe_key}",
            "label": bt,
            "namespace": "building_type",
            "source_analyzer": "ollama_llava_13b",
        })
    return tags


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Classify building type from an image via local Ollama LLaVA 13B."
    )
    parser.add_argument("image", type=Path, help="Path to an image file (JPEG/PNG)")
    parser.add_argument(
        "--url",
        default=OLLAMA_DEFAULT_URL,
        help=f"Ollama server URL (default: {OLLAMA_DEFAULT_URL})",
    )
    parser.add_argument(
        "--model",
        default=MODEL,
        help=f"Ollama model name (default: {MODEL})",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print(f"Classifying: {args.image}")
    print(f"Model:       {args.model}")
    print(f"Server:      {args.url}")
    print()

    try:
        types = classify_building_type(args.image, ollama_url=args.url, model=args.model)
    except requests.ConnectionError:
        print("ERROR: Cannot connect to Ollama. Is it running?", file=sys.stderr)
        print(f"  Start with: ollama serve", file=sys.stderr)
        print(f"  Pull model: ollama pull {args.model}", file=sys.stderr)
        sys.exit(1)

    if not types:
        print("No valid building types detected.")
        sys.exit(0)

    tags = building_types_to_tags(types)

    print(f"Detected {len(types)} building type(s):\n")
    for tag in tags:
        print(f"  Tag key: {tag['tag_key']}")
        print(f"  Label:   {tag['label']}")
        print()

    print("Raw tags JSON:")
    print(json.dumps(tags, indent=2))


if __name__ == "__main__":
    main()
