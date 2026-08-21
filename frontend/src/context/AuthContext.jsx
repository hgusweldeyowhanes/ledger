import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { blogApi } from "../api/blog";
import { clearTokens, getAccess, setTokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    if (!getAccess()) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const me = await blogApi.me();
      setUser(me);
      return me;
    } catch {
      clearTokens();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const login = async (username, password) => {
    const tokens = await blogApi.login({ username, password });
    setTokens({ access: tokens.access, refresh: tokens.refresh });
    return refreshMe();
  };

  const register = async (payload) => {
    const data = await blogApi.register(payload);
    setTokens({ access: data.access, refresh: data.refresh });
    setUser(data.user);
    setLoading(false);
    return data.user;
  };

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshMe, isAuth: !!user }),
    [user, loading, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
