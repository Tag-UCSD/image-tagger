# Shared Contract, Plain-Language Version

| Term | Plain meaning |
|---|---|
| API | Web addresses that the browser uses to ask the Python app for data or actions. |
| Endpoint | One specific API web address, such as `/health`. |
| Request | Data sent to an API endpoint. |
| Response | Data returned by an API endpoint. |
| JSON | A common text format for structured data. |
| JWT | A signed text token that says who a user is and what role they have. |
| Bearer token | A JWT sent in the `Authorization` header as `Bearer <jwt>`. |
| Role | A permission label such as `tagger`, `supervisor`, or `admin`. |
| Pagination | Splitting a long result list into pages. |
| Schema | A formal description of allowed data fields and types. |
| TypeScript | The JavaScript-based type system used by the browser code. |
| Pydantic | The Python package used to define and check data shapes. |
| Multipart upload | The web format used when uploading files. |
| MIME type | A file type label such as `image/jpeg`. |
| Trust envelope | Extra fields attached to a model result that explain how well-supported that result is. |
| IRR | Inter-rater reliability: a measure of how consistently different labelers agree. |

## API Endpoints

All v1 API endpoints start with `/v1`.

Authentication rules:

- Explorer endpoints are public and do not need an `Authorization` header.
- Workbench, Monitor, and Admin endpoints require `Authorization: Bearer <jwt>`.
- The Python app must read identity and role from the JWT claims only.
- The Python app must not trust browser-supplied headers such as `X-User-Id` or `X-User-Role` for permission checks.

### Explorer: Public Browse

- `GET /v1/explorer/search?q=&page=&page_size=&room_type=&tag=` returns `ExplorerSearchResponse`
- `GET /v1/explorer/images/{image_id}` returns `ImageDetail`
- `GET /v1/explorer/attributes` returns `{ attributes: AttributeDef[] }`

Search pagination rules:

- `page` defaults to `1`
- `page` must be at least `1`
- `page_size` defaults to `20`
- `page_size` must be at least `1`
- `page_size` must be at most `100`

### Workbench: Human Labeling

- `GET /v1/workbench/next` returns `WorkbenchAssignment` or `{ empty: true }`
- `POST /v1/workbench/validate` receives `ValidationSubmit` and returns `{ validation_id: int, accepted: bool }`
- `POST /v1/workbench/region` receives `RegionCreate` and returns `Region`

### Monitor: Supervisor Review

- `GET /v1/monitor/velocity?window_hours=` returns `{ series: VelocityPoint[] }`
- `GET /v1/monitor/irr` returns `{ rows: IRRRow[] }`

### Admin

- `POST /v1/admin/upload` receives image files in multipart field `files[]` and returns `{ job_id: str, items: int, image_ids: int[], status: "queued" }`
- `GET /v1/admin/budget` returns `{ spent_usd: float, limit_usd: float, remaining_usd: float }`
- `POST /v1/admin/kill-switch` receives `{ enabled: bool }` and returns `{ enabled: bool, changed_at: iso8601 }`

### Health

- `GET /health` returns `{ status: "ok"|"degraded", version: str, db: bool, storage: bool }`

## Shared Data Types

Use these types in both the browser code and the Python code. Browser code can express them with TypeScript. Python code can express them with the Python package `pydantic`.

```ts
type Role = "tagger" | "scientist" | "supervisor" | "admin";

type JwtClaims = {
  sub: string;
  role: Role;
};

type TrustEvaluationStatus = "validated" | "proxy_validated" | "untested";

type TrustEnvelope<T> = {
  value: T;
  model_id: string;
  evaluation_status: TrustEvaluationStatus;
  confidence_interval_95: [number, number] | null;
  n_training: number;
  notes: string;
};

type ExplorerSearchResponse = {
  items: ImageSummary[];
  total: number;
  page: number;
  page_size: number;
};

type ImageSummary = {
  id: number;
  url: string;
  thumbnail_url: string;
  room_type: string | null;
  canonical_tags: string[];
  validation_count: number;
};

type AttributeDef = {
  id: number;
  key: string;
  name: string;
  category: string | null;
  level: string | null;
  range: string | null;
  sources: string | null;
  notes: string | null;
};

type RegionGeometry =
  | { type: "bbox"; x: number; y: number; width: number; height: number }
  | { type: "polygon"; points: Array<{ x: number; y: number }> };

type RegionCreate = {
  image_id: number;
  geometry: RegionGeometry;
  manual_label: string;
};

type Region = {
  id: number;
  image_id: number;
  geometry: RegionGeometry;
  auto_label: string | null;
  auto_confidence: number | null;
  manual_label: string | null;
};

type AffordancePrediction = {
  key: string;
  label: string;
  score: number;
  confidence: TrustEnvelope<number>;
};

type VelocityPoint = {
  timestamp: string;
  count: number;
};

type IRRRow = {
  attribute_key: string;
  attribute_name: string;
  irr: number;
  bin: "low" | "medium" | "high";
  n_pairs: number;
};

type ImageDetail = ImageSummary & {
  width: number;
  height: number;
  science: SciencePayload | null;
  regions: Region[];
};

type WorkbenchAssignment = {
  image: ImageDetail;
  assignment: {
    attribute_key: string;
    attribute_name: string;
    prompt: string;
    value_type: "boolean" | "number" | "enum";
    allowed_values: Array<string | number | boolean> | null;
    min: number | null;
    max: number | null;
    step: number | null;
    required: true;
  };
};

type SciencePayload = {
  run_id: number;
  run_status: "pending" | "running" | "completed" | "failed";
  features: Record<string, TrustEnvelope<number>>;
  affordances: AffordancePrediction[];
};

type ValidationSubmit = {
  image_id: number;
  attribute_key: string;
  value: string | number | boolean;
  duration_ms: number;
};

type ErrorDetail = {
  field: string;
  message: string;
  type: string;
};

type ErrorResponse = {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: ErrorDetail[];
  };
};
```

Region geometry rule: regions sent between browser and Python must use either a bounding box (`bbox`) or a polygon exactly as shown above.

## Machine-Learning Output Contract

Every machine-learning output must include a trust envelope:

```json
{
  "value": 5.8,
  "model_id": "affordance_L059_lgbm_v1",
  "evaluation_status": "validated",
  "confidence_interval_95": [5.2, 6.1],
  "n_training": 1523,
  "notes": "held-out test R2=0.71; see ML_EVALUATION.md#L059"
}
```

Allowed `evaluation_status` values:

- `validated`: checked with strong enough evidence
- `proxy_validated`: checked indirectly or with weaker evidence
- `untested`: not yet checked enough to claim evidence

Untested models must return `evaluation_status: "untested"`. The browser must show a visible warning badge for this status.

`SciencePayload.features` is a map from feature key to trust envelope. Do not add a separate confidence map for features.

## Monitor IRR Rules

`GET /v1/monitor/irr` returns a list of table rows.

Only include an `IRRRow` when the Python app has at least 10 overlapping label pairs for the same `attribute_key`, made by two different taggers across 10 different images.

If no attribute meets that minimum, return:

```json
{ "rows": [] }
```

The browser must show the agreed empty state for that response.

## Upload Policy

`POST /v1/admin/upload` accepts only:

- `image/jpeg`
- `image/png`
- `image/webp`

Upload limits:

- each file must be at most `10 MiB`
- each upload batch must contain at most `200` files

The browser upload checks must exactly match the Python API upload checks.

Upload validation errors must use the standard `ErrorResponse` shape. Multipart upload validation errors must use the message `Request validation failed`.

## Post-Upload Processing

`POST /v1/admin/upload` starts work and returns before all image analysis is done.

A successful upload means:

- the image batch was accepted
- image records were created
- the response includes the created `image_ids`
- the response `status` is `"queued"`

Explorer discoverability rules:

- an uploaded image becomes visible to Explorer as soon as its image record is saved
- the smoke-test image must be reachable by `GET /v1/explorer/images/{image_id}` within 5 seconds

Science processing rules:

- science processing runs after upload
- image detail may first return `science: null`, or `science.run_status` as `"pending"` or `"running"`
- for the v1 smoke test, science must reach `"completed"` within 60 seconds

## Workbench Assignment Rules

`GET /v1/workbench/next` returns one image and one assigned attribute to label, or `{ empty: true }`.

Rules:

- the tagger does not choose the attribute in v1
- the browser builds the form from `assignment`
- `allowed_values` is required for `value_type: "enum"` and otherwise must be `null`
- `min`, `max`, and `step` are required for `value_type: "number"` and otherwise must be `null`
- do not hardcode attribute-specific form rules in the browser

## Standard Error Response

Every non-success API response must use this shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "9bb4fd59-d495-4f0b-a9f0-6e57e8d22496",
    "details": [
      {
        "field": "page",
        "message": "Input should be greater than or equal to 1",
        "type": "greater_than_equal"
      }
    ]
  }
}
```

Use these error codes:

- `AUTH_REQUIRED`: missing or invalid bearer token
- `FORBIDDEN`: valid token, but the role does not have permission
- `VALIDATION_ERROR`: invalid query, body, or upload data
- `NOT_FOUND`: missing resource
- `RATE_LIMITED`: too many requests
- `INTERNAL_ERROR`: unexpected server failure

## Authentication Structure

- Supabase Auth issues JWTs.
- The Python app verifies JWT signatures using `SUPABASE_JWT_SECRET`.
- The user ID comes from JWT claim `sub`.
- The user role comes from top-level JWT claim `role`.
- Allowed roles are `tagger`, `scientist`, `supervisor`, and `admin`.
- Explorer is public.
- Workbench requires a valid JWT.
- Monitor and Admin require both a valid JWT and the correct role.

## Example Requests and Responses

These examples show the expected data shape. They use shortened data but the same field names as the contract.

### Explorer Search

Request:

```http
GET /v1/explorer/search?q=window&page=1&page_size=20&room_type=living_room&tag=biophilic
```

Response:

```json
{
  "items": [
    {
      "id": 101,
      "url": "https://cdn.example.com/images/101.jpg",
      "thumbnail_url": "https://cdn.example.com/images/101-thumb.jpg",
      "room_type": "living_room",
      "canonical_tags": ["biophilic", "window", "daylight"],
      "validation_count": 4
    }
  ],
  "total": 37,
  "page": 1,
  "page_size": 20
}
```

### Explorer Image Detail

Request:

```http
GET /v1/explorer/images/101
```

Response:

```json
{
  "id": 101,
  "url": "https://cdn.example.com/images/101.jpg",
  "thumbnail_url": "https://cdn.example.com/images/101-thumb.jpg",
  "room_type": "living_room",
  "canonical_tags": ["biophilic", "window", "daylight"],
  "validation_count": 4,
  "width": 1600,
  "height": 1200,
  "science": {
    "run_id": 8801,
    "run_status": "completed",
    "features": {
      "light.daylight_ratio": {
        "value": 0.84,
        "model_id": "feature_daylight_ratio_v1",
        "evaluation_status": "proxy_validated",
        "confidence_interval_95": [0.79, 0.88],
        "n_training": 0,
        "notes": "Derived feature; checked against an internal reference set."
      }
    },
    "affordances": [
      {
        "key": "L059",
        "label": "sleep_suitability",
        "score": 5.8,
        "confidence": {
          "value": 5.8,
          "model_id": "affordance_L059_lgbm_v1",
          "evaluation_status": "validated",
          "confidence_interval_95": [5.2, 6.1],
          "n_training": 1523,
          "notes": "held-out test R2=0.71; see ML_EVALUATION.md#L059"
        }
      }
    ]
  },
  "regions": []
}
```

### Workbench Assignment

Request:

```http
GET /v1/workbench/next
```

Response:

```json
{
  "image": {
    "id": 101,
    "url": "https://cdn.example.com/images/101.jpg",
    "thumbnail_url": "https://cdn.example.com/images/101-thumb.jpg",
    "room_type": "living_room",
    "canonical_tags": ["biophilic", "window"],
    "validation_count": 4,
    "width": 1600,
    "height": 1200,
    "science": null,
    "regions": []
  },
  "assignment": {
    "attribute_key": "light.daylight_ratio",
    "attribute_name": "Daylight Ratio",
    "prompt": "Estimate the fraction of the room lit by daylight.",
    "value_type": "number",
    "allowed_values": null,
    "min": 0,
    "max": 1,
    "step": 0.05,
    "required": true
  }
}
```

### Workbench Label Submission

Request:

```json
{
  "image_id": 101,
  "attribute_key": "light.daylight_ratio",
  "value": 0.9,
  "duration_ms": 18340
}
```

Response:

```json
{
  "validation_id": 4402,
  "accepted": true
}
```

### Monitor IRR

Request:

```http
GET /v1/monitor/irr
```

Response:

```json
{
  "rows": [
    {
      "attribute_key": "light.daylight_ratio",
      "attribute_name": "Daylight Ratio",
      "irr": 0.67,
      "bin": "high",
      "n_pairs": 28
    }
  ]
}
```

### Admin Upload

Request:

```http
POST /v1/admin/upload
Content-Type: multipart/form-data

files[]: living-room-01.jpg
```

Response:

```json
{
  "job_id": "upl_20260407_0001",
  "items": 1,
  "image_ids": [101],
  "status": "queued"
}
```

### Admin Budget

Request:

```http
GET /v1/admin/budget
```

Response:

```json
{
  "spent_usd": 4.25,
  "limit_usd": 15.0,
  "remaining_usd": 10.75
}
```

### Admin Kill Switch

Request:

```json
{
  "enabled": false
}
```

Response:

```json
{
  "enabled": false,
  "changed_at": "2026-04-07T17:41:12Z"
}
```

### Health

Request:

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "db": true,
  "storage": true
}
```

## Shared Environment Variables

Use these names for settings passed outside the code:

`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `IMAGE_STORAGE_ROOT`, `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `VLM_HARD_LIMIT_USD`, `LOG_LEVEL`, `SENTRY_DSN`, `CORS_ALLOWED_ORIGINS`.
