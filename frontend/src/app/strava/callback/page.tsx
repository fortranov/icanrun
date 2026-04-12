/**
 * Strava OAuth callback page.
 *
 * Strava redirects the user here after they grant access:
 *   /strava/callback?code=xxx&scope=xxx
 *
 * This page:
 *  1. Reads the `code` query parameter.
 *  2. Calls POST /strava/callback on the backend (authenticated with the user's JWT).
 *  3. On success → redirect to /settings?strava=connected.
 *  4. On error   → redirect to /settings?strava=error.
 */
"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { stravaApi } from "@/lib/api";

function StravaCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    const code = searchParams.get("code");
    const errorParam = searchParams.get("error");

    if (errorParam || !code) {
      // User denied Strava access
      router.replace("/settings?strava=error");
      return;
    }

    stravaApi
      .callback(code)
      .then(() => {
        router.replace("/settings?strava=connected");
      })
      .catch(() => {
        router.replace("/settings?strava=error");
      });
  }, [searchParams, router]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin mx-auto mb-4"
          style={{ borderColor: "#FC4C02", borderTopColor: "transparent" }}
        />
        <p className="text-sm text-gray-500">Подключаем Strava...</p>
      </div>
    </div>
  );
}

export default function StravaCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div
            className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: "#FC4C02", borderTopColor: "transparent" }}
          />
        </div>
      }
    >
      <StravaCallbackInner />
    </Suspense>
  );
}
