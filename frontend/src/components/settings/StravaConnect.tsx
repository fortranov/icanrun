/**
 * StravaConnect — Strava integration settings block.
 *
 * Flow:
 *  1. "Connect Strava" → GET /strava/auth → redirect to Strava OAuth
 *  2. Strava redirects back to /strava/callback?code=... (frontend page)
 *  3. Callback page calls POST /strava/callback → saves tokens in DB
 *  4. User is redirected to /settings?strava=connected
 *
 * Tokens are stored in the backend database (SQLite on mounted volume).
 * They survive container redeployments.
 */
"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { stravaApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSearchParams } from "next/navigation";

interface StravaStatus {
  connected: boolean;
  athlete_id: number | null;
  athlete_name: string | null;
}

// Strava brand color
const STRAVA_ORANGE = "#FC4C02";

function StravaIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0 5 13.828h4.17" />
    </svg>
  );
}

export function StravaConnect() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const [syncResult, setSyncResult] = useState<{ synced: number; skipped: number } | null>(null);

  // Show success banner if redirected from /strava/callback
  const justConnected = searchParams.get("strava") === "connected";

  const { data: status, isLoading } = useQuery<StravaStatus>({
    queryKey: ["strava", "status"],
    queryFn: () => stravaApi.status(),
    staleTime: 30_000,
  });

  // Clear success banner after 5 s
  useEffect(() => {
    if (justConnected) {
      queryClient.invalidateQueries({ queryKey: ["strava", "status"] });
    }
  }, [justConnected, queryClient]);

  const { mutateAsync: startConnect, isPending: isConnecting } = useMutation({
    mutationFn: async () => {
      const { auth_url } = await stravaApi.getAuthUrl();
      window.location.href = auth_url;
    },
  });

  const { mutateAsync: disconnect, isPending: isDisconnecting } = useMutation({
    mutationFn: () => stravaApi.disconnect(),
    onSuccess: () => {
      setSyncResult(null);
      queryClient.invalidateQueries({ queryKey: ["strava", "status"] });
    },
  });

  const { mutateAsync: sync, isPending: isSyncing } = useMutation({
    mutationFn: () => stravaApi.sync(90),
    onSuccess: (data) => {
      setSyncResult(data);
      queryClient.invalidateQueries({ queryKey: ["workouts"] });
    },
  });

  const isConnected = status?.connected ?? false;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ backgroundColor: STRAVA_ORANGE }}
          >
            <StravaIcon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Strava</h2>
            <p className="text-xs text-gray-500">Импорт активностей из Strava</p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="px-6 py-5 space-y-4">
        {/* Success banner */}
        {justConnected && (
          <div className="rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-800">
            Strava успешно подключена!
          </div>
        )}

        {/* Sync result */}
        {syncResult && (
          <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
            Импортировано: <strong>{syncResult.synced}</strong> тренировок
            {syncResult.skipped > 0 && `, пропущено дублей: ${syncResult.skipped}`}
          </div>
        )}

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "w-2.5 h-2.5 rounded-full",
              isConnected ? "bg-green-500" : "bg-gray-300"
            )}
          />
          <span className="text-sm text-gray-700">
            {isLoading
              ? "Проверяем статус..."
              : isConnected
              ? `Подключено${status?.athlete_name ? ` (${status.athlete_name})` : ""}`
              : "Не подключено"}
          </span>
        </div>

        {/* Actions */}
        {isConnected ? (
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => sync()}
              disabled={isSyncing}
              className="flex-1 px-4 py-2 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
              style={{ backgroundColor: isSyncing ? undefined : STRAVA_ORANGE }}
            >
              {isSyncing ? "Синхронизация..." : "Синхронизировать"}
            </button>
            <button
              type="button"
              onClick={() => disconnect()}
              disabled={isDisconnecting}
              className="px-4 py-2 border border-red-200 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              {isDisconnecting ? "..." : "Отключить"}
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => startConnect()}
            disabled={isConnecting}
            className="w-full px-4 py-2 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            style={{ backgroundColor: STRAVA_ORANGE }}
          >
            <StravaIcon className="w-4 h-4" />
            {isConnecting ? "Переходим к Strava..." : "Подключить Strava"}
          </button>
        )}

        <p className="text-xs text-gray-400">
          Синхронизация импортирует ваши тренировки из Strava за последние 90 дней.
          Токены доступа хранятся в базе данных сервера.
        </p>
      </div>
    </div>
  );
}
