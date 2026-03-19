/**
 * Login page.
 * Uses react-hook-form + Zod validation.
 * Delegates auth logic to useLogin hook (React Query + authStore).
 *
 * Special case: when the server returns X-Error-Code: EMAIL_NOT_CONFIRMED,
 * we show a "resend confirmation" prompt.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { extractErrorMessage, useLogin } from "@/hooks/useAuth";
import { authApi } from "@/lib/api";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { cn } from "@/lib/utils";
import type { AxiosError } from "axios";

// ---------------------------------------------------------------------------
// Validation schema
// ---------------------------------------------------------------------------

const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Введите email")
    .email("Некорректный формат email"),
  password: z
    .string()
    .min(1, "Введите пароль")
    .min(8, "Пароль не менее 8 символов"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LoginPage() {
  const loginMutation = useLogin();
  const [resendEmail, setResendEmail] = useState<string | null>(null);
  const [resendStatus, setResendStatus] = useState<"idle" | "sending" | "done">("idle");
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    authApi.getAuthSettings().then((s) => setGoogleEnabled(s.google_oauth_enabled)).catch(() => {});
  }, []);

  const handleGoogleLogin = async () => {
    try {
      setGoogleLoading(true);
      const { auth_url } = await authApi.getGoogleAuthUrl();
      window.location.href = auth_url;
    } catch {
      setGoogleLoading(false);
    }
  };

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = (values: LoginFormValues) => {
    loginMutation.mutate(values, {
      onError: (err: unknown) => {
        // Detect unconfirmed email — offer resend option
        const axiosErr = err as AxiosError<{ detail?: string }>;
        const headers = axiosErr?.response?.headers as Record<string, string> | undefined;
        const errorCode = headers?.["x-error-code"];
        if (errorCode === "EMAIL_NOT_CONFIRMED" || axiosErr?.response?.status === 403) {
          setResendEmail(values.email);
        }
      },
    });
  };

  const handleResend = async () => {
    if (!resendEmail) return;
    setResendStatus("sending");
    try {
      await authApi.resendConfirmation(resendEmail);
      setResendStatus("done");
    } catch {
      // Always show "done" to prevent email enumeration
      setResendStatus("done");
    }
  };

  const serverError = loginMutation.isError
    ? extractErrorMessage(loginMutation.error, "Неверный email или пароль")
    : null;

  const isPending = loginMutation.isPending;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold text-blue-600">
            ICanRun
          </Link>
          <h1 className="text-xl font-semibold text-gray-900 mt-4">Войти</h1>
          <p className="text-sm text-gray-500 mt-1">
            Введите ваш email и пароль
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
          {/* Email field */}
          <div>
            <label
              htmlFor="login-email"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              disabled={isPending}
              {...register("email")}
              className={cn(
                "w-full border rounded-lg px-3 py-2 text-sm outline-none transition-colors",
                "focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                "disabled:bg-gray-50 disabled:text-gray-500",
                errors.email
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300 bg-white"
              )}
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-600">{errors.email.message}</p>
            )}
          </div>

          {/* Password field */}
          <div>
            <label
              htmlFor="login-password"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Пароль
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              disabled={isPending}
              {...register("password")}
              className={cn(
                "w-full border rounded-lg px-3 py-2 text-sm outline-none transition-colors",
                "focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                "disabled:bg-gray-50 disabled:text-gray-500",
                errors.password
                  ? "border-red-400 bg-red-50"
                  : "border-gray-300 bg-white"
              )}
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">
                {errors.password.message}
              </p>
            )}
          </div>

          {/* Server-side error */}
          {serverError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {serverError}

              {/* Resend confirmation prompt */}
              {resendEmail && (
                <div className="mt-2 pt-2 border-t border-red-100">
                  {resendStatus === "done" ? (
                    <p className="text-xs text-green-700">
                      Письмо отправлено. Проверьте папку «Спам».
                    </p>
                  ) : (
                    <button
                      type="button"
                      onClick={handleResend}
                      disabled={resendStatus === "sending"}
                      className="text-xs text-blue-700 hover:underline disabled:opacity-50"
                    >
                      {resendStatus === "sending"
                        ? "Отправляем..."
                        : "Отправить письмо повторно"}
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={isPending}
            className={cn(
              "w-full py-2.5 rounded-lg text-sm font-medium transition-colors",
              "bg-blue-600 text-white hover:bg-blue-700",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
              isPending && "opacity-60 cursor-not-allowed"
            )}
          >
            {isPending ? "Входим..." : "Войти"}
          </button>
        </form>

        {/* Google OAuth */}
        {googleEnabled && (
          <div className="mt-4">
            <div className="relative flex items-center my-4">
              <div className="flex-grow border-t border-gray-200" />
              <span className="mx-3 text-xs text-gray-400 shrink-0">или</span>
              <div className="flex-grow border-t border-gray-200" />
            </div>
            <GoogleButton onClick={handleGoogleLogin} loading={googleLoading} />
          </div>
        )}

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-gray-600">
          Нет аккаунта?{" "}
          <Link
            href="/register"
            className="text-blue-600 hover:text-blue-700 font-medium hover:underline"
          >
            Зарегистрироваться
          </Link>
        </p>
      </div>
    </div>
  );
}
