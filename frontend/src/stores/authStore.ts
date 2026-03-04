/**
 * Zustand store for authentication state.
 * Persists user info and manages login/logout.
 */
"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Subscription } from "@/types";
import { clearTokens, setTokens } from "@/lib/api";

interface AuthState {
  user: User | null;
  subscription: Subscription | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: User | null) => void;
  setSubscription: (subscription: Subscription | null) => void;
  login: (user: User, accessToken: string, refreshToken: string, subscription?: Subscription) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      subscription: null,
      isAuthenticated: false,
      isLoading: false,

      setUser: (user) =>
        set({ user, isAuthenticated: user !== null }),

      setSubscription: (subscription) =>
        set({ subscription }),

      login: (user, accessToken, refreshToken, subscription) => {
        setTokens(accessToken, refreshToken);
        set({
          user,
          subscription: subscription ?? null,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: () => {
        clearTokens();
        set({
          user: null,
          subscription: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: "icanrun-auth",
      // Only persist non-sensitive state (not tokens — stored in localStorage separately)
      partialize: (state) => ({
        user: state.user,
        subscription: state.subscription,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
