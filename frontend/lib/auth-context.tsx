"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authService } from "@/services/auth";
import type { User } from "@/types/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => void;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: () => {},
  setUser: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authService.isAuthenticated()) {
      authService
        .getMe()
        .then(setUser)
        .catch(() => authService.logout())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, logout: authService.logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
