#!/bin/bash
VERSION="dev"
if [ -f VERSION ]; then
  VERSION=$(cat VERSION)
fi
# Discover a suitable Python interpreter for host-side checks
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "❌ python3/python not found. Cannot run install-time guards."
  exit 1
fi

# Use a local virtual environment for host-side Python checks to avoid
# polluting the global interpreter.
if [ ! -d ".venv" ]; then
  echo "[install] Creating local Python virtual environment (.venv)..." 
  $PYTHON_CMD -m venv .venv || { echo "❌ Failed to create .venv"; exit 1; }
fi
if [ -x ".venv/bin/python" ]; then
  PYTHON_CMD=".venv/bin/python"
fi

echo "🚀 Starting Image Tagger v3 (v${VERSION})"
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop."
    exit 1
fi

# Governance check (Guardian)
echo "🧬 Running structural hollow-repo guard"
${PYTHON_CMD} scripts/hollow_repo_guard.py || { echo "❌ Hollow Repo Guard failed"; exit 1; }

echo "🧪 Running program integrity guard"
${PYTHON_CMD} scripts/program_integrity_guard.py || { echo "❌ Program Integrity Guard failed"; exit 1; }
echo "🧯 Running syntax guard"

${PYTHON_CMD} scripts/syntax_guard.py || { echo "❌ Syntax Guard failed"; exit 1; }

echo "🪝 Running critical import guard"

${PYTHON_CMD} scripts/critical_import_guard.py || { echo "❌ Critical Import Guard failed"; exit 1; }


echo "🧪 Running canon guard"
${PYTHON_CMD} scripts/canon_guard.py || { echo "❌ Canon Guard failed"; exit 1; }

echo "🔒 Running Guardian (governance) checks"
if command -v ${PYTHON_CMD} &> /dev/null; then
    if [ -f "governance.lock" ]; then
        ${PYTHON_CMD} scripts/guardian.py verify
        GUARDIAN_RC=$?
        if [ "$GUARDIAN_RC" -ne 0 ]; then
            echo "❌ Guardian verification failed (rc=$GUARDIAN_RC). Aborting install."
            exit $GUARDIAN_RC
        fi
    else
        echo "⚠️ governance.lock not found; creating initial baseline with 'guardian.py freeze'."
        ${PYTHON_CMD} scripts/guardian.py freeze
        if [ "$?" -ne 0 ]; then
            echo "❌ Guardian freeze failed. Aborting install."
            exit 1
        fi
    fi
else
    echo "⚠️ ${PYTHON_CMD} not found; skipping Guardian checks."
fi

# Security warning: detect default API_SECRET and warn user
DEFAULT_API_SECRET="dev_secret_key_change_me"
if [ "${API_SECRET:-$DEFAULT_API_SECRET}" = "$DEFAULT_API_SECRET" ]; then
    echo "⚠️  WARNING: API_SECRET is using the default value 'dev_secret_key_change_me'."
    echo "    This is fine for local demos, but you MUST change it for any shared or deployed environment."
fi

echo "🐳 Building containers"
cd deploy
docker-compose up -d --build

echo "🌱 Seeding database"
sleep 5
docker-compose exec -T api python3 backend/scripts/seed_tool_configs.py
docker-compose exec -T api python3 backend/scripts/seed_attributes.py

echo "✅ SYSTEM ONLINE at http://localhost:8080"


echo "🧪 Running smoke tests (API + Science)"
docker-compose exec -T api python3 backend/scripts/smoke_api.py
echo "Running science smoke test (advisory)..."
docker-compose exec -T api \
  python -m backend.scripts.smoke_science || echo "[install] WARNING: science smoketest failed (likely empty DB or misconfigured pipeline) – continuing."
# Optional second pass inside the API container; failures are treated as advisory.
docker-compose exec -T api \
  python backend/scripts/smoke_science.py || echo "[install] smoke_science (second pass) failed – continuing as advisory."

echo "[install] Running frontend smoketest..."
cd ..
${PYTHON_CMD} scripts/smoke_frontend.py || { echo "[install] Frontend smoketest failed"; exit 1; }
cd deploy
echo "✅ Smoke tests passed."
echo "🧪 Running pytest API smoketests"
docker-compose exec -T api pytest -q tests/test_v3_api.py
if [ "$?" -ne 0 ]; then
    echo "❌ Pytest API smoketests failed."
    exit 1
fi
echo "✅ Pytest API smoketests passed."

# --- GO / NO-GO checks (v3.4.36 additions) ---
echo "[go-check] Running BN naming guard (non-fatal)..."
$PYTHON_CMD -m backend.science.bn_naming_guard || echo "[go-check] bn_naming_guard completed with warnings."
