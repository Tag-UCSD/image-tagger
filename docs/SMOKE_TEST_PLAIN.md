# Smoke Test Runbook, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Smoke test | A short final check that proves the most important user paths work. |
| Deployed | Running on internet hosting services, not only on a laptop. |
| Render | The hosting service planned for the Python API. |
| Vercel | The hosting service planned for the browser site. |
| Supabase Auth | The sign-in service used to create and verify user tokens. |
| JWT | A signed text token that says who a user is and what role they have. |
| Environment variable | A setting passed to a program from the computer or hosting service, rather than written into code. |
| IRR | Inter-rater reliability: a measure of how consistently different labelers agree. |

## Ownership Notes

- Engineer A creates the smoke-test user tokens.
- Engineer A maintains three Supabase Auth test users with these roles: `admin`, `tagger`, and `supervisor`.
- Store the tokens only in local environment variables:
  - `SMOKE_ADMIN_JWT`
  - `SMOKE_TAGGER_JWT`
  - `SMOKE_SUPERVISOR_JWT`
- Do not commit JWTs, passwords, or refresh tokens to Git.
- Do not paste secret values into this file.
- The normal token setup is:
  1. Store the three test-account logins in the team password manager.
  2. Sign in shortly before the smoke test.
  3. Copy the fresh access tokens into local environment variables.

## Prerequisites

Before running the smoke test:

- `RENDER_URL` must point to the deployed Python API base URL.
- `FRONTEND_URL` must point to the deployed browser site base URL.
- Engineer A must have exported fresh values for `SMOKE_ADMIN_JWT`, `SMOKE_TAGGER_JWT`, and `SMOKE_SUPERVISOR_JWT`.
- The human owners must already have checked Render, Vercel, Supabase Auth, and image storage setup.

## Smoke Steps

1. Check that the Python API is alive and can reach its dependencies.

```bash
curl -sS "$RENDER_URL/health"
```

Expected result: the response has `status` set to `ok` or `degraded`, and also includes `version`, `db`, and `storage`.

2. Check that Explorer opens without a sign-in step.

Open:

```text
$FRONTEND_URL/
```

Expected result: Explorer loads without asking for a token and without browser console errors.

3. Upload one image as an admin user.

```bash
curl -sS -X POST "$RENDER_URL/v1/admin/upload" \
  -H "Authorization: Bearer $SMOKE_ADMIN_JWT" \
  -F "files[]=@/absolute/path/to/test-image.jpg"
```

Expected result: the response includes `job_id`, `items`, at least one `image_id`, and `status: "queued"`.

4. Wait until the uploaded image can be loaded and its analysis is finished.

Use the first `image_id` returned by step 3:

```bash
IMAGE_ID="<first image_id from upload response>"

for i in $(seq 1 12); do
  RESPONSE="$(curl -sS "$RENDER_URL/v1/explorer/images/$IMAGE_ID")"
  echo "$RESPONSE"
  echo "$RESPONSE" | jq -e '.science != null and .science.run_status == "completed"' >/dev/null && break
  sleep 5
done
```

Expected result:

- `GET /v1/explorer/images/$IMAGE_ID` returns the image within 5 seconds of upload acceptance.
- Within 60 seconds, the response includes `science` and `science.run_status` is `"completed"`.

5. Submit one label as a tagger user.

First get the current assignment:

```bash
ASSIGNMENT_RESPONSE="$(curl -sS "$RENDER_URL/v1/workbench/next" \
  -H "Authorization: Bearer $SMOKE_TAGGER_JWT")"

echo "$ASSIGNMENT_RESPONSE"

ASSIGNED_IMAGE_ID="$(echo "$ASSIGNMENT_RESPONSE" | jq -r '.image.id')"
ASSIGNED_ATTRIBUTE_KEY="$(echo "$ASSIGNMENT_RESPONSE" | jq -r '.assignment.attribute_key')"
```

Expected result: the response includes `image.id` and `assignment.attribute_key`.

Then submit a label:

```bash
curl -sS -X POST "$RENDER_URL/v1/workbench/validate" \
  -H "Authorization: Bearer $SMOKE_TAGGER_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "image_id": '"$ASSIGNED_IMAGE_ID"',
    "attribute_key": "'"$ASSIGNED_ATTRIBUTE_KEY"'",
    "value": 0.9,
    "duration_ms": 5000
  }'
```

Expected result: the response includes `validation_id` and `accepted: true`.

6. Check that Explorer shows analysis trust information.

Open the uploaded image detail page in Explorer.

Expected result: trust badges and science feature rows appear, and there are no browser console errors.

7. Check the monitor IRR API as a supervisor user.

```bash
curl -sS "$RENDER_URL/v1/monitor/irr" \
  -H "Authorization: Bearer $SMOKE_SUPERVISOR_JWT"
```

Expected result: the response has the shape `{ "rows": [...] }`. In Phase 1, either a filled `rows` list or an empty list is acceptable.

8. Check the deployed Monitor page.

Open:

```text
$FRONTEND_URL/monitor
```

Expected result: Monitor loads without browser console errors and shows either an IRR table or the agreed empty state for `{ rows: [] }`.

## Final Expected Outcome

All four deployed journeys work:

- Explorer is public.
- Admin upload works with `SMOKE_ADMIN_JWT`.
- Workbench label submission works with `SMOKE_TAGGER_JWT`.
- Monitor works with `SMOKE_SUPERVISOR_JWT` and handles either filled or empty IRR data.
- No secrets are present in Git-tracked files or pasted into this runbook.
