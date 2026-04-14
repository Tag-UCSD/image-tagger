from pathlib import Path
import yaml

def _first_yaml(registry_dir: Path) -> Path:
    yamls = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not yamls:
        raise FileNotFoundError(f"No registry YAML found in {registry_dir}")
    return yamls[0]

def load_registry(registry_dir: Path) -> dict:
    p = _first_yaml(registry_dir)
    return yaml.safe_load(p.read_text(encoding="utf-8"))
