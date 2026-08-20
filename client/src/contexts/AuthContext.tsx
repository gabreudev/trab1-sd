import { useCallback, useEffect, useState } from "react";
import * as api from "../lib/api";
import { AuthContext } from "./auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<{ id: string; email: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Tenta recuperar sessão (checar se token ainda é válido)
    api
      .getMe()
      .then((data) => {
        setUser(data);
        setLoading(false);
      })
      .catch(() => {
        api.clearTokens();
        setUser(null);
        setLoading(false);
      });
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    try {
      const data = await api.signUp(email, password);
      setUser({ id: data.user_id, email: data.email });
      return {};
    } catch (e: any) {
      return { error: e.message };
    }
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const data = await api.signIn(email, password);
      setUser({ id: data.user_id, email: data.email });
      return {};
    } catch (e: any) {
      return { error: e.message };
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.signOut();
    } catch {
      // Os tokens já são removidos pelo cliente da API mesmo se o servidor
      // estiver indisponível ou a sessão tiver expirado.
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}
