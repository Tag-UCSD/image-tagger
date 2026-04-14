# Image Detail View — Specification & Implementation Plan

**Feature:** Single-image detail viewer for the Explorer app
**Version:** image-tagger v3.4.74
**Date:** 2026-02-20
**Status:** Proposed

---

## 1. Problem Statement

The Explorer app currently has no way to inspect a single image in detail. Clicking a card in the masonry grid toggles it into the export cart — there is no modal, drawer, or route for viewing an image at full resolution alongside its science attributes, debug visualizations, and human validations.

The Help text even says *"Click image thumbnails to inspect their tags and attributes"* (line 216 of `App.jsx`), but this behavior does not exist.

Researchers and TAs need to:

1. **View a single image at full resolution** without the masonry grid compressing it.
2. **Cycle through debug modes** (edges, depth, complexity, segmentation, room, materials) on that specific image with interactive controls, rather than switching the entire grid.
3. **Read all science-pipeline attributes** (color, texture, fractal, symmetry, fluency, spatial, style, cognitive) computed for that image.
4. **Read all human validation records** for that image.
5. **Navigate sequentially** (prev/next) through the current search result set without returning to the grid.

---

## 2. Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Component type** | Full-screen overlay (modal) inside Explorer | No router exists; adding one would be over-engineering. A modal keeps the grid state intact and allows instant close-to-return. |
| **Trigger** | Single-click on image opens detail view; cart selection moves to a checkbox affordance on each card | Resolves the current UX conflict where click = cart toggle, matching what the Help text already promises. |
| **Debug modes** | Per-image debug mode selector inside the detail view (dropdown or tab strip) with inline controls | More useful than grid-wide debug — researchers typically want to compare modes on one image. |
| **Data source for attributes** | New backend endpoint `GET /v1/explorer/images/{id}/detail` returning image + validations + attributes in one call | Avoids N+1 queries and keeps the frontend simple. |
| **Navigation** | Prev/Next arrows keyed to the current `images[]` array index | Simple, stateless, no pagination changes needed. |
| **Keyboard shortcuts** | `Escape` = close, `ArrowLeft` = prev, `ArrowRight` = next, `1-8` = debug mode toggle | Scientific tool users expect keyboard navigation. |

---

## 3. Architecture

### 3.1 New Backend Endpoint

**`GET /v1/explorer/images/{image_id}/detail`**

Returns a single JSON object with everything the detail view needs:

```python
# New schema: backend/schemas/discovery.py

class ImageDetailResult(BaseModel):
    """Full detail payload for the single-image viewer."""
    id: int
    url: str
    filename: str
    tags: List[str] = []
    meta_data: Dict[str, Any] = {}

    # Science pipeline attributes (from Validation table, source="science_pipeline*")
    science_attributes: List[AttributeValue] = []

    # Human validations (from Validation table, source="manual")
    human_validations: List[HumanValidation] = []

class AttributeValue(BaseModel):
    key: str
    name: str          # from Attribute registry
    category: str | None
    value: float
    source: str

class HumanValidation(BaseModel):
    user_id: int | None
    username: str | None
    attribute_key: str
    value: float
    duration_ms: int | None
    created_at: datetime | None
```

**Implementation** in `backend/api/v1_discovery.py`:

```python
@router.get("/images/{image_id}/detail", response_model=ImageDetailResult)
def get_image_detail(image_id: int, db=Depends(get_db), user=Depends(require_tagger)):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(404, "Image not found")

    validations = db.query(Validation).filter(Validation.image_id == image_id).all()

    science = [v for v in validations if v.source and v.source.startswith("science_pipeline")]
    human = [v for v in validations if v.source == "manual"]

    # Join attribute names from Attribute table
    attr_map = {a.key: a for a in db.query(Attribute).all()}

    return ImageDetailResult(
        id=image.id,
        url=_build_url(image),
        filename=image.meta_data.get("filename", f"image_{image.id}"),
        tags=image.meta_data.get("tags", []),
        meta_data=image.meta_data,
        science_attributes=[...],
        human_validations=[...],
    )
```

### 3.2 New Frontend Component

**File:** `frontend/apps/explorer/src/ImageDetailModal.jsx`

Single file, ~400-500 lines. No new dependencies.

#### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  [← Prev]  Image 42 of 1,024 — kitchen_modern_03.jpg  [Next →]  [✕ Close] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────┐  ┌──────────────┐  │
│  │                                      │  │ DEBUG MODE   │  │
│  │                                      │  │ ○ Original   │  │
│  │        Primary Image Display         │  │ ○ Edges      │  │
│  │        (debug mode applied)          │  │ ○ Overlay    │  │
│  │                                      │  │ ○ Depth      │  │
│  │        max-h with object-contain     │  │ ○ Complexity │  │
│  │        so image never clips          │  │ ○ Segment.   │  │
│  │                                      │  │ ○ Room       │  │
│  │                                      │  │ ○ Materials  │  │
│  │                                      │  │              │  │
│  │                                      │  │ [sliders]    │  │
│  └──────────────────────────────────────┘  │              │  │
│                                            │ ─────────── │  │
│                                            │ TAGS         │  │
│                                            │ Modern       │  │
│                                            │ Kitchen      │  │
│                                            │ High-Res     │  │
│                                            └──────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  SCIENCE ATTRIBUTES              │  HUMAN VALIDATIONS        │
│  ┌────────────────────────────┐  │  ┌──────────────────────┐ │
│  │ color                      │  │  │ user_3 | style.modern│ │
│  │   perceptual_lightness 0.62│  │  │   value: 0.80        │ │
│  │   lab_volume          0.45 │  │  │   dwell: 2,340ms     │ │
│  │   warmth_ratio        0.71 │  │  │   2026-02-18 14:22   │ │
│  │ texture                    │  │  │                      │ │
│  │   glcm_contrast       0.38 │  │  │ user_7 | style.modern│ │
│  │   ...                      │  │  │   value: 0.75        │ │
│  │ style                      │  │  │   dwell: 1,890ms     │ │
│  │   modern              0.91 │  │  │   ...                │ │
│  │   minimalist          0.78 │  │  │                      │ │
│  └────────────────────────────┘  │  └──────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### Component Props

```jsx
<ImageDetailModal
    images={images}           // Full search result array (for prev/next)
    initialIndex={clickedIdx} // Index of clicked image
    debugMode={debugMode}     // Current global debug mode (inherited)
    edgeThresholds={edgeThresholds}
    overlayOpacity={overlayOpacity}
    segmentationConf={segmentationConf}
    onClose={() => setDetailIndex(null)}
    onAddToCart={(id) => toggleCart(id)}
    cart={cart}
/>
```

#### Internal State

```jsx
const [currentIndex, setCurrentIndex] = useState(initialIndex);
const [localDebugMode, setLocalDebugMode] = useState(debugMode);
const [detail, setDetail] = useState(null);        // ImageDetailResult from API
const [detailLoading, setDetailLoading] = useState(false);
const [detailError, setDetailError] = useState(null);

// Local copies of debug controls so the modal can adjust independently
const [localEdgeThresholds, setLocalEdgeThresholds] = useState(edgeThresholds);
const [localOverlayOpacity, setLocalOverlayOpacity] = useState(overlayOpacity);
const [localSegConf, setLocalSegConf] = useState(segmentationConf);
```

---

## 4. Implementation Plan — Step-by-Step

Each step is designed to be independently verifiable. An agent should complete each step fully, test it, and only then proceed.

### Step 1: Backend — Add Detail Endpoint

**Files to modify:**
- `backend/schemas/discovery.py` — Add `AttributeValue`, `HumanValidation`, `ImageDetailResult` schemas
- `backend/api/v1_discovery.py` — Add `GET /images/{image_id}/detail` endpoint

**Acceptance criteria:**
- `GET /v1/explorer/images/1/detail` returns 200 with correct shape
- Science attributes grouped by namespace prefix
- Human validations include username (joined from User table)
- Returns 404 for nonexistent image IDs

**Testing:** `curl` or pytest against the endpoint.

---

### Step 2: Frontend — Create ImageDetailModal Component (Skeleton)

**Files to create:**
- `frontend/apps/explorer/src/ImageDetailModal.jsx`

**Scope:** Modal shell only — overlay, close button, header with nav arrows, image display area, placeholder panels for attributes. No debug mode switching yet, no API call yet.

**Acceptance criteria:**
- Modal renders as a fixed full-screen overlay with `z-50`
- Escape key closes the modal
- Left/Right arrows navigate (updating `currentIndex`)
- Close button works
- Image displays using `img.url` from the `images[]` prop

---

### Step 3: Frontend — Wire Modal into Explorer Grid

**Files to modify:**
- `frontend/apps/explorer/src/App.jsx`

**Changes:**
- Add `detailIndex` state (`null` when no modal is open)
- Change card `onClick`: single-click opens detail view (`setDetailIndex(idx)`)
- Move cart-toggle to a small checkbox/button in the card corner (click stops propagation)
- Render `<ImageDetailModal>` when `detailIndex !== null`
- Pass all required props

**Acceptance criteria:**
- Clicking an image card opens the detail modal
- Clicking the checkbox on a card adds/removes from cart without opening the modal
- Clicking outside the modal or pressing Escape closes it
- Grid state (search results, filters) is preserved when modal opens/closes

---

### Step 4: Frontend — Fetch and Display Detail Data

**Files to modify:**
- `frontend/apps/explorer/src/ImageDetailModal.jsx`

**Changes:**
- `useEffect` fetches `GET /v1/explorer/images/{id}/detail` when `currentIndex` changes
- Render science attributes in a grouped, collapsible list (grouped by namespace prefix)
- Render human validations in a simple table
- Render tags as pills
- Show loading spinner while fetching
- Show error state on failure

**Acceptance criteria:**
- Navigating between images triggers a new fetch
- Attributes are grouped by prefix (color.*, texture.*, style.*, etc.)
- Values display with 2 decimal places
- Human validations show username, attribute key, value, dwell time, timestamp
- Loading and error states are visible

---

### Step 5: Frontend — Debug Mode Switching in Modal

**Files to modify:**
- `frontend/apps/explorer/src/ImageDetailModal.jsx`

**Changes:**
- Add a vertical radio-button group for debug modes (right panel)
- When a mode is selected, swap the `<img>` src to the corresponding debug endpoint URL
- Show relevant sliders (edge thresholds, overlay opacity, segmentation confidence) beneath the radio buttons
- For overlay mode, stack two `<img>` tags with `mix-blend-screen`

**Acceptance criteria:**
- All 8 debug modes work (none, edges, overlay, depth, complexity, segmentation, room, materials)
- Sliders are mode-appropriate (only shown when relevant)
- Debug mode state is local to the modal (does not affect the grid)
- Number keys 1-8 toggle debug modes as a keyboard shortcut

---

### Step 6: Frontend — Cart Integration & Polish

**Files to modify:**
- `frontend/apps/explorer/src/ImageDetailModal.jsx`
- `frontend/apps/explorer/src/App.jsx`

**Changes:**
- Add "Add to Cart" / "Remove from Cart" button in the modal header
- Show cart state (blue highlight) on the image when it's in the cart
- Add image filename and resolution to the header bar
- Add `meta_data` display (upload batch, source, etc.) as a collapsible section
- Responsive layout: stack panels vertically on narrow screens

**Acceptance criteria:**
- Cart button reflects current cart state and toggles correctly
- Changes to cart in the modal are reflected in the grid when the modal closes
- Layout degrades gracefully on tablet-width screens

---

## 5. Keyboard Shortcuts Reference

| Key | Action |
|---|---|
| `Escape` | Close detail modal |
| `ArrowLeft` | Previous image |
| `ArrowRight` | Next image |
| `1` | Debug: Off (Original) |
| `2` | Debug: Edges |
| `3` | Debug: Overlay |
| `4` | Debug: Depth |
| `5` | Debug: Complexity |
| `6` | Debug: Segmentation |
| `7` | Debug: Room |
| `8` | Debug: Materials |
| `c` | Toggle cart for current image |

---

## 6. Files Changed Summary

| File | Action | Description |
|---|---|---|
| `backend/schemas/discovery.py` | Modify | Add `AttributeValue`, `HumanValidation`, `ImageDetailResult` |
| `backend/api/v1_discovery.py` | Modify | Add `GET /images/{image_id}/detail` |
| `frontend/apps/explorer/src/ImageDetailModal.jsx` | Create | New component (~400-500 lines) |
| `frontend/apps/explorer/src/App.jsx` | Modify | Wire modal, change click behavior, add checkbox affordance |

---

## 7. Out of Scope

These are explicitly deferred to avoid scope creep:

- **Image zoom / pan** — Useful but adds complexity (pinch-zoom, scroll hijacking). Can be added later.
- **Side-by-side debug comparison** — Comparing two debug modes on the same image. Future enhancement.
- **Deep-link URL for detail view** — Would require adding a router. Not worth it for a single feature.
- **Editing attributes or validations** — The detail view is read-only. Editing belongs in Workbench.
- **Batch navigation beyond current page** — The detail view navigates within the current `images[]` result set (up to 48). Infinite scroll or cross-page nav is deferred.

---

## 8. Risk Mitigation

| Risk | Mitigation |
|---|---|
| Detail endpoint is slow (many joins) | Single query with eager loading; cache attribute registry in-memory |
| Debug mode images are slow to load | Existing disk cache on backend; add loading spinner in modal |
| Modal blocks grid scroll | Use `overflow-hidden` on body when modal is open; restore on close |
| Click behavior change breaks existing workflows | Cart toggle moves to an explicit checkbox — more discoverable, less accidental |

---

## 9. Dependencies

- **No new npm packages.** Uses existing React, Tailwind, Lucide icons.
- **No new Python packages.** Uses existing SQLAlchemy, FastAPI, Pydantic.
- **No database migrations.** Reads from existing `Image`, `Validation`, `Attribute` tables.
- **No new environment variables.**
