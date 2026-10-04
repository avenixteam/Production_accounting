import axios from 'axios';

// Production'da frontend va API bitta domenda: /api (Caddy orqaga yo'naltiradi).
// Lokal ishlab chiqarishda vite.config.js dagi proxy /api ni backend (8001) ga yuboradi.
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 20000,
});

const TOKEN_KEY = 'factory_token';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* brauzer saqlashga ruxsat bermasa - e'tibor bermaymiz */
  }
}

let unauthorizedHandler = null;
export function onUnauthorized(fn) {
  unauthorizedHandler = fn;
}

API.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = String(err?.config?.url || '');
    if (err?.response?.status === 401 && !url.includes('/auth/login')) unauthorizedHandler?.();
    return Promise.reject(err);
  },
);

/** Backend xatosini foydalanuvchiga tushunarli matnga aylantiradi. */
export function errMsg(err) {
  if (err?.code === 'ERR_NETWORK') return "Serverga ulanib bo'lmadi. Internet yoki server holatini tekshiring.";
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => `${(d.loc || []).filter((x) => x !== 'body').join('.')}: ${d.msg}`)
      .join('; ');
  }
  return err?.message || 'Noma\'lum xatolik';
}

export default API;
