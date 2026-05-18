# TRACK A: IMAGE SETS AND PROVENANCE

**Owner:** Backend/data agent. **Scope:** local image-set storage, collection import, provenance, image-set listing, image-set filtering in Explorer APIs, image detail provenance, and backend tests. **Out of scope:** latent detector algorithms, frontend components, Workbench validation UX, Monitor charts, and upstream Knowledge Atlas deliverables.

Track A can run in parallel with Track B and Track C. Track B may persist latent observations without image-set attachment until this track lands. Track C should build against mocks first.

## Track A End State

Track A is complete when:

- the local database stores named image sets
- each image-set item preserves room type and provenance
- Admin has a protected backend endpoint for manifest import
- duplicate imports reuse existing images and do not duplicate set membership
- Explorer can list image sets
- Explorer search can filter by image set
- image detail responses include image-set membership and provenance
- tests cover import, duplicate handling, search filtering, and detail provenance

Track A does **not** include:

- latent score computation
- frontend UI implementation
- science pipeline changes
- importing or committing a full 500-image dataset

## Task List

#### Task A2-1: Add Image Set Models
- **Goal:** Create first-class persistence for named image collections.
- **Files to create or modify:** `backend/models/assets.py` or `backend/models/image_sets.py`, `backend/models/__init__.py`, a migration helper under `backend/scripts/`, backend tests.
- **Implementation notes:** Add `ImageSet` with `slug`, `name`, `description`, `source`, `provenance`, timestamps. Add `ImageSetItem` with `image_set_id`, `image_id`, `position`, `room_type`, `source_url`, `photographer`, `license`, `license_url`, timestamps. Use a unique `slug`. Use a unique pair for `(image_set_id, image_id)`.
- **Acceptance criteria:** Tests create a set, attach images, commit, reload, and read provenance. Duplicate membership is rejected or service-handled idempotently.
- **Depends on:** existing database model setup.

#### Task A2-2: Define Image Set Schemas
- **Goal:** Add typed request and response shapes for import and browse.
- **Files to create or modify:** `backend/schemas/admin.py`, `backend/schemas/discovery.py`, or `backend/schemas/image_sets.py`.
- **Implementation notes:** The import request accepts `name`, `slug`, optional `description`, optional `source`, optional `provenance`, and an `images` list. Each image accepts `filename`, one of `url`, `path`, or `storage_path`, optional `room_type`, provenance fields, optional `tags`, and optional `meta_data`. The import response returns `image_set_id`, `slug`, `created_images`, `reused_images`, `created_items`, `skipped_items`, `errors`, and `total_in_file`.
- **Acceptance criteria:** Pydantic rejects empty image lists, missing image path/URL, empty filenames, and overlong slugs with the existing validation error envelope.
- **Depends on:** A2-1 can proceed in parallel.

#### Task A2-3: Build The Import Service
- **Goal:** Import a collection manifest into image and image-set rows.
- **Files to create or modify:** `backend/services/image_sets.py`, `backend/tests/test_image_set_import.py`.
- **Implementation notes:** Create or reuse `ImageSet` by slug. Create or reuse `Image` by filename plus storage path unless the repo has a better identity rule. Store path/URL in `Image.storage_path`. Preserve imported tags in `Image.meta_data["tags"]`. Store room type and provenance on `ImageSetItem`. Continue importing valid rows when one row fails.
- **Acceptance criteria:** A three-image fixture imports. Re-importing it reports reused/skipped records and creates no duplicates. A bad row is reported while good rows still import.
- **Depends on:** A2-1, A2-2.

#### Task A2-4: Add Admin Import Endpoint
- **Goal:** Let admins import image sets through the backend API.
- **Files to create or modify:** `backend/api/v1_admin.py`, `backend/tests/integration/test_admin.py`.
- **Implementation notes:** Add `POST /v1/admin/image-sets/import`. Use the existing admin auth dependency. Delegate to the import service. Do not trust client-supplied identity headers.
- **Acceptance criteria:** Admin JWT succeeds. Tagger/supervisor JWT gets `403`. Missing/invalid token gets `401`. Invalid manifest returns the shared validation error shape.
- **Depends on:** A2-3.

#### Task A2-5: Add Explorer Image Set Listing
- **Goal:** Expose available image sets to the public Explorer app.
- **Files to create or modify:** `backend/api/v1_discovery.py`, discovery schemas, Explorer integration tests.
- **Implementation notes:** Add `GET /v1/explorer/image-sets`. Return summaries sorted by name or newest. Explorer remains anonymous.
- **Acceptance criteria:** The endpoint returns all imported image sets without requiring auth. Empty database returns an empty list with the documented shape.
- **Depends on:** A2-1.

#### Task A2-6: Add Image Set Search Filtering
- **Goal:** Filter Explorer search results by image-set slug or ID.
- **Files to create or modify:** `backend/api/v1_discovery.py`, search schemas/tests.
- **Implementation notes:** Extend `GET /v1/explorer/search` with `image_set`. Prefer slug as the public query value. Preserve existing search defaults and pagination.
- **Acceptance criteria:** Search without `image_set` behaves as before. Search with `image_set=<slug>` returns only set members. Unknown slug behavior is documented and tested.
- **Depends on:** A2-5.

#### Task A2-7: Extend Image Detail With Provenance
- **Goal:** Let the Explorer modal display source, license, and set membership.
- **Files to create or modify:** `backend/api/v1_discovery.py`, discovery schemas/tests.
- **Implementation notes:** Add `image_sets` to detail response. Each membership includes set ID, slug, name, room type, source URL, photographer, license, and license URL. Return all memberships if an image belongs to multiple sets.
- **Acceptance criteria:** Detail for an image in two sets returns two membership records. Imported provenance round-trips into the detail payload. Existing detail behavior remains intact.
- **Depends on:** A2-6.

#### Task A2-8: Update Contract Docs
- **Goal:** Make Track A response shapes execution authority.
- **Files to create or modify:** `docs/CONTRACT.md`.
- **Implementation notes:** Add image-set import, image-set listing, `image_set` search param, and detail provenance fields. Keep unrelated contract text unchanged.
- **Acceptance criteria:** Contract mentions the new routes and states which are public versus protected.
- **Depends on:** A2-4 through A2-7.

## Track A Smoke Check

Import a three-image fixture as admin. List image sets through Explorer. Search by the new set slug. Open detail for one image and confirm room type, source URL, photographer, license, and set name are present.

