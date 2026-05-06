# FRONTEND PHASE 2

**Owner:** Engineer B. **Scope:** optional UX enhancements that improve speed and polish after the v1 experience is already functional. **Out of scope:** any change required to satisfy the contracted v1 user journeys.

## Phase 2 End State

Phase 2 is complete when:

- the workbench supports richer annotation interactions without changing the core contract
- explorer detail and frontend polish are noticeably stronger
- optional UI refinements improve usability without introducing new backend dependencies

Phase 2 must not block the v1 tag. If it slips, Phase 1 remains the shipped milestone.

## Task List

#### Task F-1: Advanced Workbench Annotation Enhancements
- **Goal:** Add region-annotation tooling and operator-efficiency features on top of the core workbench flow.
- **Files to create or modify:** `frontend/apps/workbench/src/RegionCanvas.jsx`, `frontend/apps/workbench/src/App.jsx`, `frontend/apps/workbench/src/KeyboardShortcuts.jsx`.
- **Implementation notes:** Implement `RegionCanvas` with plain `<canvas>` and mouse events. Add region submission against `POST /v1/workbench/region`, plus local undo for the most recent action in the session. Keep the phase constrained to the already contracted region schema; do not invent additional backend capabilities.
- **Acceptance criteria:** A tagger can create one region on a mock image, undo it locally, recreate it, and submit it successfully against the mocked contract; with live backend enabled and a valid tagger JWT, one region submission succeeds without console errors.
- **Depends on:** B-4, B-9 from Phase 1.

#### Task F-2: Explorer Performance and Presentation Polish
- **Goal:** Improve explorer responsiveness and detail-page readability beyond the functional baseline.
- **Files to create or modify:** `frontend/apps/explorer/src/ImageGrid.jsx`, `frontend/apps/explorer/src/ImageDetailModal.jsx`, `frontend/shared/src/theme.css`.
- **Implementation notes:** Focus on rendering polish, skeleton tuning, confidence visualization clarity, and performance cleanup. This task may refine but must not change the contract surface.
- **Acceptance criteria:** Lighthouse performance score is at least 85 on localhost for the explorer route; the detail modal remains contract-accurate while presenting trust and confidence data more clearly than the Phase 1 baseline.
- **Depends on:** B-3, B-7 from Phase 1.

#### Task F-3: Frontend Workflow Polish Pass
- **Goal:** Tighten the operator experience across monitor, admin, and shared UI without introducing new backend requirements.
- **Files to create or modify:** `frontend/apps/monitor/src/*`, `frontend/apps/admin/src/*`, `frontend/shared/src/components/*`.
- **Implementation notes:** Use this pass for improvements such as denser table interactions, clearer destructive-action confirmation copy, keyboard affordances, and state-transition polish. Do not add new journeys, new auth flows, or backend-dependent panels.
- **Acceptance criteria:** The optional polish pass lands without any contract changes, and the existing Phase 1 smoke runbook still passes unchanged.
- **Depends on:** B-5, B-6, B-9 from Phase 1.
