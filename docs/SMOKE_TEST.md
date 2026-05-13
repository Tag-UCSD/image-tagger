# Smoke test — deployed backend (Phase 1)

Hands-on checklist for validating a **production** backend instance reachable over HTTPS after configuration in `render.yaml`. This runbook deliberately references **environment variable names only** for bearer tokens; paste real secrets into your shell from a password manager, never commit them into the repo.

## Roles and JWT provisioning (**Engineer A**)

Short-lived JWTs carry the canonical `role` claim (`admin`, `tagger`, or `supervisor`) used by the API. Before the smoke session:

1. In Supabase Auth, ensure three test identities exist with those role claims in the JWT templates your project uses for custom claims.
2. Immediately before smoke, mint fresh Supabase Auth access tokens and export them locally (replace angle-bracket placeholders in your terminal only):

   ```bash
   export SMOKE_ADMIN_JWT="<paste-admin-access-token>"
   export SMOKE_TAGGER_JWT="<paste-tagger-access-token>"
   export SMOKE_SUPERVISOR_JWT="<paste-supervisor-access-token>"
   ```

The commands below assume `BACKEND_URL` points at your Render service (`https://<service>.onrender.com`).

```bash
export BACKEND_URL="https://REPLACE_ME.onrender.com"
```

## Prerequisites

| Item | Notes |
|------|--------|
| Postgres | Render Postgres is wired via `DATABASE_URL` in the blueprint. The first deploy runs a lightweight ORM bootstrap so mapped tables exist. |
| Object storage architecture | Canonical media for **Supabase Storage** is described in Phase 1 planning; uploads on Render still persist under `IMAGE_STORAGE_ROOT` inside the container. Treat that filesystem as **ephemeral**: redeploy may discard local files unless you mirror off-box. Operational sync to bucket storage belongs to platform runbooks outside this repo. |
| Smoke tokens | Populate `SMOKE_ADMIN_JWT`, `SMOKE_TAGGER_JWT`, `SMOKE_SUPERVISOR_JWT` immediately before executing the steps (see Engineer A section). |

Tools used below: `curl` and `jq` (recommended).

---

## A. Health boundary

Confirm the service binds real dependencies (`db` touches Postgres; `storage` reflects `IMAGE_STORAGE_ROOT` writeability):

```bash
curl -sfS "${BACKEND_URL}/health" | jq -e '.status == "ok" and .db == true and .storage == true and (.version | type == "string")'
```

---

## B. Public Explorer (anonymous)

Anonymous read access must work without `Authorization`:

```bash
curl -sfS "${BACKEND_URL}/v1/explorer/search?page=1&page_size=5" | jq -e 'type == "array"'
```

---

## C. Protected admin upload (asynchronous acceptance)

Administrative uploads are accepted with **`SMOKE_ADMIN_JWT`** and respond **202 Accepted**. The envelope includes:

| Field | Expectation |
|-------|--------------|
| `job_id` | Present when background job bookkeeping succeeds (integer or `null` only if job creation failed unusually). |
| `items` | One object per persisted image (at minimum `image_id` and logical filename metadata). |
| `image_ids` | Non-empty list of new database ids after a successful multipart post. |
| `status` | Always `queued` for the happy path—the science pipeline executes after the HTTP response returns. |

Example (supply a tiny PNG/JPEG/WebP):

```bash
RESP=$(curl -sS -o /tmp/smoke-upload.json -w "%{http_code}" \
  -X POST "${BACKEND_URL}/v1/admin/upload" \
  -H "Authorization: Bearer ${SMOKE_ADMIN_JWT}" \
  -F "files=@./path/to/smoke.png")

test "$RESP" = "202"
jq -e '.job_id != null and (.image_ids | length) >= 1 and (.items | length) >= 1 and .status == "queued"' \
  /tmp/smoke-upload.json
IMAGE_ID="$(jq -r '.image_ids[0]' /tmp/smoke-upload.json)"
```

Timing checks:

1. **Within five seconds**, the new row must be reachable from Explorer detail:

   ```bash
   for i in $(seq 1 10); do
     code=$(curl -sS -o /dev/null -w "%{http_code}" "${BACKEND_URL}/v1/explorer/images/${IMAGE_ID}/detail")
     test "$code" = "200" && break
     sleep 0.5
   done
   test "$code" = "200"
   ```

2. **Within sixty seconds**, the canonical science run for that image should finish (status is uppercase in the wire format):

   ```bash
   for i in $(seq 1 30); do
     st=$(curl -sfS "${BACKEND_URL}/v1/explorer/images/${IMAGE_ID}/detail" | jq -r '.science_run.status // empty')
     test "$st" = "COMPLETED" && break
     sleep 2
   done
   test "$st" = "COMPLETED"
   ```

If `science_run` stays `PENDING` or `RUNNING`, inspect Render logs and the upload job tables in Postgres before retrying.

---

## D. Workbench validation path (tagger)

Submit one validation using **`SMOKE_TAGGER_JWT`**. You need a valid `image_id` and an `attribute_key` that exists in your attribute registry (`GET /v1/explorer/attributes` lists candidates). Minimal shape:

```bash
ATTR_KEY="$(curl -sfS "${BACKEND_URL}/v1/explorer/attributes" | jq -r '.[0].key')"

curl -sfS -X POST "${BACKEND_URL}/v1/workbench/validate" \
  -H "Authorization: Bearer ${SMOKE_TAGGER_JWT}" \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg ak "$ATTR_KEY" --argjson id "$IMAGE_ID" \
      '{ image_id: $id, attribute_key: $ak, value: 0.5, duration_ms: 1000 }')" \
  | jq -e '.status == "success"'
```

---

## E. Monitor (supervision surface)

`/v1/monitor/*` is **admin-role** guarded. Prefer **`SMOKE_ADMIN_JWT`** (alternatively another identity whose JWT carries `admin`; **`SMOKE_SUPERVISOR_JWT`** is listed for parity where your policy maps supervisor privileges to monitoring routes).

**Velocity**:

```bash
curl -sfS "${BACKEND_URL}/v1/monitor/velocity?window_hours=24" \
  -H "Authorization: Bearer ${SMOKE_ADMIN_JWT}" | jq -e 'type == "array"'
```

**IRR (inter-rater / overlap statistics)**  

The API returns a JSON **array** today (possibly empty `[ ]`). The long-term contractual wrapper described in `/docs/CONTRACT.md` may introduce a **`rows`** object for clients; Phase 2 may add IRR seed automation scripts in-repo.

**Important:** meaningful IRR pairs require overlapping human validations seeded in Postgres. Until that dataset exists on your instance, **`[]`** is acceptable for Phase 1. If you believe overlap data exists yet still see `[ ]`, sample again after more validations land.

```bash
curl -sfS "${BACKEND_URL}/v1/monitor/irr?window_hours=72" \
  -H "Authorization: Bearer ${SMOKE_ADMIN_JWT}" | jq -e 'type == "array"'
```

---

## Troubleshooting cheatsheet

- **Production fails fast at boot** (`RuntimeError`): confirm `DATABASE_URL`, `SUPABASE_JWT_SECRET`, `CORS_ALLOWED_ORIGINS`, and `VLM_HARD_LIMIT_USD` via the Render Dashboard (matching `backend.settings.Settings.assert_production_ready`).
- **`401` on protected routes:** token expiry or wrong HS256 signing secret versus `SUPABASE_JWT_SECRET` on Render.
- **Explorer detail `404` shortly after upload:** wait for the persistence loop windows above; failing that, verify the upload multipart field name is `files` and that the image survived the Postgres commit.
