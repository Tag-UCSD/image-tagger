# Frontend Phase 2, Plain-Language Version

| Term | Plain meaning |
|---|---|
| Frontend | The browser apps that users see and click. |
| Phase 2 | Optional follow-up after v1 already works. |
| UX | User experience: how easy and clear the app feels to use. |
| Annotation | Marking a part of an image with a label. |
| Canvas | A browser drawing area used for custom image interaction. |
| Contract | The written agreement for API addresses, data shapes, permissions, and shared fields. |
| Lighthouse | A browser auditing tool for performance and quality. |
| Backend dependency | A need for new Python API behavior before the browser feature can work. |

**Owner:** Engineer B.

**Scope:** optional browser improvements after the v1 experience already works.

**Out of scope:** anything required for the contracted v1 user journeys.

## Phase 2 End State

Frontend Phase 2 is complete when:

- Workbench supports richer image annotation without changing the core contract
- Explorer detail and presentation are stronger
- optional interface improvements make the app easier to use without adding new backend requirements

Phase 2 must not block the v1 tag.

## Task F-1: Advanced Workbench Annotation

Goal: add region annotation and efficiency features on top of the core Workbench flow.

Files: `frontend/apps/workbench/src/RegionCanvas.jsx`, `frontend/apps/workbench/src/App.jsx`, `frontend/apps/workbench/src/KeyboardShortcuts.jsx`.

Instructions:

- Build `RegionCanvas` with the browser `<canvas>` element and mouse events.
- Submit regions to `POST /v1/workbench/region`.
- Add local undo for the most recent action in the current session.
- Use only the region schema already defined in the contract.
- Do not invent new backend capabilities.

Done when a tagger can create, undo, recreate, and submit one region with mock data, and one live region submission works with a valid tagger JWT.

## Task F-2: Explorer Performance and Presentation Polish

Goal: make Explorer faster and easier to read beyond the Phase 1 baseline.

Files: `frontend/apps/explorer/src/ImageGrid.jsx`, `frontend/apps/explorer/src/ImageDetailModal.jsx`, `frontend/shared/src/theme.css`.

Instructions:

- Improve rendering smoothness.
- Improve loading placeholder behavior.
- Make confidence and trust information clearer.
- Do not change the API contract.

Done when Lighthouse performance is at least 85 on localhost for Explorer and image detail still follows the contract.

## Task F-3: Frontend Workflow Polish Pass

Goal: improve Monitor, Admin, and shared UI without requiring backend changes.

Files: Monitor, Admin, and shared component files.

Instructions:

- Improve table interactions.
- Improve confirmation text for dangerous actions.
- Improve keyboard behavior.
- Improve state transitions.
- Do not add new journeys.
- Do not add a new sign-in flow.
- Do not add panels that require new backend API behavior.

Done when the polish changes land without contract changes and the Phase 1 smoke runbook still passes unchanged.
