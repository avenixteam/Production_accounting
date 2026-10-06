import { useCallback, useEffect, useState } from 'react';
import API, { errMsg } from '../api';

// Oxirgi javoblar keshi: sahifaga qaytganda eski ma'lumot DARHOL ko'rinadi,
// fonda yangisi yuklanadi (stale-while-revalidate).
const cache = new Map();
const MAX_CACHE = 100;

/** Chiqishda chaqiriladi: boshqa foydalanuvchi oldingi ma'lumotni ko'rmasligi uchun. */
export function clearFetchCache() {
  cache.clear();
}

/** GET so'rovi + qayta yuklash (reload). params o'zgarsa avtomatik qayta yuklanadi. */
export function useFetch(url, params) {
  const key = JSON.stringify(params ?? {});
  const cacheKey = `${url}?${key}`;
  const [tick, setTick] = useState(0);
  const [res, setRes] = useState({ key: null, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    const clean = Object.fromEntries(
      Object.entries(JSON.parse(key)).filter(([, v]) => v !== '' && v !== null && v !== undefined),
    );
    API.get(url, { params: clean })
      .then((r) => {
        if (cache.size >= MAX_CACHE) cache.clear();
        cache.set(cacheKey, r.data);
        if (!cancelled) setRes({ key: cacheKey, data: r.data, error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        setRes((prev) => ({
          key: cacheKey,
          data: prev.key === cacheKey ? prev.data : (cache.get(cacheKey) ?? null),
          error: errMsg(err),
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [url, key, cacheKey, tick]);

  const cached = cache.get(cacheKey);
  const fresh = res.key === cacheKey;
  const data = fresh ? res.data : (cached ?? null);
  const loading = !fresh && cached === undefined;
  const error = fresh ? res.error : null;

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, loading, error, reload };
}
