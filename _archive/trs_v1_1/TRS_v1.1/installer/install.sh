\
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Tagging_Contractor Installer =="
echo "Repo: $(pwd)"
echo

# A "world-class" installer is a deterministic bootstrapper + doctor gate.
# It can fix safe mechanical issues, but will not silently rewrite semantics.

chmod +x ./bin/tc || true
./bin/tc up
