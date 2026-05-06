# Frontend Phase 1, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Frontend | The browser apps that users see and click. |
| Backend | The Python app that stores data, checks permissions, runs image analysis, and answers browser requests. |
| API client | Shared browser code that calls the Python API. |
| Mock | Fake data used before the live API is ready. |
| Fixture | A saved example response used as fake data in tests or demos. |
| JWT | A signed text token that says who a user is and what role they have. |
| Environment variable | A setting passed to the browser build or hosting service. |
| Vite | The JavaScript build tool used by the frontend. |
| React | The JavaScript package used to build browser screens. |
| Accessibility | Making the app usable by people with different devices and assistive tools. |
| Vercel | The hosting service planned for the browser site. |
| Tailwind | A CSS utility framework that may already be configured in the project. |
| Playwright | The JavaScript package used here to check browser layouts. |

**Owner:** Engineer B.

**Scope:** files under `frontend/` required for a credible v1 release against the current contract.

**Out of scope:** backend changes, a real sign-in screen, and optional annotation or polish work that does not block the final smoke test.

`docs/workplan/COORDINATION.md` is required for this track. Tasks C-1, C-1.5, and C-2 are required support work for Phase 1.

## Phase 1 End State

Frontend Phase 1 is complete when:

- all four user journeys use the shared API client
- Explorer works without sign-in
- Workbench, Monitor, and Admin work with pre-issued demo JWTs
- the browser handles loading, empty, error, and unauthorized states
- the browser screens are usable on small and large screens
- the app is deployed and can switch from mock data to the live Python API

Phase 1 does not include:

- a real sign-in screen
- advanced region drawing
- extra polish that does not change the contracted user journeys

## Task B-1: Mock API Client and Contract Fixtures

Goal: create one shared API client that can use fake data or live data.

Files: `frontend/shared/src/api-client.js`, `frontend/shared/src/mocks/`, `frontend/shared/src/types.ts`.

Instructions:

- Use native browser `fetch` inside typed helper functions such as `explorer.search()` and `workbench.getNext()`.
- When `VITE_USE_MOCKS` is `"true"`, return fake data after a short randomized delay.
- Make fake data match `docs/CONTRACT.md`.
- Keep mock code in `frontend/shared/src/api-client.js` and `frontend/shared/src/mocks/`.
- Do not use the JavaScript package `msw` in Phase 1.
- Put shared TypeScript declarations in `frontend/shared/src/types.ts`.
- Add one helper that reads role-specific demo JWTs from Vite environment variables:
  - `VITE_DEMO_ADMIN_JWT`
  - `VITE_DEMO_TAGGER_JWT`
  - `VITE_DEMO_SUPERVISOR_JWT`

Done when all four apps can render without the backend running, live mode calls `VITE_API_BASE_URL`, protected live calls attach the correct bearer token, and `npm install && npm run dev` works from `frontend/`.

## Task B-2: Shared Design System and Layout Pieces

Goal: make shared display components for all four apps.

Files: shared components under `frontend/shared/src/components/`, `frontend/shared/src/theme.css`, `frontend/shared/preview.html`.

Instructions:

- Build shared header, toasts, buttons, inputs, loading placeholders, empty states, error banners, trust badges, modals, and pagination controls.
- Use the existing Tailwind CSS setup if present.
- `TrustBadge` receives `evaluation_status` from the trust envelope.
- Make keyboard focus clearly visible.
- Use colors with WCAG AA contrast.

Done when `frontend/shared/preview.html` shows every shared component in default, loading, error, and disabled states, and the accessibility command reports zero critical or serious issues.

## Task B-3: Explorer Journey

Goal: search, filter, paginate, and open image detail with science and trust badges.

Files: Explorer app files such as `App.jsx`, `SearchBar.jsx`, `ImageGrid.jsx`, and `ImageDetailModal.jsx`.

Instructions:

- Store search state in the URL query parameters.
- Explorer API calls are public and must not send an `Authorization` header.
- Use `GET /v1/explorer/search`.
- In the detail view, show Overview, Science Features, and Affordances.
- Read feature values and `evaluation_status` directly from `science.features[feature_key]`.
- Do not use a separate feature confidence lookup.
- Make loading, empty, error, and success states reachable from mock data.

Done when mock flags can show all states, Explorer sends no auth header, and reloading a URL preserves `q`, `page`, and `room_type`.

## Task B-4: Workbench Journey

Goal: fetch the next assigned image, show the correct label form, validate the label, submit it, and move forward.

Files: Workbench app files such as `App.jsx`, `AttributeForm.jsx`, and `KeyboardShortcuts.jsx`.

Instructions:

- Keep Phase 1 focused on the main labeling flow.
- `GET /v1/workbench/next` returns either one assignment or `{ empty: true }`.
- If the response is `{ empty: true }`, show a clear empty-queue state and a retry action.
- If an assignment exists, build the form from `assignment.value_type`, `allowed_values`, `min`, `max`, `step`, and `required`.
- Do not hardcode rules for specific attributes in the browser.
- Use `performance.now()` to measure `duration_ms`.
- Use the JavaScript package `zod` to validate the value before sending it.
- Add keyboard shortcuts for submitting and moving to the next assignment.
- Leave advanced region creation for Phase 2.
- In live mode, use `VITE_DEMO_TAGGER_JWT`.
- If the tagger token is missing in live mode, show a visible demo-access configuration message.

Done when ten mock assignments can be completed by keyboard, each value type renders the right control, empty queue works, invalid values do not call the network, and live mode handles both assignment and empty responses.

## Task B-5: Monitor Journey

Goal: show supervisor views for labeling speed and inter-rater reliability.

Files: Monitor app files such as `App.jsx`, `VelocityChart.jsx`, and `IRRTable.jsx`.

Instructions:

- Use the JavaScript package `recharts` for the velocity line chart.
- `GET /v1/monitor/irr` returns a list of rows for a table.
- IRR table columns are attribute, IRR, `n_pairs`, and `bin`.
- Show an empty state for `{ rows: [] }`.
- Show a dedicated unauthorized screen for `403`.
- In live mode, use `VITE_DEMO_SUPERVISOR_JWT`.
- If the supervisor token is missing in live mode, show a visible demo-access configuration message.

Done when table sorting works, velocity tooltips show timestamp and count, unauthorized state works, empty IRR data works, and missing live token shows a visible message.

## Task B-6: Admin Journey

Goal: upload images, show budget, and toggle the kill switch.

Files: Admin app files such as `App.jsx`, `UploadPanel.jsx`, `BudgetPanel.jsx`, and `KillSwitch.jsx`.

Instructions:

- Support drag-and-drop upload.
- Before any network call, reject:
  - files that are not JPEG, PNG, or WebP
  - files larger than 10 MiB
  - batches larger than 200 files
- Match the upload rules in the contract exactly.
- Treat a successful upload response as queued work.
- Require confirmation before toggling the kill switch.
- Build the budget display from `spent_usd`, `limit_usd`, and `remaining_usd`.
- Do not add a separate browser-only budget limit setting.
- In live mode, use `VITE_DEMO_ADMIN_JWT`.
- If the admin token is missing in live mode, show a visible demo-access configuration message.

Done when invalid uploads are blocked before network calls, successful uploads return queued status, budget display uses returned values, kill-switch errors roll back cleanly, unauthorized admin state works, and missing live token shows a visible message.

## Task B-7: Responsive Layout and Accessibility Audit

Goal: make all four apps usable from 360px mobile screens through 1920px desktop screens.

Files: CSS and JSX across apps, `frontend/shared/src/hooks/useBreakpoint.js`, `frontend/tests/responsive.spec.ts`, and JavaScript package `playwright` config if needed.

Instructions:

- Use one local preview server at `http://127.0.0.1:4173`.
- Test `/`, `/workbench/`, `/monitor/`, and `/admin/`.
- Every image must have alt text.
- Every form input must have a label.
- Keyboard focus order must make sense.
- Use the JavaScript package `@axe-core/cli` for accessibility checks.
- Use the JavaScript package `playwright` for responsive layout checks.

Done when build and preview work, accessibility checks have zero critical or serious issues on all routes, and the JavaScript package `playwright` shows no horizontal scrollbars at 360px.

## Task B-8a: Frontend Deployment Repo Configuration

Goal: make the browser site deployable to Vercel from committed files.

Files: `frontend/vercel.json`, `.github/workflows/deploy_frontend.yml`, and app `vite.config.js` files if needed.

Instructions:

- Use one Vercel project for the whole `frontend/` workspace.
- Serve Explorer at `/`, Workbench at `/workbench`, Monitor at `/monitor`, and Admin at `/admin`.
- Use Vercel rewrites in `frontend/vercel.json`.
- Do not create four separate Vercel projects.
- Keep browser environment variables limited to `VITE_*` names.
- Support `VITE_DEMO_ADMIN_JWT`, `VITE_DEMO_TAGGER_JWT`, and `VITE_DEMO_SUPERVISOR_JWT` for protected demos.
- Do not treat Vercel project creation or dashboard secret entry as repo work.

Done when deployment files exist, subpath rewrites are explicit, frontend build passes, preview serves all four routes, and live-mode preview can open protected routes with demo JWTs.

## Task B-8b: Frontend Platform Provisioning and Live Verification

Goal: have a human verify the real hosted browser site.

Human prerequisites:

- Vercel project linked to the repo
- required `VITE_*` variables in Vercel
- GitHub-to-Vercel preview integration
- deployed backend URL from A-12b

Instructions:

- Do not hand this task to an agent as if repo files alone can prove it.
- Use the repo configuration from B-8a and the live Vercel project.
- If live verification finds a repo defect, fix it in a follow-up commit.

Done when a frontend pull request produces a Vercel preview, merging to `main` updates production, mock mode works without contacting the backend, live mode reaches the deployed backend, and protected routes work through demo tokens without a sign-in screen.

## Task B-9: Mock-to-Live Swap

Goal: switch from fake data to the real deployed backend and run the final smoke test.

Files: `frontend/shared/src/api-client.js`, `frontend/.env.production`, `README.md`.

Instructions:

- Do this in a joint session with Engineer A.
- Set `VITE_USE_MOCKS=false`.
- Set `VITE_API_BASE_URL` to the deployed backend URL.
- Keep Explorer public.
- Use configured demo JWTs for Workbench, Monitor, and Admin.
- Use `docs/SMOKE_TEST.md` as the checklist.

Done when both engineers verify admin upload, Explorer image detail, science completion within 60 seconds, trust badges, Workbench label submission, and Monitor display with no browser console errors.
