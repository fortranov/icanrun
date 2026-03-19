/**
 * Google OAuth — Terms Acceptance page.
 *
 * Shown to first-time Google sign-in users before creating their account.
 * Receives: ?token=xxx&name=xxx&email=xxx
 *
 * On submit: POST /auth/google/complete → receive tokens → login → /dashboard
 */
"use client";

import Link from "next/link";
import { Suspense, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiClient, authApi, setTokens } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";
import type { User, Subscription } from "@/types";

function AcceptTermsInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuthStore();

  const pendingToken = searchParams.get("token") ?? "";
  const name = searchParams.get("name") ?? "";
  const email = searchParams.get("email") ?? "";

  const [accepted, setAccepted] = useState(false);
  const [touched, setTouched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setTouched(true);

    if (!accepted) return;

    if (!pendingToken) {
      setError("Сессия устарела. Пожалуйста, начните вход заново.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await authApi.googleComplete(pendingToken);
      setTokens(data.access_token, data.refresh_token);

      const meRes = await apiClient.get<User & { subscription: Subscription | null }>(
        "/users/me"
      );
      const { subscription, ...user } = meRes.data;
      login(user as User, data.access_token, data.refresh_token, subscription ?? undefined);

      router.replace("/dashboard");
    } catch {
      setError("Не удалось создать аккаунт. Попробуйте ещё раз или войдите с паролем.");
      setLoading(false);
    }
  };

  if (!pendingToken) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 w-full max-w-md text-center">
          <p className="text-sm text-gray-500 mb-4">
            Сессия устарела или ссылка недействительна.
          </p>
          <Link href="/login" className="text-blue-600 hover:underline text-sm">
            Вернуться на страницу входа
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-6">
          <Link href="/" className="text-2xl font-bold text-blue-600">
            ICanRun
          </Link>
          <h1 className="text-xl font-semibold text-gray-900 mt-4">
            Создание аккаунта
          </h1>
          {name && (
            <p className="text-sm text-gray-500 mt-1">
              Добро пожаловать, {name}!
            </p>
          )}
          {email && (
            <p className="text-xs text-gray-400 mt-0.5">{email}</p>
          )}
        </div>

        <p className="text-sm text-gray-600 mb-5 leading-relaxed">
          Для завершения регистрации через Google необходимо принять условия
          Пользовательского соглашения.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Terms checkbox */}
          <div className="space-y-1">
            <div className="flex items-start gap-2">
              <input
                id="terms"
                type="checkbox"
                checked={accepted}
                onChange={(e) => {
                  setAccepted(e.target.checked);
                  setTouched(true);
                }}
                disabled={loading}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
              />
              <label htmlFor="terms" className="text-sm text-gray-600 cursor-pointer">
                Я принимаю{" "}
                <Link
                  href="/user-agreement"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  Пользовательское соглашение
                </Link>
              </label>
            </div>
            {touched && !accepted && (
              <p className="text-xs text-red-600">
                Необходимо принять пользовательское соглашение
              </p>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className={cn(
              "w-full py-2.5 rounded-lg text-sm font-medium transition-colors",
              "bg-blue-600 text-white hover:bg-blue-700",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
              loading && "opacity-60 cursor-not-allowed"
            )}
          >
            {loading ? "Создаём аккаунт..." : "Создать аккаунт"}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-gray-400">
          Не хотите создавать аккаунт?{" "}
          <Link href="/login" className="text-blue-500 hover:underline">
            Вернуться на страницу входа
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function AcceptTermsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AcceptTermsInner />
    </Suspense>
  );
}
