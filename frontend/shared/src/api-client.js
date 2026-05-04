// ─── Legacy class (kept for existing app components until B-3 through B-6) ───

export class ApiClient {
  constructor(baseUrl = '/api', defaultHeaders = {}) {
    this.baseUrl = baseUrl;
    this.defaultHeaders = defaultHeaders;
  }

  async get(endpoint) {
    return this._request(endpoint, { method: 'GET' });
  }

  async post(endpoint, body, options = {}) {
    return this._request(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...this.defaultHeaders,
        ...(options.headers || {}),
      },
      body: JSON.stringify(body),
    });
  }

  async delete(endpoint) {
    return this._request(endpoint, { method: 'DELETE' });
  }

  async put(endpoint, body, options = {}) {
    return this._request(endpoint, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...this.defaultHeaders,
        ...(options.headers || {}),
      },
      body: JSON.stringify(body),
    });
  }

  async patch(endpoint, body, options = {}) {
    return this._request(endpoint, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...this.defaultHeaders,
        ...(options.headers || {}),
      },
      body: JSON.stringify(body),
    });
  }

  async _request(endpoint, options) {
    const headers = { 'X-User-ID': '1', ...this.defaultHeaders, ...options.headers };
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, { ...options, headers });
      if (!response.ok) {
        let payload = {};
        try { payload = await response.json(); } catch {}
        const message = payload.detail || payload.message || `API Request Failed: ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        if (response.status === 503) {
          error.isMaintenance = true;
          if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
            window.dispatchEvent(new CustomEvent('image-tagger:maintenance', {
              detail: { status: response.status, endpoint: `${this.baseUrl}${endpoint}`, message },
            }));
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

// ─── Contract-aligned journey clients (B-1) ──────────────────────────────────

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

// Mock state control — set window.__MOCK_FLAGS in the browser console to
// override the state for a specific journey without changing component code.
// e.g. window.__MOCK_FLAGS = { explorer: 'error', workbench: 'empty' }
function mockFlag(journey) {
  if (typeof window !== 'undefined' && window.__MOCK_FLAGS?.[journey]) {
    return window.__MOCK_FLAGS[journey];
  }
  return 'success';
}

function mockDelay() {
  return new Promise(resolve => setTimeout(resolve, 150 + Math.random() * 250));
}

async function liveFetch(path, options = {}) {
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
  const res = await fetch(`${base}${path}`, options);
  if (!res.ok) {
    let body = {};
    try { body = await res.json(); } catch {}
    const err = new Error(body?.error?.message ?? `HTTP ${res.status}`);
    err.status = res.status;
    err.code = body?.error?.code;
    if (res.status === 503) err.isMaintenance = true;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

function getDemoToken(role) {
  const map = {
    admin: import.meta.env.VITE_DEMO_ADMIN_JWT,
    tagger: import.meta.env.VITE_DEMO_TAGGER_JWT,
    supervisor: import.meta.env.VITE_DEMO_SUPERVISOR_JWT,
  };
  return map[role] ?? null;
}

function bearerHeaders(role) {
  const token = getDemoToken(role);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ─── Explorer (public — no auth) ─────────────────────────────────────────────

export const explorer = {
  async search({ q = '', page = 1, page_size = 20, room_type, tag } = {}) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag('explorer');
      if (state === 'error') throw Object.assign(new Error('Mock search error'), { code: 'MOCK_ERROR' });
      const mocks = await import('./mocks/explorer.js');
      if (state === 'empty') return mocks.searchEmptyResponse;
      return { ...mocks.searchResponse, page };
    }
    const params = new URLSearchParams({ page: String(page), page_size: String(page_size) });
    if (q) params.set('q', q);
    if (room_type) params.set('room_type', room_type);
    if (tag) params.set('tag', tag);
    return liveFetch(`/v1/explorer/search?${params}`);
  },

  async getImage(imageId) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag('explorer');
      if (state === 'error') throw Object.assign(new Error('Mock image fetch error'), { code: 'MOCK_ERROR' });
      const mocks = await import('./mocks/explorer.js');
      return { ...mocks.imageDetail, id: imageId };
    }
    return liveFetch(`/v1/explorer/images/${imageId}`);
  },

  async getAttributes() {
    if (USE_MOCKS) {
      await mockDelay();
      const mocks = await import('./mocks/explorer.js');
      return mocks.attributesResponse;
    }
    return liveFetch('/v1/explorer/attributes');
  },
};

// ─── Workbench (tagger role) ──────────────────────────────────────────────────

export const workbench = {
  async getNext() {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag('workbench');
      if (state === 'error') throw Object.assign(new Error('Mock workbench error'), { code: 'MOCK_ERROR' });
      const mocks = await import('./mocks/workbench.js');
      if (state === 'empty') return mocks.nextEmpty;
      const typeMap = { number: mocks.nextNumber, enum: mocks.nextEnum, boolean: mocks.nextBoolean };
      const type = window.__MOCK_FLAGS?.workbenchType ?? 'number';
      return typeMap[type] ?? mocks.nextNumber;
    }
    return liveFetch('/v1/workbench/next', { headers: bearerHeaders('tagger') });
  },

  async validate(body) {
    if (USE_MOCKS) {
      await mockDelay();
      const mocks = await import('./mocks/workbench.js');
      return mocks.validateResponse;
    }
    return liveFetch('/v1/workbench/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...bearerHeaders('tagger') },
      body: JSON.stringify(body),
    });
  },

  async createRegion(body) {
    if (USE_MOCKS) {
      await mockDelay();
      return { id: 901, ...body, auto_label: null, auto_confidence: null };
    }
    return liveFetch('/v1/workbench/region', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...bearerHeaders('tagger') },
      body: JSON.stringify(body),
    });
  },
};

// ─── Monitor (supervisor role) ────────────────────────────────────────────────

export const monitor = {
  async getVelocity(window_hours = 24) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag('monitor');
      if (state === 'error') throw Object.assign(new Error('Mock monitor error'), { code: 'MOCK_ERROR' });
      const mocks = await import('./mocks/monitor.js');
      return mocks.velocityResponse;
    }
    return liveFetch(`/v1/monitor/velocity?window_hours=${window_hours}`, {
      headers: bearerHeaders('supervisor'),
    });
  },

  async getIRR() {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag('monitor');
      if (state === 'error') throw Object.assign(new Error('Mock monitor error'), { code: 'MOCK_ERROR' });
      const mocks = await import('./mocks/monitor.js');
      if (state === 'empty' || window.__MOCK_FLAGS?.irrEmpty) return mocks.irrEmptyResponse;
      return mocks.irrResponse;
    }
    return liveFetch('/v1/monitor/irr', { headers: bearerHeaders('supervisor') });
  },
};

// ─── Admin (admin role) ───────────────────────────────────────────────────────

export const admin = {
  async upload(files) {
    if (USE_MOCKS) {
      await mockDelay();
      const state = mockFlag('admin');
      if (state === 'error') throw Object.assign(new Error('Mock upload error'), { code: 'MOCK_ERROR' });
      const mocks = await import('./mocks/admin.js');
      return { ...mocks.uploadResponse, items: files.length, image_ids: files.map((_, i) => 101 + i) };
    }
    const form = new FormData();
    for (const file of files) form.append('files[]', file);
    return liveFetch('/v1/admin/upload', { method: 'POST', headers: bearerHeaders('admin'), body: form });
  },

  async getBudget() {
    if (USE_MOCKS) {
      await mockDelay();
      const mocks = await import('./mocks/admin.js');
      return mocks.budgetResponse;
    }
    return liveFetch('/v1/admin/budget', { headers: bearerHeaders('admin') });
  },

  async setKillSwitch(enabled) {
    if (USE_MOCKS) {
      await mockDelay();
      const mocks = await import('./mocks/admin.js');
      return enabled ? mocks.killSwitchEnabled : mocks.killSwitchDisabled;
    }
    return liveFetch('/v1/admin/kill-switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...bearerHeaders('admin') },
      body: JSON.stringify({ enabled }),
    });
  },
};

// ─── Demo access helper ───────────────────────────────────────────────────────

export const demoAccess = {
  hasAdminToken: () => Boolean(import.meta.env.VITE_DEMO_ADMIN_JWT),
  hasTaggerToken: () => Boolean(import.meta.env.VITE_DEMO_TAGGER_JWT),
  hasSupervisorToken: () => Boolean(import.meta.env.VITE_DEMO_SUPERVISOR_JWT),
};