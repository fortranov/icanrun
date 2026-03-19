/**
 * Google OAuth callback page.
 *
 * Google redirects the user here after they grant access:
 *   /auth/google/callback?code=xxx&state=xxx
 *
 * This page:
 *  1. Reads the `code` query parameter.
 *  2. Calls POST /auth/google/callback on the backend.
 *  3a. If the backend returns tokens → log the user in and redirect to /dashboard.
 *  3b. If requires_terms_acceptance → redirect to /auth/google/accept-terms.
 *  4. On any error → redirect to /login?error=google_failed.
 */
"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { apiClient, authApi, setTokens } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import type { User, Subscription } from "@/types";

function GoogleCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuthStore();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const code = searchParams.get("code");
    const errorParam = searchParams.get("error");

    if (errorParam || !code) {
      // User denied access or no code
      router.replace("/login?error=google_failed");
      return;
    }

    const redirectUri = window.location.origin + "/auth/google/callback";

    authApi
      .googleCallback(code, redirectUri)
      .then(async (data) => {
        if (data.requires_terms_acceptance) {
          // New user — redirect to terms acceptance page
          const params = new URLSearchParams({
            token: data.pending_token ?? "",
            name: data.name ?? "",
            email: data.email ?? "",
          });
          router.replace(`/auth/google/accept-terms?${params.toString()}`);
          return;
        }

        // Existing user — store tokens and fetch profile
        if (!data.access_token || !data.refresh_token) {
          router.replace("/login?error=google_failed");
          return;
        }

        setTokens(data.access_token, data.refresh_token);

        const meRes = await apiClient.get<User & { subscription: Subscription | null }>(
          "/users/me"
        );
        const { subscription, ...user } = meRes.data;
        login(user as User, data.access_token, data.refresh_token, subscription ?? undefined);

        router.replace("/dashboard");
      })
      .catch(() => {
        router.replace("/login?error=google_failed");
      });
  }, [searchParams, router, login]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-gray-500">Выполняем вход через Google...</p>
      </div>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <GoogleCallbackInner />
    </Suspense>
  );
}
