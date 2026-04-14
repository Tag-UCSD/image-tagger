import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from .settings import REGISTRY_DIR, CONTRACTS_DIR, SCHEMAS_DIR, VENDOR_DIR
from .registry_loader import load_registry

router = APIRouter()

def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def list_files(dirp: Path, pattern: str):
    return sorted([p for p in dirp.glob(pattern) if p.is_file()])

@router.get("/health")
def health():
    return {"ok": True}

@router.get("/status")
def status():
    reg = load_registry(REGISTRY_DIR)
    tags = reg.get("tags", {})
    if isinstance(tags, dict):
        tag_count = len(tags)
    elif isinstance(tags, list):
        tag_count = len(tags)
    else:
        tag_count = 0
    return {
        "core_version": str(REGISTRY_DIR.parent.name),
        "core_paths": {
            "registry_dir": str(REGISTRY_DIR),
            "contracts_dir": str(CONTRACTS_DIR),
            "schemas_dir": str(SCHEMAS_DIR),
            "vendor_specs_dir": str(VENDOR_DIR),
        },
        "counts": {
            "tag_count": tag_count,
            "contracts_files": len(list_files(CONTRACTS_DIR, "*.json")),
            "schema_files": len([p for p in SCHEMAS_DIR.rglob("*") if p.is_file()]),
        },
    }

@router.get("/registry")
def get_registry():
    return load_registry(REGISTRY_DIR)

@router.get("/contracts/latest")
def get_contract_latest(consumer: str = Query(..., min_length=1)):
    files = list_files(CONTRACTS_DIR, "*.json")
    matches = [p for p in files if consumer.lower() in p.name.lower()]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No contract found for consumer={consumer}. Available: {[p.name for p in files]}")
    return read_json(matches[-1])

@router.get("/schemas/{path:path}")
def get_schema(path: str):
    p = (SCHEMAS_DIR / path).resolve()
    if not str(p).startswith(str(SCHEMAS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Bad schema path")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"path": path, "content": p.read_text(encoding="utf-8", errors="ignore")}

@router.get("/resolve")
def resolve_term(term: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    reg = load_registry(REGISTRY_DIR)
    tags = reg.get("tags", {})
    term_l = term.strip().lower()
    results = []

    if isinstance(tags, dict):
        items = tags.items()
    elif isinstance(tags, list):
        items = [(t.get("canonical_id") or t.get("tag_id") or t.get("id"), t) for t in tags if isinstance(t, dict)]
    else:
        items = []

    def aliases_for(obj: dict) -> list[str]:
        out = []
        sem = obj.get("semantics")
        if isinstance(sem, dict):
            for key in ("aliases", "synonyms", "search_terms"):
                a = sem.get(key)
                if isinstance(a, list):
                    out.extend([str(x) for x in a])
        for k in ("canonical_name", "attribute_id", "label", "name"):
            v = obj.get(k)
            if isinstance(v, str):
                out.append(v)
        return [x for x in out if x]

    for tag_id, obj in items:
        if not tag_id or not isinstance(obj, dict):
            continue
        hay = " | ".join([str(tag_id)] + aliases_for(obj)).lower()
        if term_l in hay:
            results.append({
                "tag_id": tag_id,
                "canonical_name": obj.get("canonical_name") or obj.get("name"),
                "status": obj.get("status"),
                "value_type": obj.get("value_type"),
                "domain": obj.get("domain"),
                "subdomain": obj.get("subdomain"),
            })
            if len(results) >= limit:
                break

    return {"term": term, "matches": results}
