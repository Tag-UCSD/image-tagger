\
#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, hashlib
from pathlib import Path

def die(msg: str) -> None:
    print(f"NO-GO: {msg}")
    sys.exit(2)

def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def find_first_yaml(registry_dir: Path) -> Path:
    cands = sorted(list(registry_dir.glob("*.yml")) + list(registry_dir.glob("*.yaml")))
    if not cands:
        die(f"No YAML registry found in {registry_dir}")
    return cands[0]

def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    env_path = repo / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

    ver = os.getenv("TRS_CORE_VER", "").strip()
    if not ver:
        die("TRS_CORE_VER is not set. Add it to .env (e.g., TRS_CORE_VER=v0.2.8).")

    core = repo / "core" / "trs-core" / ver
    if not core.exists():
        die(f"Core bundle folder missing: {core}")

    expected = ["registry", "contracts", "schemas", "vendor_specs"]
    for sub in expected:
        p = core / sub
        if not p.exists():
            die(f"Missing core subfolder: {p}")

    # Quick registry parse + tag count (no heavy validation yet)
    import yaml
    reg_yaml = find_first_yaml(core / "registry")
    reg = yaml.safe_load(reg_yaml.read_text(encoding="utf-8"))
    tags = reg.get("tags", {})
    if isinstance(tags, dict):
        tag_count = len(tags)
    elif isinstance(tags, list):
        tag_count = len(tags)
    else:
        tag_count = 0

    contracts = sorted((core / "contracts").glob("*.json"))
    if not contracts:
        die(f"No contract JSON files found in {core/'contracts'}")

    # Requirements sanity (catch the exact failure you saw)
    for req in [repo/"backend"/"requirements.txt", repo/"frontend_streamlit"/"requirements.txt"]:
        if req.exists():
            txt = req.read_text(encoding="utf-8", errors="ignore")
            if "cat >" in txt or "<< 'EOF'" in txt or "EOF" in txt and "==" not in txt:
                die(f"requirements file looks corrupted (contains shell heredoc): {req}")

    report = {
        "GO": True,
        "repo": str(repo),
        "core_version": ver,
        "registry_file": str(reg_yaml),
        "registry_sha256": sha256_path(reg_yaml),
        "tag_count": tag_count,
        "contracts_count": len(contracts),
    }
    print("GO: doctor checks passed.")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
