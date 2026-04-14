import os
from pathlib import Path

def _guess_repo_root() -> Path:
    here = Path(__file__).resolve()

    # Host layout: <repo>/backend/app/settings.py -> parents[2] == <repo>
    if len(here.parents) >= 3 and (here.parents[2] / "core").exists():
        return here.parents[2]

    # Container layout: WORKDIR is /app and /app/core exists
    if Path("/app/core").exists():
        return Path("/app")

    # Fallback
    return Path.cwd()

REPO_ROOT = _guess_repo_root()

CORE_VER = os.getenv("TRS_CORE_VER", "v0.2.8")
CORE_ROOT = REPO_ROOT / "core" / "trs-core" / CORE_VER

REGISTRY_DIR = CORE_ROOT / "registry"
CONTRACTS_DIR = CORE_ROOT / "contracts"
SCHEMAS_DIR = CORE_ROOT / "schemas"
VENDOR_DIR = CORE_ROOT / "vendor_specs"
