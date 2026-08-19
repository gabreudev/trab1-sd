import { createContext, useContext, useEffect, useState } from "react";
import * as api from "../lib/api";

interface AuthState {
  user: { id: string; email: string } | null;
  loading: boolean;
  signUp: (email: string, password: string) => Promise<{ error?: string }>;
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

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

  const signUp = async (email: string, password: string) => {
    try {
      const data = await api.signUp(email, password);
      setUser({ id: data.user_id, email: data.email });
      return {};
    } catch (e: any) {
      return { error: e.message };
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      const data = await api.signIn(email, password);
      setUser({ id: data.user_id, email: data.email });
      return {};
    } catch (e: any) {
      return { error: e.message };
    }
  };

  const signOut = async () => {
    await api.signOut();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, signUp, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
