// ─── Legacy class — used by admin and monitor until those apps are rewritten ───

export class ApiClient {
  constructor(baseUrl = "/api", defaultHeaders = {}) {
    this.baseUrl = baseUrl;
    this.defaultHeaders = defaultHeaders;
  }

  async get(endpoint) {
    return this._request(endpoint, { method: "GET" });
  }

  async post(endpoint, body, options = {}) {
    return this._request(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...this.defaultHeaders,
        ...(options.headers || {}),
      },
      body: JSON.stringify(body),
    });
  }

  async delete(endpoint) {
    return this._request(endpoint, { method: "DELETE" });
  }

  async put(endpoint, body, options = {}) {
    return this._request(endpoint, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...this.defaultHeaders,
        ...(options.headers || {}),
      },
      body: JSON.stringify(body),
    });
  }

  async patch(endpoint, body, options = {}) {
    return this._request(endpoint, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...this.defaultHeaders,
        ...(options.headers || {}),
      },
      body: JSON.stringify(body),
    });
  }

  async _request(endpoint, options) {
    const headers = {
      "X-User-ID": "1",
      ...this.defaultHeaders,
      ...options.headers,
    };
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
      });
      if (!response.ok) {
        let payload = {};
        try {
          payload = await response.json();
        } catch {}
        const message =
          payload.detail ||
          payload.message ||
          `API Request Failed: ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        if (response.status === 503) {
          error.isMaintenance = true;
          if (
            typeof window !== "undefined" &&
            typeof window.dispatchEvent === "function"
          ) {
            window.dispatchEvent(
              new CustomEvent("image-tagger:maintenance", {
                detail: {
                  status: response.status,
                  endpoint: `${this.baseUrl}${endpoint}`,
                  message,
                },
              }),
            );
          }
        }
        throw error;
      }
      if (response.status === 204) return null;
      return await response.json();
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }
}

import { resolveApiBaseUrl, resolveAssetUrl } from "./api-config.js";

// ─── Contract-aligned journey clients (B-1) ──────────────────────────────────

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

// Mock state control — set window.__MOCK_FLAGS in the browser console to
// override the state for a specific journey without changing component code.
// e.g. window.__MOCK_FLAGS = { explorer: 'error', workbench: 'empty' }
function mockFlag(journey) {
  if (typeof window !== "undefined" && window.__MOCK_FLAGS?.[journey]) {
    return window.__MOCK_FLAGS[journey];
  }
  return "success";
}

function mockDelay() {
  return new Promise((resolve) =>
    setTimeout(resolve, 150 + Math.random() * 250),
  );
}

async function readJsonResponse(res) {
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return res.json();
  }
  const text = await res.text();
  if (text.trimStart().startsWith("<!")) {
    throw new Error(
      "API returned HTML instead of JSON. Set VITE_API_BASE_URL to your Render backend URL at build time.",
    );
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`API returned non-JSON response (HTTP ${res.status}).`);
  }
}

async function liveFetch(path, options = {}) {
  const base = resolveApiBaseUrl();
  const res = await fetch(`${base}${path}`, options);
  if (!res.ok) {
    let body = {};
    try {
      body = await readJsonResponse(res);
    } catch (err) {
      if (err instanceof Error && err.message.includes("HTML")) throw err;
    }
    const err = new Error(body?.error?.message ?? `HTTP ${res.status}`);
    err.status = res.status;
    err.code = body?.error?.code;
    if (res.status === 503) err.isMaintenance = true;
    throw err;
  }
  if (res.status === 204) return null;
  return readJsonResponse(res);
}

function normalizeExplorerSearchItem(item, apiBase) {
  const meta = item?.meta_data ?? {};
  const thumb = item?.thumbnail_url ?? item?.url;
  return {
    id: item.id,
    url: resolveAssetUrl(item.url ?? thumb, apiBase),
    thumbnail_url: resolveAssetUrl(thumb, apiBase),
    room_type: item.room_type ?? meta.room_type ?? null,
    canonical_tags: item.canonical_tags ?? item.tags ?? [],
    validation_count: item.validation_count ?? 0,
  };
}

function normalizeExplorerSearchResponse(raw, { page, page_size }) {
  const apiBase = resolveApiBaseUrl();
  if (Array.isArray(raw)) {
    const items = raw.map((item) => normalizeExplorerSearchItem(item, apiBase));
    return { items, total: items.length, page, page_size };
  }
  const items = (raw?.items ?? []).map((item) =>
    normalizeExplorerSearchItem(item, apiBase),
  );
  return {
    items,
    total: raw?.total ?? items.length,
    page: raw?.page ?? page,
    page_size: raw?.page_size ?? page_size,
  };
}

/** Map backend upload payload to the contract shape Admin UI expects. */
function normalizeUploadResponse(raw, fileCount = 0) {
  const details = Array.isArray(raw?.items) ? raw.items : [];
  const items =
    typeof raw?.items === "number"
      ? raw.items
      : (raw?.created_count ?? details.length ?? fileCount);
  return {
    ...raw,
    items,
    upload_items: details,
    image_ids:
      raw?.image_ids ?? details.map((row) => row.image_id).filter((id) => id != null),
    job_id: raw?.job_id ?? null,
    status: raw?.status ?? "queued",
  };
}

/** Map backend budget fields to the contract shape Admin UI expects. */
function normalizeBudgetResponse(raw) {
  const spent = raw?.spent_usd ?? raw?.total_spent ?? 0;
  const limit = raw?.limit_usd ?? raw?.hard_limit ?? 0;
  const remaining =
    raw?.remaining_usd ?? Math.max(0, Number(limit) - Number(spent));
  return {
    ...raw,
    spent_usd: Number(spent),
    limit_usd: Number(limit),
    remaining_usd: Number(remaining),
    is_kill_switched: Boolean(raw?.is_kill_switched),
  };
}

function getDemoToken() {
  return import.meta.env.VITE_DEMO_TOKEN ?? null;
}

function bearerHeaders() {
  const token = getDemoToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function jsonResponse(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  });
}

function textResponse(body, status = 200, headers = {}) {
  return new Response(body, {
    status,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      ...headers,
    },
  });
}

function cloneJson(value) {
  return value == null ? value : JSON.parse(JSON.stringify(value));
}

function requestUrl(input) {
  const rawUrl = typeof input === "string" ? input : input?.url;
  return new URL(
    rawUrl,
    typeof window !== "undefined" ? window.location.origin : "http://localhost",
  );
}

function requestMethod(input, init) {
  return String(init?.method || input?.method || "GET").toUpperCase();
}

function parseJsonBody(init) {
  const body = init?.body;
  if (!body || typeof body !== "string") {
    return null;
  }
  try {
    return JSON.parse(body);
  } catch {
    return null;
  }
}

function parseFormDataCount(init) {
  const body = init?.body;
  if (typeof FormData === "undefined" || !(body instanceof FormData)) {
    return 0;
  }
  const files = body.getAll("files[]");
  if (files.length > 0) {
    return files.length;
  }
  return body.getAll("files").length;
}

function mockHeaders(extra = {}) {
  return {
    "Cache-Control": "no-store",
    ...extra,
  };
}

async function handleMockRequest(input, init = {}) {
  const url = requestUrl(input);
  const method = requestMethod(input, init);
  const path = url.pathname.replace(/\/$/, "");

  if (!/^\/(api\/)?v1\//.test(path)) {
    return null;
  }

  if (path === "/v1/explorer/search" && method === "GET") {
    const state = mockFlag("explorer");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock search error" } },
        500,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/explorer.js");
    if (state === "loading") {
      await new Promise((resolve) => setTimeout(resolve, 2500));
    }
    if (state === "empty") {
      return jsonResponse(
        cloneJson(mocks.searchEmptyResponse),
        200,
        mockHeaders(),
      );
    }
    const page = Number(url.searchParams.get("page") || 1);
    return jsonResponse(
      { ...cloneJson(mocks.searchResponse), page },
      200,
      mockHeaders(),
    );
  }

  if (path.startsWith("/v1/explorer/images/") && method === "GET") {
    const state = mockFlag("explorer");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock image fetch error" } },
        500,
        mockHeaders(),
      );
    }
    const imageId = Number(path.split("/").pop());
    const mocks = await import("./mocks/explorer.js");
    if (state === "loading") {
      await new Promise((resolve) => setTimeout(resolve, 2500));
    }
    const fixture =
      imageId === 102
        ? mocks.imageDetailNoLatents
        : imageId === 103
          ? mocks.imageDetailLowConfidence
          : mocks.imageDetail;
    return jsonResponse(
      { ...cloneJson(fixture), id: imageId },
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/explorer/attributes" && method === "GET") {
    const mocks = await import("./mocks/explorer.js");
    return jsonResponse(
      cloneJson(mocks.attributesResponse),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/explorer/image-sets" && method === "GET") {
    const state = mockFlag("explorer");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock image-sets error" } },
        500,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/explorer.js");
    if (state === "empty") {
      return jsonResponse(
        cloneJson(mocks.imageSetsEmptyResponse),
        200,
        mockHeaders(),
      );
    }
    return jsonResponse(
      cloneJson(mocks.imageSetsResponse),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/workbench/next" && method === "GET") {
    const state = mockFlag("workbench");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock workbench error" } },
        500,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/workbench.js");
    if (state === "empty") {
      return jsonResponse(cloneJson(mocks.nextEmpty), 200, mockHeaders());
    }
    const typeMap = {
      number: mocks.nextNumber,
      enum: mocks.nextEnum,
      boolean: mocks.nextBoolean,
    };
    const type =
      typeof window !== "undefined"
        ? (window.__MOCK_FLAGS?.workbenchType ?? "number")
        : "number";
    return jsonResponse(
      cloneJson(typeMap[type] ?? mocks.nextNumber),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/workbench/validate" && method === "POST") {
    const mocks = await import("./mocks/workbench.js");
    return jsonResponse(cloneJson(mocks.validateResponse), 200, mockHeaders());
  }

  if (path === "/v1/workbench/latent/next" && method === "GET") {
    const state = mockFlag("workbench");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock workbench error" } },
        500,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/workbench.js");
    if (state === "empty") {
      return jsonResponse(cloneJson(mocks.nextEmpty), 200, mockHeaders());
    }
    return jsonResponse(cloneJson(mocks.nextLatent), 200, mockHeaders());
  }

  if (path === "/v1/workbench/region" && method === "POST") {
    const payload = parseJsonBody(init) || {};
    return jsonResponse(
      { id: 901, ...payload, auto_label: null, auto_confidence: null },
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/monitor/velocity" && method === "GET") {
    const state = mockFlag("monitor");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock monitor error" } },
        500,
        mockHeaders(),
      );
    }
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.monitorRole === "non-supervisor"
    ) {
      return jsonResponse(
        { error: { code: "FORBIDDEN", message: "Forbidden" } },
        403,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/monitor.js");
    return jsonResponse(cloneJson(mocks.velocityResponse), 200, mockHeaders());
  }

  if (path === "/v1/monitor/irr" && method === "GET") {
    const state = mockFlag("monitor");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock monitor error" } },
        500,
        mockHeaders(),
      );
    }
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.monitorRole === "non-supervisor"
    ) {
      return jsonResponse(
        { error: { code: "FORBIDDEN", message: "Forbidden" } },
        403,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/monitor.js");
    if (
      state === "empty" ||
      (typeof window !== "undefined" && window.__MOCK_FLAGS?.irrEmpty)
    ) {
      return jsonResponse(
        cloneJson(mocks.irrEmptyResponse),
        200,
        mockHeaders(),
      );
    }
    return jsonResponse(cloneJson(mocks.irrResponse), 200, mockHeaders());
  }

  if (path === "/v1/monitor/pipeline_health" && method === "GET") {
    const mocks = await import("./mocks/monitor.js");
    return jsonResponse(
      cloneJson(mocks.pipelineHealthResponse),
      200,
      mockHeaders(),
    );
  }

  if (
    path.match(/^\/v1\/monitor\/image-sets\/[^/]+\/latent-status$/) &&
    method === "GET"
  ) {
    const state = mockFlag("monitor");
    if (state === "error") {
      return jsonResponse(
        { error: { code: "MOCK_ERROR", message: "Mock monitor error" } },
        500,
        mockHeaders(),
      );
    }
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.monitorRole === "non-supervisor"
    ) {
      return jsonResponse(
        { error: { code: "FORBIDDEN", message: "Forbidden" } },
        403,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/monitor.js");
    if (state === "empty") {
      return jsonResponse(
        cloneJson(mocks.latentStatusEmptyResponse),
        200,
        mockHeaders(),
      );
    }
    const variant =
      typeof window !== "undefined"
        ? window.__MOCK_FLAGS?.latentStatus
        : null;
    if (variant === "suspicious") {
      return jsonResponse(
        cloneJson(mocks.latentStatusSuspiciousResponse),
        200,
        mockHeaders(),
      );
    }
    return jsonResponse(
      cloneJson(mocks.latentStatusResponse),
      200,
      mockHeaders(),
    );
  }

  if (
    path.match(/^\/v1\/monitor\/image\/[^/]+\/validations$/) &&
    method === "GET"
  ) {
    const mocks = await import("./mocks/monitor.js");
    return jsonResponse(
      cloneJson(mocks.validationsResponse),
      200,
      mockHeaders(),
    );
  }

  if (
    path.match(/^\/v1\/monitor\/image\/[^/]+\/inspector$/) &&
    method === "GET"
  ) {
    const mocks = await import("./mocks/monitor.js");
    return jsonResponse(cloneJson(mocks.inspectorResponse), 200, mockHeaders());
  }

  if (path === "/v1/debug/pipeline_health" && method === "GET") {
    const mocks = await import("./mocks/monitor.js");
    return jsonResponse(
      cloneJson(mocks.pipelineHealthResponse),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/models" && method === "GET") {
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(cloneJson(mocks.modelsResponse), 200, mockHeaders());
  }

  if (path.match(/^\/v1\/admin\/models\/\d+$/) && method === "PATCH") {
    const mocks = await import("./mocks/admin.js");
    const modelId = Number(path.split("/").pop());
    const payload = parseJsonBody(init) || {};
    const current = (mocks.modelsResponse || []).find(
      (model) => model.id === modelId,
    ) || { id: modelId, name: `Model ${modelId}` };
    return jsonResponse(
      { ...cloneJson(current), ...payload },
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/budget" && method === "GET") {
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.adminRole === "non-admin"
    ) {
      return jsonResponse(
        { error: { code: "FORBIDDEN", message: "Forbidden" } },
        403,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(cloneJson(mocks.budgetResponse), 200, mockHeaders());
  }

  if (path.startsWith("/v1/admin/costs/daily") && method === "GET") {
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(
      cloneJson(mocks.costHistoryResponse),
      200,
      mockHeaders(),
    );
  }

  if (path.startsWith("/v1/admin/upload/jobs") && method === "GET") {
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(
      cloneJson(mocks.uploadJobsResponse),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/upload" && method === "POST") {
    const mocks = await import("./mocks/admin.js");
    const count =
      parseFormDataCount(init) || cloneJson(mocks.uploadResponse).items || 0;
    return jsonResponse(
      {
        ...cloneJson(mocks.uploadResponse),
        items: count,
        image_ids: Array.from({ length: count }, (_, index) => 101 + index),
      },
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/image-sets/import" && method === "POST") {
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.adminRole === "non-admin"
    ) {
      return jsonResponse(
        { error: { code: "FORBIDDEN", message: "Forbidden" } },
        403,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/admin.js");
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.importImageSet === "validation"
    ) {
      return jsonResponse(
        cloneJson(mocks.importImageSetValidationError),
        422,
        mockHeaders(),
      );
    }
    const payload = parseJsonBody(init) || {};
    return jsonResponse(
      {
        ...cloneJson(mocks.importImageSetResponse),
        slug:
          payload?.slug ?? mocks.importImageSetResponse.slug,
        total_in_file:
          Array.isArray(payload?.images)
            ? payload.images.length
            : mocks.importImageSetResponse.total_in_file,
      },
      200,
      mockHeaders(),
    );
  }

  if (
    path.match(/^\/v1\/admin\/image-sets\/[^/]+\/latent-runs$/) &&
    method === "POST"
  ) {
    if (
      typeof window !== "undefined" &&
      window.__MOCK_FLAGS?.adminRole === "non-admin"
    ) {
      return jsonResponse(
        { error: { code: "FORBIDDEN", message: "Forbidden" } },
        403,
        mockHeaders(),
      );
    }
    const mocks = await import("./mocks/admin.js");
    const imageSetId = path.split("/")[4];
    return jsonResponse(
      { ...cloneJson(mocks.latentRunResponse), image_set_id: imageSetId },
      200,
      mockHeaders(),
    );
  }

  if (path.startsWith("/v1/admin/kill-switch") && method === "POST") {
    const mocks = await import("./mocks/admin.js");
    const active = url.searchParams.get("active") === "true";
    return jsonResponse(
      active
        ? cloneJson(mocks.killSwitchEnabled)
        : cloneJson(mocks.killSwitchDisabled),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/vlm/config" && method === "GET") {
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(cloneJson(mocks.vlmConfigResponse), 200, mockHeaders());
  }

  if (path === "/v1/admin/vlm/config" && method === "POST") {
    const mocks = await import("./mocks/admin.js");
    const payload = parseJsonBody(init) || {};
    return jsonResponse(
      { ...cloneJson(mocks.vlmConfigResponse), ...payload },
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/vlm/test" && method === "POST") {
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(cloneJson(mocks.vlmTestResponse), 200, mockHeaders());
  }

  if (path === "/v1/admin/training/export" && method === "POST") {
    const mocks = await import("./mocks/admin.js");
    return jsonResponse(
      cloneJson(mocks.trainingExportResponse),
      200,
      mockHeaders(),
    );
  }

  if (path === "/v1/admin/export/images" && method === "GET") {
    return new Response(
      new Blob(["mock image export"], { type: "application/zip" }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/zip",
          "Content-Disposition":
            'attachment; filename="image_tagger_images_export.zip"',
          "Cache-Control": "no-store",
        },
      },
    );
  }

  if (path === "/v1/vlm-health/runs" && method === "GET") {
    return jsonResponse(
      [
        {
          run_id: "vlm_20260504_0001",
          created_at: "2026-05-04T17:30:00Z",
          has_variance_audit: true,
          has_turing_summary: true,
        },
        {
          run_id: "vlm_20260503_0008",
          created_at: "2026-05-03T15:05:00Z",
          has_variance_audit: false,
          has_turing_summary: true,
        },
      ],
      200,
      mockHeaders(),
    );
  }

  if (
    path.match(
      /^\/v1\/vlm-health\/runs\/[^/]+\/(variance-audit|turing-summary)$/,
    ) &&
    method === "GET"
  ) {
    const artifact = path.endsWith("/variance-audit")
      ? "variance audit"
      : "turing summary";
    return textResponse(`mock ${artifact}`, 200, {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    });
  }

  return null;
}

function installMockFetchInterceptor() {
  if (typeof window === "undefined" || typeof window.fetch !== "function") {
    return;
  }
  if (window.__IMAGE_TAGGER_MOCK_FETCH_INSTALLED__) {
    return;
  }
  const originalFetch = window.fetch.bind(window);
  window.__IMAGE_TAGGER_MOCK_FETCH_INSTALLED__ = true;
  window.fetch = async (input, init) => {
    const mockedResponse = await handleMockRequest(input, init);
    if (mockedResponse) {
      return mockedResponse;
    }
    return originalFetch(input, init);
  };
}

if (USE_MOCKS) {
  installMockFetchInterceptor();
}

// ─── Explorer (public — no auth) ─────────────────────────────────────────────

export const explorer = {
  async search({
    q = "",
    page = 1,
    page_size = 20,
    room_type,
    tag,
    image_set,
    latent_tag,
    effect_domain,
    min_value,
  } = {}) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("explorer");
      if (state === "error")
        throw Object.assign(new Error("Mock search error"), {
          code: "MOCK_ERROR",
        });
      const mocks = await import("./mocks/explorer.js");
      if (state === "empty") return mocks.searchEmptyResponse;
      return { ...mocks.searchResponse, page };
    }
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(page_size),
    });
    if (q) params.set("q", q);
    if (room_type) params.set("room_type", room_type);
    if (tag) params.set("tag", tag);
    if (image_set) params.set("image_set", image_set);
    if (latent_tag) params.set("latent_tag", latent_tag);
    if (effect_domain) params.set("effect_domain", effect_domain);
    if (min_value !== undefined && min_value !== null && min_value !== "") {
      params.set("min_value", String(min_value));
    }
    const raw = await liveFetch(`/v1/explorer/search?${params}`);
    return normalizeExplorerSearchResponse(raw, { page, page_size });
  },

  async listImageSets() {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("explorer");
      if (state === "error")
        throw Object.assign(new Error("Mock image-sets error"), {
          code: "MOCK_ERROR",
        });
      const mocks = await import("./mocks/explorer.js");
      if (state === "empty") return mocks.imageSetsEmptyResponse;
      return mocks.imageSetsResponse;
    }
    const raw = await liveFetch("/v1/explorer/image-sets");
    // Normalize either {items:[…]} or a bare array.
    const items = Array.isArray(raw) ? raw : (raw?.items ?? []);
    return { items };
  },

  async getImage(imageId) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("explorer");
      if (state === "error")
        throw Object.assign(new Error("Mock image fetch error"), {
          code: "MOCK_ERROR",
        });
      const mocks = await import("./mocks/explorer.js");
      const fixture =
        imageId === 102
          ? mocks.imageDetailNoLatents
          : imageId === 103
            ? mocks.imageDetailLowConfidence
            : mocks.imageDetail;
      return { ...fixture, id: imageId };
    }
    const raw = await liveFetch(`/v1/explorer/images/${imageId}/detail`);
    const apiBase = resolveApiBaseUrl();
    const meta = raw?.meta_data ?? {};
    // Backend detail endpoint returns tags as List[TagInfo] objects {label, source, …};
    // components expect canonical_tags as string[].
    const rawTags = raw?.canonical_tags ?? raw?.tags ?? [];
    const canonicalTags = rawTags.map(t => (typeof t === "string" ? t : t?.label)).filter(Boolean);
    // Backend ImageSetMembership uses `id`; components key/read on `image_set_id`.
    const rawSets = raw?.image_sets ?? raw?.memberships ?? [];
    const imageSets = rawSets.map(m => ({ ...m, image_set_id: m.image_set_id ?? m.id }));
    return {
      ...raw,
      url: resolveAssetUrl(raw?.url, apiBase),
      thumbnail_url: resolveAssetUrl(raw?.thumbnail_url ?? raw?.url, apiBase),
      room_type: raw?.room_type ?? meta.room_type ?? null,
      canonical_tags: canonicalTags,
      image_sets: imageSets,
      latent_observations:
        raw?.latent_observations ?? raw?.latents ?? [],
      linked_effects: raw?.linked_effects ?? raw?.effects ?? [],
    };
  },

  async getAttributes() {
    if (USE_MOCKS) {
      await mockDelay();
      const mocks = await import("./mocks/explorer.js");
      return mocks.attributesResponse;
    }
    return liveFetch("/v1/explorer/attributes");
  },
};

// ─── Workbench (tagger role) ──────────────────────────────────────────────────

export const workbench = {
  async getNext() {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("workbench");
      if (state === "error")
        throw Object.assign(new Error("Mock workbench error"), {
          code: "MOCK_ERROR",
        });
      const mocks = await import("./mocks/workbench.js");
      if (state === "empty") return mocks.nextEmpty;
      const typeMap = {
        number: mocks.nextNumber,
        enum: mocks.nextEnum,
        boolean: mocks.nextBoolean,
      };
      const type = window.__MOCK_FLAGS?.workbenchType ?? "number";
      return typeMap[type] ?? mocks.nextNumber;
    }
    return liveFetch("/v1/workbench/next", {
      headers: bearerHeaders(),
    });
  },

  async validate(body) {
    if (USE_MOCKS) {
      await mockDelay();
      const mocks = await import("./mocks/workbench.js");
      return mocks.validateResponse;
    }
    return liveFetch("/v1/workbench/validate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...bearerHeaders(),
      },
      body: JSON.stringify(body),
    });
  },

  async createRegion(body) {
    if (USE_MOCKS) {
      await mockDelay();
      return { id: 901, ...body, auto_label: null, auto_confidence: null };
    }
    return liveFetch("/v1/workbench/region", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...bearerHeaders(),
      },
      body: JSON.stringify(body),
    });
  },

  async getNextLatent() {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("workbench");
      if (state === "error")
        throw Object.assign(new Error("Mock workbench error"), {
          code: "MOCK_ERROR",
        });
      const mocks = await import("./mocks/workbench.js");
      if (state === "empty") return mocks.nextEmpty;
      return mocks.nextLatent;
    }
    return liveFetch("/v1/workbench/latent/next", {
      headers: bearerHeaders(),
    });
  },
};

// ─── Monitor (supervisor role) ────────────────────────────────────────────────

export const monitor = {
  async getVelocity(window_hours = 24) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("monitor");
      if (state === "error")
        throw Object.assign(new Error("Mock monitor error"), {
          code: "MOCK_ERROR",
        });
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.monitorRole === "non-supervisor"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/monitor.js");
      return mocks.velocityResponse;
    }
    return liveFetch(`/v1/monitor/velocity?window_hours=${window_hours}`, {
      headers: bearerHeaders(),
    });
  },

  async getIRR() {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("monitor");
      if (state === "error")
        throw Object.assign(new Error("Mock monitor error"), {
          code: "MOCK_ERROR",
        });
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.monitorRole === "non-supervisor"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/monitor.js");
      if (state === "empty" || window.__MOCK_FLAGS?.irrEmpty)
        return mocks.irrEmptyResponse;
      return mocks.irrResponse;
    }
    return liveFetch("/v1/monitor/irr", {
      headers: bearerHeaders(),
    });
  },

  async getLatentStatus(imageSetId) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("monitor");
      if (state === "error")
        throw Object.assign(new Error("Mock monitor error"), {
          code: "MOCK_ERROR",
        });
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.monitorRole === "non-supervisor"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/monitor.js");
      if (state === "empty") return mocks.latentStatusEmptyResponse;
      const variant =
        typeof window !== "undefined"
          ? window.__MOCK_FLAGS?.latentStatus
          : null;
      if (variant === "suspicious") return mocks.latentStatusSuspiciousResponse;
      return mocks.latentStatusResponse;
    }
    return liveFetch(
      `/v1/monitor/image-sets/${encodeURIComponent(imageSetId)}/latent-status`,
      { headers: bearerHeaders() },
    );
  },
};

// ─── Admin (admin role) ───────────────────────────────────────────────────────

export const admin = {
  async upload(files) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("admin");
      if (state === "error")
        throw Object.assign(new Error("Mock upload error"), {
          code: "MOCK_ERROR",
        });
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.adminRole === "non-admin"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/admin.js");
      return {
        ...mocks.uploadResponse,
        items: files.length,
        image_ids: files.map((_, i) => 101 + i),
      };
    }
    const form = new FormData();
    for (const file of files) form.append("files[]", file);
    return normalizeUploadResponse(
      await liveFetch("/v1/admin/upload", {
        method: "POST",
        headers: bearerHeaders(),
        body: form,
      }),
      files.length,
    );
  },

  async getBudget() {
    if (USE_MOCKS) {
      await mockDelay();
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.adminRole === "non-admin"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/admin.js");
      return mocks.budgetResponse;
    }
    return normalizeBudgetResponse(
      await liveFetch("/v1/admin/budget", { headers: bearerHeaders() }),
    );
  },

  async setKillSwitch(enabled) {
    if (USE_MOCKS) {
      await mockDelay();
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.adminRole === "non-admin"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/admin.js");
      return enabled ? mocks.killSwitchEnabled : mocks.killSwitchDisabled;
    }
    return liveFetch("/v1/admin/kill-switch", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...bearerHeaders(),
      },
      body: JSON.stringify({ enabled }),
    });
  },

  async importImageSet(manifest) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("admin");
      if (state === "error")
        throw Object.assign(new Error("Mock import error"), {
          code: "MOCK_ERROR",
        });
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.adminRole === "non-admin"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/admin.js");
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.importImageSet === "validation"
      ) {
        const err = new Error("Request validation failed");
        err.status = 422;
        err.code = "VALIDATION_ERROR";
        err.body = mocks.importImageSetValidationError;
        throw err;
      }
      return {
        ...mocks.importImageSetResponse,
        slug: manifest?.slug ?? mocks.importImageSetResponse.slug,
        total_in_file: manifest?.images?.length
          ?? mocks.importImageSetResponse.total_in_file,
      };
    }
    return liveFetch("/v1/admin/image-sets/import", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...bearerHeaders(),
      },
      body: JSON.stringify(manifest),
    });
  },

  async runLatentDetectors(imageSetId) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag("admin");
      if (state === "error")
        throw Object.assign(new Error("Mock latent-run error"), {
          code: "MOCK_ERROR",
        });
      if (
        typeof window !== "undefined" &&
        window.__MOCK_FLAGS?.adminRole === "non-admin"
      )
        throw Object.assign(new Error("Forbidden"), { status: 403 });
      const mocks = await import("./mocks/admin.js");
      return { ...mocks.latentRunResponse, image_set_id: imageSetId };
    }
    return liveFetch(
      `/v1/admin/image-sets/${encodeURIComponent(imageSetId)}/latent-runs`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...bearerHeaders(),
        },
        body: JSON.stringify({}),
      },
    );
  },
};

// ─── Demo access helper ───────────────────────────────────────────────────────

export const demoAccess = {
  hasToken: () => Boolean(import.meta.env.VITE_DEMO_TOKEN),
  hasAdminToken: () => Boolean(import.meta.env.VITE_DEMO_TOKEN),
  hasTaggerToken: () => Boolean(import.meta.env.VITE_DEMO_TOKEN),
  hasSupervisorToken: () => Boolean(import.meta.env.VITE_DEMO_TOKEN),
};
