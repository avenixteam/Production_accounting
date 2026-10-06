import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import API, { getToken, onUnauthorized, setToken } from '../api';
import { clearFetchCache } from '../hooks/useFetch';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!getToken());

  const logout = useCallback(() => {
    setToken(null);
    clearFetchCache();
    setUser(null);
  }, []);

  useEffect(() => {
    onUnauthorized(logout); // token muddati tugasa yoki yaroqsiz bo'lsa - login sahifasiga
  }, [logout]);

  useEffect(() => {
    if (!getToken()) return;
    let cancelled = false;
    API.get('/auth/me')
      .then((r) => !cancelled && setUser(r.data))
      .catch(() => !cancelled && setToken(null))
      .finally(() => !cancelled && setReady(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username, password) => {
    const { data } = await API.post('/auth/login', { username, password });
    setToken(data.access_token);
    clearFetchCache();
    setUser(data.user);
  }, []);

  const value = useMemo(() => ({ user, ready, login, logout }), [user, ready, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
