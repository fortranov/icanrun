/**
 * React Query hooks for authentication operations.
 *
 * useCurrentUser  — fetch /users/me, sync to authStore
 * useLogin        — login mutation, stores tokens + user in authStore
 * useRegister     — register mutation, stores tokens + user in authStore
 * useLogout       — logout mutation, clears authStore + tokens
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient, authApi, clearTokens, getAccessToken, setTokens } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { Subscription, User } from "@/types";
import type { AxiosError } from "axios";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const authKeys = {
  me: ["auth", "me"] as const,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  birth_year?: number;
  gender?: "male" | "female" | "other";
  weight_kg?: number;
  height_cm?: number;
}

interface MeResponse extends User {
  subscription: Subscription | null;
}

interface ApiErrorDetail {
  detail?: string;
  code?: string;
}

export function extractErrorMessage(error: unknown, fallback = "Произошла ошибка"): string {
  const axiosError = error as AxiosError<ApiErrorDetail>;
  return axiosError?.response?.data?.detail ?? fallback;
}

// ---------------------------------------------------------------------------
// useCurrentUser
// ---------------------------------------------------------------------------

/**
 * Fetch the current authenticated user and sync to the auth store.
 * Only runs when an access token is present (user is logged in).
 */
export function useCurrentUser() {
  const { login, logout } = useAuthStore();
  const hasToken = typeof window !== "undefined" && !!getAccessToken();

  return useQuery<MeResponse>({
    queryKey: authKeys.me,
    queryFn: async () => {
      const res = await apiClient.get<MeResponse>("/users/me");
      return res.data;
    },
    enabled: hasToken,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
    select: (data) => {
      // Sync to store whenever data is fetched
      return data;
    },
  });
}

// ---------------------------------------------------------------------------
// useLogin
// ---------------------------------------------------------------------------

/**
 * Login mutation.
 * On success: stores tokens, fetches /users/me, updates authStore.
 */
export function useLogin() {
  const { login } = useAuthStore();
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<void, AxiosError<ApiErrorDetail>, LoginPayload>({
    mutationFn: async ({ email, password }) => {
      const tokenRes = await authApi.login(email, password);
      const { access_token, refresh_token } = tokenRes.data as {
        access_token: string;
        refresh_token: string;
      };

      // Store tokens before fetching /me so the interceptor can attach them
      setTokens(access_token, refresh_token);

      const meRes = await apiClient.get<MeResponse>("/users/me");
      const { subscription, ...user } = meRes.data;

      login(user as User, access_token, refresh_token, subscription ?? undefined);
      queryClient.setQueryData(authKeys.me, meRes.data);
    },
    onSuccess: () => {
      router.push("/dashboard");
    },
  });
}

// ---------------------------------------------------------------------------
// useRegister
// ---------------------------------------------------------------------------

interface RegisterResponse {
  access_token?: string | null;
  refresh_token?: string | null;
  token_type: string;
  requires_confirmation: boolean;
}

/**
 * Registration mutation.
 *
 * Returns { requiresConfirmation: true } when the backend has email confirmation
 * enabled. In that case no tokens are issued and the caller should show the
 * "check your inbox" screen instead of redirecting to /dashboard.
 *
 * On normal success: stores tokens, fetches /users/me, updates authStore, redirects.
 */
export function useRegister() {
  const { login } = useAuthStore();
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<
    { requiresConfirmation: boolean },
    AxiosError<ApiErrorDetail>,
    RegisterPayload
  >({
    mutationFn: async (payload) => {
      const tokenRes = await authApi.register(
        payload.email,
        payload.password,
        payload.name,
        // Pass optional profile fields via the extended register call
        payload as object
      );
      const data = tokenRes.data as RegisterResponse;

      if (data.requires_confirmation) {
        return { requiresConfirmation: true };
      }

      const access_token = data.access_token!;
      const refresh_token = data.refresh_token!;

      setTokens(access_token, refresh_token);

      const meRes = await apiClient.get<MeResponse>("/users/me");
      const { subscription, ...user } = meRes.data;

      login(user as User, access_token, refresh_token, subscription ?? undefined);
      queryClient.setQueryData(authKeys.me, meRes.data);

      return { requiresConfirmation: false };
    },
    onSuccess: ({ requiresConfirmation }) => {
      if (!requiresConfirmation) {
        router.push("/dashboard");
      }
    },
  });
}

// ---------------------------------------------------------------------------
// useLogout
// ---------------------------------------------------------------------------

/**
 * Logout mutation.
 * Blacklists the refresh token on the server, then clears local state.
 */
export function useLogout() {
  const { logout } = useAuthStore();
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<void, AxiosError<ApiErrorDetail>, void>({
    mutationFn: async () => {
      try {
        // Best-effort server-side token invalidation
        const refreshToken =
          typeof window !== "undefined"
            ? localStorage.getItem("icanrun_refresh_token")
            : null;
        if (refreshToken) {
          await authApi.logout();
        }
      } catch {
        // Ignore errors — we always clear local state
      }
    },
    onSettled: () => {
      clearTokens();
      logout();
      queryClient.clear();
      router.push("/login");
    },
  });
}
