# TRACK C: GUI UPDATES AND SHARED CLIENT

**Owner:** Frontend agent. **Scope:** shared API-client methods, frontend mocks, Explorer filters/detail updates, Admin image-set import controls, Workbench latent validation mode, Monitor latent status views, and frontend tests. **Out of scope:** backend models, detector algorithms, migrations, and live dataset import.

Track C can start immediately with mocks. Do not wait for Track A or Track B. When backend endpoints land, normalize response differences in the shared API client rather than scattering field-shape fixes through components.

## Track C End State

Track C is complete when:

- shared frontend API methods exist for image sets, latent filters, imports, latent runs, and latent status
- mocks cover success, empty, loading, error, and unauthorized states
- Explorer filters by image set, latent tag, effect domain, and score threshold
- Explorer detail shows provenance, latent scores, evidence, confidence, and linked effects
- Admin validates and submits an image-set manifest, then triggers a latent run
- Workbench renders a latent validation assignment and submits a corrected ordinal value
- Monitor shows image-set latent status and distribution warnings
- frontend tests cover the new user-visible states

Track C does **not** include:

- backend endpoint implementation
- latent score computation
- standalone HTML viewer work
- changes to upload policy

## Task List

#### Task C2-1: Extend Shared API Client And Types
- **Goal:** Add the frontend contract surface for Workplan 2.
- **Files to create or modify:** `frontend/shared/src/api-client.js`, `frontend/shared/src/types.ts`, `frontend/shared/src/mocks/`.
- **Implementation notes:** Add `explorer.listImageSets()`, extended `explorer.search()`, extended `explorer.getImage()`, `admin.importImageSet()`, `admin.runLatentDetectors(imageSetId)`, `monitor.getLatentStatus(imageSetId)`, and either `workbench.getNextLatent()` or an option on existing Workbench calls. Explorer stays anonymous. Admin, Workbench, and Monitor keep demo-token behavior in live mode.
- **Acceptance criteria:** With mocks enabled, every new method returns stable fixture data. With mocks disabled, protected methods attach bearer tokens and Explorer methods do not.
- **Depends on:** current shared client.

#### Task C2-2: Build Workplan 2 Mock Payloads
- **Goal:** Allow all UI work to proceed before backend tracks merge.
- **Files to create or modify:** `frontend/shared/src/mocks/explorer.js`, `admin.js`, `workbench.js`, `monitor.js`.
- **Implementation notes:** Mock two image sets, six latent observations, linked effect domains, one full-provenance image, one image with no latents, and one low-confidence proxy image. Mock Monitor normal and suspicious distributions. Mock Admin import success, validation error, and latent-run summary.
- **Acceptance criteria:** All four apps can render their Workplan 2 states without a backend.
- **Depends on:** C2-1.

#### Task C2-3: Update Explorer Filters
- **Goal:** Add image-set, latent-tag, effect-domain, and threshold filters.
- **Files to create or modify:** `frontend/apps/explorer/src/App.jsx`, `SearchBar.jsx`, optional new Explorer filter components.
- **Implementation notes:** Populate image-set selector from `explorer.listImageSets()`. Show controls for the six latent tags and seven effect domains. Add threshold default `2.5`. Preserve current search and pagination. Keep filter state in URL params where practical.
- **Acceptance criteria:** Changing each filter triggers search with expected params. Reloading a filtered URL restores state. Loading, empty, and error states still work.
- **Depends on:** C2-1, C2-2.

#### Task C2-4: Add Latent Summary To Image Cards
- **Goal:** Show why an image matched latent/effect filters.
- **Files to create or modify:** `frontend/apps/explorer/src/ImageGrid.jsx` and related components.
- **Implementation notes:** Cards should show top latent observation, compact `0..4` bar, confidence cue, and effect mechanism when filtering by effect domain. Keep cards scannable and avoid nested card styling.
- **Acceptance criteria:** Cards with latents show readable scores. Cards without latents do not break layout. Effect-filtered cards can show a short mechanism line.
- **Depends on:** C2-3.

#### Task C2-5: Add Latent Detail UI
- **Goal:** Show all latent observations and evidence in the image detail modal.
- **Files to create or modify:** `frontend/apps/explorer/src/ImageDetailModal.jsx`.
- **Implementation notes:** Add a Latents tab or section. For every observation, render label, value out of 4, score bar, confidence, detector version, and evidence rows. Evidence rendering must be generic over arbitrary key/value pairs. Add provenance and linked effects with domain and mechanism. Preserve existing Overview, Science Features, and Affordances behavior.
- **Acceptance criteria:** Mocked detail with six observations renders all six. Arbitrary evidence keys render. Provenance shows set name, source URL, photographer, and license. Modal remains usable at mobile width and closes with Escape.
- **Depends on:** C2-2.

#### Task C2-6: Add Admin Image Set Import Panel
- **Goal:** Let admins submit collection manifests.
- **Files to create or modify:** `frontend/apps/admin/src/App.jsx`, new `ImageSetImportPanel.jsx`, mocks.
- **Implementation notes:** Add paste-based JSON import, and file selection if simple. Validate JSON parse and non-empty `images` before network. Render import summary counts and row errors. Do not change existing upload behavior.
- **Acceptance criteria:** Invalid JSON and empty image lists fail client-side. Successful mock import shows image-set ID/slug and counts.
- **Depends on:** C2-1, C2-2.

#### Task C2-7: Add Admin Latent Run Controls
- **Goal:** Let admins trigger latent detector runs for a set.
- **Files to create or modify:** Admin app components and mocks.
- **Implementation notes:** After import or image-set selection, show a Run latent detectors action. Call `admin.runLatentDetectors(imageSetId)`. Render queued, already completed, running, and failed counts.
- **Acceptance criteria:** Run action shows loading, then summary. Errors show inline and leave the panel usable.
- **Depends on:** C2-6.

#### Task C2-8: Add Workbench Latent Validation Mode
- **Goal:** Let taggers review and correct latent detector outputs.
- **Files to create or modify:** `frontend/apps/workbench/src/App.jsx`, existing or new form component.
- **Implementation notes:** Render image, latent tag label, detector value, confidence, evidence, and a `0..4` correction control. Preserve existing assigned-attribute validation. Keep keyboard submission if practical.
- **Acceptance criteria:** Mocked latent assignment renders evidence and value control. Submit sends image ID, tag ID, corrected value, and duration. Out-of-range values do not hit network.
- **Depends on:** C2-1, C2-2.

#### Task C2-9: Add Monitor Latent Status View
- **Goal:** Show detector completion and score distribution warnings.
- **Files to create or modify:** `frontend/apps/monitor/src/App.jsx`, optional `LatentStatusPanel.jsx`.
- **Implementation notes:** Add image-set selector and latent status panel. Show total images, images with all six observations, failures, mean score by detector, percent above `2.5`, and mean confidence. Warn when values are all identical, more than 80 percent above `2.5`, more than 80 percent below `0.5`, or mean confidence is below `0.2`. Preserve velocity and IRR views.
- **Acceptance criteria:** Normal mock status has no warnings. Suspicious mock status renders warning rows. Empty, unauthorized, and no-token states still work.
- **Depends on:** C2-1, C2-2.

#### Task C2-10: Add Frontend Tests
- **Goal:** Cover the new GUI states.
- **Files to create or modify:** existing frontend test files or new tests under the repo's frontend test layout.
- **Implementation notes:** Use the repo's current frontend tooling. Keep tests mock-driven. Cover Explorer filters, detail modal latents, Admin import, Workbench latent correction, and Monitor warnings. Include a mobile-width check for Explorer filter/detail layout.
- **Acceptance criteria:** Frontend build passes. New tests pass with mocks enabled. Existing frontend smoke tests still pass.
- **Depends on:** C2-3 through C2-9.

#### Task C2-11: Swap To Live Local Contracts
- **Goal:** Verify the UI against Track A and Track B endpoints.
- **Files to create or modify:** `frontend/shared/src/api-client.js`, possibly mocks or contract docs if drift is found.
- **Implementation notes:** Run with mocks disabled against local backend. Normalize response differences in the shared API client. If backend shape conflicts with `docs/CONTRACT.md`, fix backend or docs instead of embedding accidental assumptions in components.
- **Acceptance criteria:** Explorer lists image sets, searches by latent filters, and opens detail. Admin imports a fixture. Workbench renders a latent assignment if available. Monitor renders latent status. No console errors in happy paths.
- **Depends on:** Track A and Track B live endpoints.

## Track C Smoke Check

With mocks enabled, open all four apps. In Explorer, choose an image set, latent tag, social effect domain, and threshold. Open detail and confirm provenance, six latent rows, evidence, confidence, and linked effects. In Admin, paste a fixture manifest and run latent detectors. In Workbench, submit one mocked latent correction. In Monitor, view normal and suspicious latent status fixtures.

