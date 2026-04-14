# Tagging_Contractor (Turnkey)

This is a **turnkey runnable wrapper** around the TRS **core dist bundle** (vendored under `core/trs-core/v0.2.8/`).
It boots:

- **FastAPI** service (read-only) serving registry/contracts/schemas
- **Streamlit** UI for browsing and inspection

## One-command run (recommended)

From the repo root:

```bash
./bin/tc up
```

Then open:
- UI: http://localhost:8501
- API: http://localhost:8401/health

## Doctor (GO/NO-GO)

```bash
./bin/tc doctor
```

## Notes

- This repo does **not** attempt to install Docker Desktop (macOS requires interactive approval).
- Once Docker Desktop is installed and running, the system is fully one-command.


## Quick Start

```bash
./install.sh
# or
./bin/tc up
```

## Walk-Away Install Notes
- `./install.sh` now runs `./bin/tc up`, which blocks until API/UI health checks pass.
- Manual readiness check: `./bin/tc health` or open `http://localhost:8401/health` and `http://localhost:8501`.
