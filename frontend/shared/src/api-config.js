/** Production Render backend — matches render.yaml service name. */
export const DEFAULT_PRODUCTION_API_BASE =
  "https://image-tagger-backend.onrender.com";

/**
 * Resolve the API origin for live (non-mock) requests.
 * Vite bakes ``VITE_API_BASE_URL`` at build time; when it is missing on Vercel
 * the client used to call same-origin ``/v1/...`` and receive ``index.html``.
 */
export function resolveApiBaseUrl() {
  const configured = (import.meta.env.VITE_API_BASE_URL ?? "")
    .trim()
    .replace(/\/$/, "");
  if (configured) return configured;
  if (import.meta.env.PROD && import.meta.env.VITE_USE_MOCKS !== "true") {
    return DEFAULT_PRODUCTION_API_BASE;
  }
  return "";
}

/** Turn backend-relative asset paths into absolute URLs when needed. */
export function resolveAssetUrl(pathOrUrl, base = resolveApiBaseUrl()) {
  if (!pathOrUrl) return pathOrUrl;
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  if (pathOrUrl.startsWith("/") && base) return `${base}${pathOrUrl}`;
  return pathOrUrl;
}
