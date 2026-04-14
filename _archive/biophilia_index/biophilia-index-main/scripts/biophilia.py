import argparse
import yaml
from pathlib import Path

from plant_presence import calc_plant_presence, load_rcnn as load_plant_model
from natural_texture_presence import (
    calc_natural_texture_presence,
    load_mmsformer_model,
    NATURAL_LABELS,
)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("biophilia_config.yaml")


def load_biophilia_config(config_path=DEFAULT_CONFIG_PATH):
    """
    Load YAML config, resolving relative paths sensibly:
    - Absolute paths are used as-is.
    - Relative paths are first tried against the current working directory.
    - If not found, they are resolved relative to this file's directory.
    """
    cfg_path = Path(config_path)
    if not cfg_path.is_absolute():
        candidate = Path.cwd() / cfg_path
        cfg_path = candidate if candidate.exists() else DEFAULT_CONFIG_PATH.parent / cfg_path
    cfg_path = cfg_path.resolve()

    with open(cfg_path) as f:
        return yaml.safe_load(f)


def _normalize_weights(factors_cfg):
    enabled = {
        name: settings
        for name, settings in factors_cfg.items()
        if settings.get("enabled", True)
    }
    if not enabled:
        raise ValueError("No factors enabled in config.")

    total_weight = sum(settings.get("weight", 0.0) for settings in enabled.values())
    if total_weight <= 0:
        raise ValueError("Enabled factors must have positive weights.")

    for settings in enabled.values():
        settings["_normalized_weight"] = settings.get("weight", 0.0) / total_weight
    return enabled


def compute_biophilic_index(image_path: str, config_path=DEFAULT_CONFIG_PATH):
    """
    Compute the biophilic index as weighted sum of enabled factors.
    """
    cfg = load_biophilia_config(config_path)
    factors_cfg = cfg.get("factors", {})
    enabled_factors = _normalize_weights(factors_cfg)

    results = {}
    total_score = 0.0

    # Lazily load heavy models once
    plant_model_cache = {}
    natural_model_cache = {}

    for name, settings in enabled_factors.items():
        weight = settings["_normalized_weight"]
        params = settings.get("params", {})
        device = params.get("device", "cpu")

        if name == "plant_presence":
            if device not in plant_model_cache:
                plant_model_cache[device] = load_plant_model(device=device)

            viz_dir = params.get("viz_dir")
            viz_path = None
            if params.get("visualize"):
                if viz_dir:
                    viz_dir_path = Path(viz_dir)
                    if not viz_dir_path.is_absolute():
                        candidate = Path.cwd() / viz_dir_path
                        viz_dir_path = (
                            candidate
                            if candidate.exists()
                            else DEFAULT_CONFIG_PATH.parent / viz_dir_path
                        )
                    viz_dir_path.mkdir(parents=True, exist_ok=True)
                else:
                    viz_dir_path = Path(image_path).parent
                viz_path = viz_dir_path / f"{Path(image_path).stem}_plant_overlay.png"

            score, uncertainty, _ = calc_plant_presence(
                image_path,
                confidence_threshold=params.get("confidence_threshold", 0.5),
                visualize=params.get("visualize", False),
                viz_path=viz_path,
                device=device,
                model=plant_model_cache[device],
            )
            results[name] = {
                "score": score,
                "weight": weight,
                "uncertainty": uncertainty,
                "viz_path": str(viz_path) if params.get("visualize") else None,
            }
            total_score += weight * score
        elif name == "natural_texture_presence":
            config_override = params.get("config_path")
            effective_cfg_path = Path(
                config_override if config_override is not None else config_path
            )
            if not effective_cfg_path.is_absolute():
                cwd_candidate = Path.cwd() / effective_cfg_path
                effective_cfg_path = (
                    cwd_candidate
                    if cwd_candidate.exists()
                    else DEFAULT_CONFIG_PATH.parent / effective_cfg_path
                )

            cache_key = (effective_cfg_path.resolve(), device)
            if cache_key not in natural_model_cache:
                natural_model_cache[cache_key] = load_mmsformer_model(
                    config_path=effective_cfg_path,
                    device=device,
                )[0]

            nat_viz_path = None
            if params.get("visualize"):
                viz_dir = params.get("viz_dir")
                if viz_dir:
                    viz_dir_path = Path(viz_dir)
                    if not viz_dir_path.is_absolute():
                        candidate = Path.cwd() / viz_dir_path
                        viz_dir_path = (
                            candidate
                            if candidate.exists()
                            else DEFAULT_CONFIG_PATH.parent / viz_dir_path
                        )
                    viz_dir_path.mkdir(parents=True, exist_ok=True)
                else:
                    viz_dir_path = Path(image_path).parent
                nat_viz_path = viz_dir_path / f"{Path(image_path).stem}_natural_overlay.png"

            score, details = calc_natural_texture_presence(
                image_path,
                device=device,
                model=natural_model_cache[cache_key],
                config_path=effective_cfg_path,
                natural_labels=params.get("natural_labels", NATURAL_LABELS),
                visualize=params.get("visualize", False),
                viz_path=nat_viz_path,
                refine_with_superpixels=params.get("refine_with_superpixels", False),
                min_fraction=params.get("min_fraction", 0.05),
                min_conf=params.get("min_conf", 0.2),
                num_superpixels=params.get("num_superpixels", 300),
                num_levels=params.get("num_levels", 4),
                prior=params.get("prior", 2),
                num_histogram_bins=params.get("num_histogram_bins", 5),
                num_iterations=params.get("num_iterations", 10),
            )
            results[name] = {
                "score": score,
                "weight": weight,
                "per_class_presence": details["per_class_presence"],
                "viz_path": details.get("viz_path"),
            }
            total_score += weight * score
        else:
            raise ValueError(f"Unknown factor '{name}' in config.")

    return total_score, results


def main():
    parser = argparse.ArgumentParser(description="Compute biophilic index for an image.")
    parser.add_argument("--image", type=str, required=True, help="Path to image file.")
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to biophilia config YAML.",
    )
    args = parser.parse_args()

    score, breakdown = compute_biophilic_index(args.image, config_path=args.config)

    print(f"Biophilic index: {score:.4f}")
    for name, data in breakdown.items():
        print(f" - {name}: score={data['score']:.4f}, weight={data['weight']:.3f}")


if __name__ == "__main__":
    main()
