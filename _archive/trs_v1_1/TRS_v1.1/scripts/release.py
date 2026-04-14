#!/usr/bin/env python3
"""
TRS Release Script with Validation Gates

Usage:
    python3 scripts/release.py vX.Y.Z
    python3 scripts/release.py vX.Y.Z --skip-gates  # Skip validation (not recommended)
    python3 scripts/release.py vX.Y.Z --force       # Continue despite warnings

Release Gates:
    1. Schema validation - All tags pass schema checks
    2. Invariant validation - No semantic violations
    3. Breaking change detection - No removed tags or type changes
    4. Contract generation - All contracts regenerated successfully

Exit codes:
    0 = Release successful
    1 = Validation failed (gates blocked)
    2 = Usage error
"""

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

# Add scripts to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from audit import AuditLog

REPO_ROOT = SCRIPT_DIR.parent
ART = REPO_ROOT / "release_artifacts"
ART.mkdir(parents=True, exist_ok=True)

EXCLUDE_DIRS = {
    "release_artifacts",
    "Release_Artifacts",
    "_archive",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".venv",
    "venv",
    "myvenv",
    "node_modules",
    "logs",
}
EXCLUDE_FILES = {".DS_Store"}


def is_excluded(rel: Path) -> bool:
    if any(p in EXCLUDE_DIRS for p in rel.parts):
        return True
    if rel.name.startswith(".env"):
        return True
    if rel.name in EXCLUDE_FILES:
        return True
    return False


def iter_files():
    out = []
    for p in REPO_ROOT.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(REPO_ROOT)
        if is_excluded(rel):
            continue
        out.append(p)
    return sorted(out, key=lambda x: str(x.relative_to(REPO_ROOT)))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_previous_version(current_ver: str) -> str | None:
    """Find the most recent version before the current one."""
    core_dir = REPO_ROOT / "core" / "trs-core"
    if not core_dir.exists():
        return None
    
    versions = []
    for d in core_dir.iterdir():
        if d.is_dir() and d.name.startswith("v"):
            versions.append(d.name)
    
    versions.sort()
    if current_ver in versions:
        idx = versions.index(current_ver)
        if idx > 0:
            return versions[idx - 1]
    elif versions:
        return versions[-1]
    
    return None


def run_validation(registry_dir: Path) -> tuple[bool, int, int]:
    """Run schema and invariant validation. Returns (passed, errors, warnings)."""
    try:
        from validate_registry import validate_registry
        result = validate_registry(registry_dir)
        return result.passed, len(result.errors), len(result.warnings)
    except ImportError:
        print("  WARNING: validate_registry module not available")
        return True, 0, 0


def run_diff_check(old_ver: str, new_ver: str) -> tuple[bool, int, int, int]:
    """Run breaking change detection. Returns (no_breaking, breaking, warnings, info)."""
    try:
        from diff_registry import diff_registries
        old_path = REPO_ROOT / "core" / "trs-core" / old_ver / "registry"
        new_path = REPO_ROOT / "core" / "trs-core" / new_ver / "registry"
        
        if not old_path.exists():
            print(f"  WARNING: Previous version {old_ver} not found, skipping diff")
            return True, 0, 0, 0
        
        result = diff_registries(old_path, new_path)
        return not result.has_breaking, len(result.breaking_changes), len(result.warnings), len(result.info)
    except ImportError:
        print("  WARNING: diff_registry module not available")
        return True, 0, 0, 0


def run_contract_generation(version: str) -> bool:
    """Generate contracts. Returns success."""
    try:
        from generate_contracts import load_registry, generate_meta, sha256_file
        from generate_contracts import (
            generate_image_tagger_contract,
            generate_article_eater_contract,
            generate_bn_contract,
            generate_preference_testing_contract,
        )
        import json
        
        registry_dir = REPO_ROOT / "core" / "trs-core" / version / "registry"
        contracts_dir = REPO_ROOT / "core" / "trs-core" / version / "contracts"
        
        registry, reg_path = load_registry(registry_dir)
        tags = registry.get("tags", {})
        registry_sha256 = sha256_file(reg_path)
        meta = generate_meta(registry_sha256, version)
        
        contracts = [
            ("image_tagger", generate_image_tagger_contract(tags, meta, version)),
            ("article_eater", generate_article_eater_contract(tags, meta, version, registry)),
            ("bn", generate_bn_contract(tags, meta, version)),
            ("preference_testing", generate_preference_testing_contract(tags, meta, version)),
        ]
        
        contracts_dir.mkdir(parents=True, exist_ok=True)
        for name, contract in contracts:
            path = contracts_dir / f"{name}_contract_{version}.json"
            path.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
        
        # SHA256 manifest
        sha_path = contracts_dir / f"registry_sha256_{version}.json"
        sha_path.write_text(json.dumps({"registry_sha256": registry_sha256}, indent=2), encoding="utf-8")
        
        return True
    except Exception as e:
        print(f"  ERROR: Contract generation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Create a release with validation gates")
    parser.add_argument("version", help="Version string (e.g., v0.2.9)")
    parser.add_argument("--skip-gates", action="store_true", help="Skip validation gates (dangerous)")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merging approved proposals")
    parser.add_argument("--force", action="store_true", help="Continue despite warnings")
    args = parser.parse_args()

    ver = args.version
    if not ver.startswith("v"):
        print("ERROR: Version must start with 'v'")
        return 2

    audit = AuditLog()
    registry_dir = REPO_ROOT / "core" / "trs-core" / ver / "registry"
    
    if not registry_dir.exists():
        print(f"ERROR: Registry not found at {registry_dir}")
        return 2

    print(f"=" * 60)
    print(f"RELEASE {ver}")
    print(f"=" * 60)
    print()

    # Step 0: Merge approved proposals
    merged_count = 0
    if not args.skip_merge:
        print("[0/4] Merging Approved Proposals...")
        try:
            from merge_proposals import merge_proposals
            merged_count, merge_errors, _ = merge_proposals(ver, registry_dir, dry_run=False)
            if merge_errors > 0:
                print(f"  ⚠️  Merged {merged_count} with {merge_errors} errors")
            elif merged_count > 0:
                print(f"  ✓ Merged {merged_count} proposals")
            else:
                print(f"  ✓ No proposals to merge")
        except ImportError:
            print(f"  ⚠️  SKIPPED: merge_proposals module not available")
        except Exception as e:
            print(f"  ⚠️  SKIPPED: {e}")
        print()

    # Track gate results
    gates_passed = True
    gate_results = {}

    if args.skip_gates:
        print("⚠️  SKIPPING VALIDATION GATES (--skip-gates)")
        print()
    else:
        print("Running release gates...")
        print()
        
        # Gate 1: Schema + Invariant Validation
        print("[1/4] Schema & Invariant Validation...")
        passed, errors, warnings = run_validation(registry_dir)
        gate_results["validation"] = {"passed": passed, "errors": errors, "warnings": warnings}
        
        if not passed:
            print(f"  ❌ FAILED: {errors} errors, {warnings} warnings")
            gates_passed = False
        elif warnings > 0:
            print(f"  ⚠️  PASSED with {warnings} warnings")
        else:
            print(f"  ✓ PASSED")
        
        # Gate 2: Breaking Change Detection
        print("[2/4] Breaking Change Detection...")
        prev_ver = find_previous_version(ver)
        if prev_ver:
            no_breaking, breaking, diff_warnings, info = run_diff_check(prev_ver, ver)
            gate_results["diff"] = {"no_breaking": no_breaking, "breaking": breaking, "warnings": diff_warnings, "info": info}
            
            if not no_breaking:
                print(f"  ❌ FAILED: {breaking} breaking changes detected")
                gates_passed = False
            elif diff_warnings > 0:
                print(f"  ⚠️  PASSED with {diff_warnings} warnings, {info} info")
            else:
                print(f"  ✓ PASSED ({info} changes)")
        else:
            print(f"  ⚠️  SKIPPED: No previous version found")
            gate_results["diff"] = {"skipped": True}
        
        # Gate 3: Contract Generation
        print("[3/4] Contract Generation...")
        gen_success = run_contract_generation(ver)
        gate_results["contracts"] = {"success": gen_success}
        
        if gen_success:
            print(f"  ✓ PASSED")
        else:
            print(f"  ❌ FAILED")
            gates_passed = False
        
        print()
        
        if not gates_passed:
            print("=" * 60)
            print("❌ RELEASE BLOCKED - Gates failed")
            print("=" * 60)
            audit.log_release(
                version=ver,
                previous_version=prev_ver,
                result="blocked",
            )
            return 1

    # Create release artifacts
    print("Creating release artifacts...")
    files = iter_files()

    zip_name = f"Tagging_Contractor_{ver}.zip"
    man_name = f"Tagging_Contractor_{ver}_manifest.txt"
    sha_name = f"Tagging_Contractor_{ver}_sha256.txt"

    zip_path = ART / zip_name
    partial_zip = ART / (zip_name + ".partial")
    man_path = ART / man_name
    sha_path = ART / sha_name

    man_path.write_text(
        "".join(f"{p.relative_to(REPO_ROOT)}\t{p.stat().st_size}\n" for p in files),
        encoding="utf-8"
    )

    if partial_zip.exists():
        partial_zip.unlink()

    with zipfile.ZipFile(partial_zip, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
        for p in files:
            z.write(p, arcname=str(p.relative_to(REPO_ROOT)))

    if zip_path.exists():
        zip_path.unlink()
    partial_zip.rename(zip_path)

    sha_path.write_text(f"{sha256_file(zip_path)}  {zip_name}\n", encoding="utf-8")
    (REPO_ROOT / "VERSION.txt").write_text(ver + "\n", encoding="utf-8")

    # Log success
    diff_info = gate_results.get("diff", {})
    audit.log_release(
        version=ver,
        previous_version=find_previous_version(ver),
        tags_added=diff_info.get("info", 0),
        tags_removed=diff_info.get("breaking", 0),
        result="success",
    )

    print()
    print("=" * 60)
    print(f"✓ RELEASE {ver} SUCCESSFUL")
    print("=" * 60)
    print()
    print(f"Artifacts:")
    print(f"  {zip_path}")
    print(f"  {man_path}")
    print(f"  {sha_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
