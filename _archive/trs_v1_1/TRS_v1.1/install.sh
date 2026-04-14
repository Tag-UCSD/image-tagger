#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

say(){ printf "%s\n" "$*"; }

ensure_exec_bits(){
  chmod +x "$REPO_ROOT/bin/tc" 2>/dev/null || true
  chmod +x "$REPO_ROOT/scripts/release.py" 2>/dev/null || true
}

ensure_env(){
  if [[ ! -f "$REPO_ROOT/.env" ]]; then
    if [[ -f "$REPO_ROOT/.env.example" ]]; then
      cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
      say "Created .env from .env.example"
    else
      cat > "$REPO_ROOT/.env" << 'E'
TRS_CORE_VER=v0.2.8
TRS_API_PORT=8401
TRS_UI_PORT=8501
E
      say "Created default .env"
    fi
  fi
}

preflight(){
  say "== Tagging_Contractor Turnkey Installer =="
  say "Repo: $REPO_ROOT"
  command -v docker >/dev/null 2>&1 || { say "NO-GO: docker not found. Install Docker Desktop."; exit 2; }
  docker compose version >/dev/null 2>&1 || { say "NO-GO: docker compose not available."; exit 2; }
  [[ -f "$REPO_ROOT/docker-compose.yml" ]] || { say "NO-GO: missing docker-compose.yml"; exit 2; }
  [[ -f "$REPO_ROOT/Dockerfile.api" ]] || { say "NO-GO: missing Dockerfile.api"; exit 2; }
  [[ -f "$REPO_ROOT/Dockerfile.ui" ]] || { say "NO-GO: missing Dockerfile.ui"; exit 2; }
}

main(){
  ensure_exec_bits
  ensure_env
  preflight

  # Doctor (best-effort; doesn't block install)
  "$REPO_ROOT/bin/tc" doctor || true

  say ""
  say "Starting services (detached)..."
  "$REPO_ROOT/bin/tc" up

  say ""
  say "Open UI:"
  say "  UI  : open http://localhost:8501"
  say ""
  say "Useful commands:"
  say "  ./bin/tc logs"
  say "  ./bin/tc logs trs_api"
  say "  ./bin/tc down"

  # Try to open browser automatically (non-fatal)
  (open http://localhost:8501 >/dev/null 2>&1 || true)

  say ""
  say "GO."
}

main "$@"
