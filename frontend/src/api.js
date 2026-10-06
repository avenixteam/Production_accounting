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

const XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
export const reportFilename = (date) => `kunlik_hisobot_${date}.xlsx`;

/** iPhone/iPad (iPadOS ham "Mac" deb ko'rinadi). Bu yerda fayl yuklab olish o'rniga "Ulashish" ishlatiladi. */
export const isIOS = () =>
  typeof navigator !== 'undefined' &&
  (/iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1));

/** Kunlik hisobot faylini serverdan oladi (Blob). */
export async function fetchDailyReport(date) {
  try {
    const res = await API.get('/reports/daily/excel', { params: { date }, responseType: 'blob', timeout: 60000 });
    return res.data;
  } catch (err) {
    // blob javobdagi xato matnini o'qiladigan qilamiz
    if (err?.response?.data instanceof Blob) {
      try {
        err.response.data = JSON.parse(await err.response.data.text());
      } catch {
        /* JSON emas - o'z holicha qoldiramiz */
      }
    }
    throw err;
  }
}

/** Faylni qurilmaga yuklab oladi (kompyuter, Android). */
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

/** Telefonning "Ulashish" oynasi bilan fayl yuborish (iPhone: Fayllarga saqlash, Telegram, Excel...). */
export function canShareFile(blob, filename) {
  if (typeof navigator === 'undefined' || !navigator.canShare || !navigator.share) return false;
  return navigator.canShare({ files: [new File([blob], filename, { type: XLSX_TYPE })] });
}

export async function shareFile(blob, filename) {
  await navigator.share({ files: [new File([blob], filename, { type: XLSX_TYPE })], title: filename });
}

export default API;
