"use client";

/**
 * Email confirmation page.
 *
 * Reads the `?token=...` query parameter, POSTs to /auth/confirm-email,
 * then shows success or error and redirects to /login after 3 seconds on success.
 *
 * The inner component is wrapped in a Suspense boundary (required by Next.js 14
 * App Router when useSearchParams() is used in a client component).
 */

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";

type Status = "loading" | "success" | "error" | "missing";

function ConfirmEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<Status>(token ? "loading" : "missing");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [countdown, setCountdown] = useState(3);
  const calledRef = useRef(false);

  useEffect(() => {
    if (!token || calledRef.current) return;
    calledRef.current = true;

    authApi
      .confirmEmail(token)
      .then(() => {
        setStatus("success");
      })
      .catch((err: unknown) => {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data
            ?.detail ?? "Ссылка недействительна или срок её действия истёк.";
        setErrorMessage(detail);
        setStatus("error");
      });
  }, [token]);

  // Countdown redirect after success
  useEffect(() => {
    if (status !== "success") return;
    if (countdown <= 0) {
      router.push("/login");
      return;
    }
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [status, countdown, router]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 w-full max-w-md text-center">
        <Link href="/" className="text-2xl font-bold text-blue-600">
          ICanRun
        </Link>

        {status === "loading" && (
          <div className="mt-10">
            <div className="animate-spin inline-block w-10 h-10 rounded-full border-4 border-blue-200 border-t-blue-600" />
            <p className="mt-4 text-sm text-gray-500">Подтверждаем ваш email...</p>
          </div>
        )}

        {status === "success" && (
          <div className="mt-8">
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-green-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>
            <h1 className="text-xl font-semibold text-gray-900">
              Email подтверждён!
            </h1>
            <p className="text-sm text-gray-500 mt-2">
              Ваш аккаунт активирован. Переход на страницу входа через{" "}
              <span className="font-medium text-gray-700">{countdown}</span> сек.
            </p>
            <Link
              href="/login"
              className="mt-6 inline-block px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Войти сейчас
            </Link>
          </div>
        )}

        {status === "error" && (
          <div className="mt-8">
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-red-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </div>
            </div>
            <h1 className="text-xl font-semibold text-gray-900">
              Не удалось подтвердить email
            </h1>
            <p className="text-sm text-gray-500 mt-2">{errorMessage}</p>
            <p className="text-xs text-gray-400 mt-4">
              Ссылка могла истечь. Запросите новое письмо на странице входа.
            </p>
            <Link
              href="/login"
              className="mt-6 inline-block text-sm text-blue-600 hover:text-blue-700 hover:underline"
            >
              Вернуться на страницу входа
            </Link>
          </div>
        )}

        {status === "missing" && (
          <div className="mt-8">
            <h1 className="text-xl font-semibold text-gray-900">
              Ссылка недействительна
            </h1>
            <p className="text-sm text-gray-500 mt-2">
              Токен подтверждения не найден в URL.
            </p>
            <Link
              href="/login"
              className="mt-6 inline-block text-sm text-blue-600 hover:text-blue-700 hover:underline"
            >
              Вернуться на страницу входа
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ConfirmEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="animate-spin w-10 h-10 rounded-full border-4 border-blue-200 border-t-blue-600" />
        </div>
      }
    >
      <ConfirmEmailContent />
    </Suspense>
  );
}
