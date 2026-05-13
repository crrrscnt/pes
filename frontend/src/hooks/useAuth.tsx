import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { authApi } from '../api/endpoints';
import type { User } from '../types';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const response = await authApi.me();
      setUser(response.data);
    } catch (error: unknown) {
      // 401 — ожидаемо для незалогиненного пользователя
      if ((error as any)?.response?.status !== 401) {
        console.error('Auth refresh failed:', error);
      }
      setUser(null);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    setUser(response.data.user);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await authApi.register({ email, password });
    // По дизайну системы регистрация НЕ логинит автоматически
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, [refreshUser]);

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
