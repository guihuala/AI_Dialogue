const rawApiBase = String(import.meta.env.VITE_API_BASE_URL || '').trim();

function resolveApiBase(): string {
  if (rawApiBase) {
    const normalized = rawApiBase.replace(/\/+$/, '');
    return /\/api$/i.test(normalized) ? normalized : `${normalized}/api`;
  }

  if (typeof window !== 'undefined') {
    const host = String(window.location.hostname || '').toLowerCase();
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://127.0.0.1:8000/api';
    }
  }

  return '/api';
}

export const API_BASE = resolveApiBase();

