/**
 * GarminConnect — Garmin integration settings block.
 *
 * Shows connection status and provides connect/disconnect/sync actions.
 * Available for Trial, Basic, and Pro subscribers.
 *
 * Note: Garmin backend service is a future implementation.
 * This component shows the UI scaffold with API calls stubbed.
 */
"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { garminApi } from "@/lib/api";
import { useSubscription } from "@/hooks/useSubscription";
import { cn } from "@/lib/utils";

interface GarminStatus {
  connected: boolean;
  username?: string;
  last_sync?: string;
}

export function GarminConnect() {
  const { canUseGarmin } = useSubscription();
  const [showForm, setShowForm] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const { data: status, isLoading, refetch } = useQuery<GarminStatus>({
    queryKey: ["garmin", "status"],
    queryFn: async () => {
      try {
        const res = await garminApi.status();
        return res.data as GarminStatus;
      } catch {
        return { connected: false };
      }
    },
    staleTime: 30 * 1000,
  });

  const { mutateAsync: connect, isPending: isConnecting } = useMutation({
    mutationFn: () => garminApi.connect(username, password),
    onSuccess: () => {
      refetch();
      setShowForm(false);
      setUsername("");
      setPassword("");
      setFormError(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Не удалось подключить Garmin";
      setFormError(msg);
    },
  });

  const { mutateAsync: disconnect, isPending: isDisconnecting } = useMutation({
    mutationFn: () => garminApi.disconnect(),
    onSuccess: () => refetch(),
  });

  const { mutateAsync: sync, isPending: isSyncing } = useMutation({
    mutationFn: () => garminApi.sync(),
    onSuccess: () => refetch(),
  });

  if (!canUseGarmin) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Интеграция с Garmin
        </h2>
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          Интеграция с Garmin Connect доступна для подписок Trial, Basic и Pro.
        </div>
      </div>
    );
  }

  const isConnected = status?.connected ?? false;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <div className="flex items-center gap-3">
          {/* Garmin logo placeholder */}
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Garmin Connect
            </h2>
            <p className="text-xs text-gray-500">
              Импорт активностей из Garmin
            </p>
          </div>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* Connection status */}
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
              ? `Подключено${status?.username ? ` (${status.username})` : ""}`
              : "Не подключено"}
          </span>
        </div>

        {status?.last_sync && (
          <p className="text-xs text-gray-400">
            Последняя синхронизация:{" "}
            {new Date(status.last_sync).toLocaleString("ru-RU")}
          </p>
        )}

        {/* Actions */}
        {isConnected ? (
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => sync()}
              disabled={isSyncing}
              className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
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
          <>
            {showForm ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Email Garmin Connect
                  </label>
                  <input
                    type="email"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="your@email.com"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Пароль
                  </label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                {formError && (
                  <div className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">
                    {formError}
                  </div>
                )}
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => connect()}
                    disabled={isConnecting || !username || !password}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {isConnecting ? "Подключаем..." : "Подключить"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowForm(false);
                      setFormError(null);
                    }}
                    className="px-4 py-2 border border-gray-200 text-sm text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowForm(true)}
                className="w-full px-4 py-2 border border-blue-200 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 transition-colors"
              >
                Подключить Garmin Connect
              </button>
            )}
          </>
        )}

        <p className="text-xs text-gray-400">
          Ваши учётные данные Garmin хранятся в зашифрованном виде.
          Мы используем их только для импорта ваших активностей.
        </p>
      </div>
    </div>
  );
}
