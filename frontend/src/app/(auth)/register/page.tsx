/**
 * Registration page.
 * Collects: name, email, password + optional athlete profile fields.
 * Uses react-hook-form + Zod validation.
 * Delegates auth logic to useRegister hook (React Query + authStore).
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { extractErrorMessage, useRegister } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Validation schema
// ---------------------------------------------------------------------------

const registerSchema = z
  .object({
    name: z
      .string()
      .min(1, "Введите ваше имя")
      .max(255, "Имя не более 255 символов"),
    email: z
      .string()
      .min(1, "Введите email")
      .email("Некорректный формат email"),
    password: z
      .string()
      .min(8, "Пароль не менее 8 символов")
      .max(128, "Пароль не более 128 символов"),
    password_confirm: z.string().min(1, "Подтвердите пароль"),

    // Optional athlete profile
    birth_year: z
      .string()
      .optional()
      .transform((v) => (v && v !== "" ? parseInt(v, 10) : undefined))
      .pipe(z.number().int().min(1900).max(2020).optional()),
    gender: z.enum(["male", "female", "other"]).optional(),
    weight_kg: z
      .string()
      .optional()
      .transform((v) => (v && v !== "" ? parseFloat(v) : undefined))
      .pipe(z.number().min(20).max(300).optional()),
    height_cm: z
      .string()
      .optional()
      .transform((v) => (v && v !== "" ? parseFloat(v) : undefined))
      .pipe(z.number().min(100).max(250).optional()),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Пароли не совпадают",
    path: ["password_confirm"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

// ---------------------------------------------------------------------------
// Reusable field component
// ---------------------------------------------------------------------------

function Field({
  label,
  error,
  children,
  hint,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      {children}
      {hint && !error && (
        <p className="mt-1 text-xs text-gray-400">{hint}</p>
      )}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function RegisterPage() {
  const registerMutation = useRegister();
  const [showProfile, setShowProfile] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      password_confirm: "",
      gender: undefined,
    },
  });

  const onSubmit = (values: RegisterFormValues) => {
    const { password_confirm, ...payload } = values;
    registerMutation.mutate(payload);
  };

  const serverError = registerMutation.isError
    ? extractErrorMessage(
        registerMutation.error,
        "Ошибка регистрации. Попробуйте ещё раз."
      )
    : null;

  const isPending = registerMutation.isPending;

  const inputClass = (hasError?: boolean) =>
    cn(
      "w-full border rounded-lg px-3 py-2 text-sm outline-none transition-colors",
      "focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
      "disabled:bg-gray-50 disabled:text-gray-500",
      hasError ? "border-red-400 bg-red-50" : "border-gray-300 bg-white"
    );

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="text-2xl font-bold text-blue-600">
            ICanRun
          </Link>
          <h1 className="text-xl font-semibold text-gray-900 mt-4">
            Создать аккаунт
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            30 дней бесплатного доступа ко всем функциям
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {/* Name */}
          <Field label="Имя" error={errors.name?.message}>
            <input
              type="text"
              autoComplete="name"
              placeholder="Иван Иванов"
              disabled={isPending}
              {...register("name")}
              className={inputClass(!!errors.name)}
            />
          </Field>

          {/* Email */}
          <Field label="Email" error={errors.email?.message}>
            <input
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              disabled={isPending}
              {...register("email")}
              className={inputClass(!!errors.email)}
            />
          </Field>

          {/* Password */}
          <Field
            label="Пароль"
            error={errors.password?.message}
            hint="Минимум 8 символов"
          >
            <input
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              disabled={isPending}
              {...register("password")}
              className={inputClass(!!errors.password)}
            />
          </Field>

          {/* Password confirm */}
          <Field
            label="Повторите пароль"
            error={errors.password_confirm?.message}
          >
            <input
              type="password"
              autoComplete="new-password"
              placeholder="••••••••"
              disabled={isPending}
              {...register("password_confirm")}
              className={inputClass(!!errors.password_confirm)}
            />
          </Field>

          {/* Optional profile section toggle */}
          <button
            type="button"
            onClick={() => setShowProfile((v) => !v)}
            className="text-sm text-blue-600 hover:text-blue-700 hover:underline"
          >
            {showProfile
              ? "Скрыть профиль спортсмена"
              : "+ Заполнить профиль спортсмена (необязательно)"}
          </button>

          {/* Optional profile fields */}
          {showProfile && (
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4 space-y-4">
              <p className="text-xs text-gray-500 mb-1">
                Данные профиля используются при составлении планов тренировок.
              </p>

              {/* Birth year */}
              <Field
                label="Год рождения"
                error={errors.birth_year?.message}
                hint="Например: 1990"
              >
                <input
                  type="number"
                  min={1900}
                  max={2020}
                  placeholder="1990"
                  disabled={isPending}
                  {...register("birth_year")}
                  className={inputClass(!!errors.birth_year)}
                />
              </Field>

              {/* Gender */}
              <Field label="Пол" error={errors.gender?.message}>
                <select
                  disabled={isPending}
                  {...register("gender")}
                  className={inputClass(!!errors.gender)}
                >
                  <option value="">Не указан</option>
                  <option value="male">Мужской</option>
                  <option value="female">Женский</option>
                  <option value="other">Другой</option>
                </select>
              </Field>

              {/* Weight and height in a 2-column row */}
              <div className="grid grid-cols-2 gap-3">
                <Field
                  label="Вес (кг)"
                  error={errors.weight_kg?.message}
                >
                  <input
                    type="number"
                    min={20}
                    max={300}
                    step={0.1}
                    placeholder="70"
                    disabled={isPending}
                    {...register("weight_kg")}
                    className={inputClass(!!errors.weight_kg)}
                  />
                </Field>
                <Field
                  label="Рост (см)"
                  error={errors.height_cm?.message}
                >
                  <input
                    type="number"
                    min={100}
                    max={250}
                    step={0.1}
                    placeholder="175"
                    disabled={isPending}
                    {...register("height_cm")}
                    className={inputClass(!!errors.height_cm)}
                  />
                </Field>
              </div>
            </div>
          )}

          {/* Server error */}
          {serverError && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {serverError}
            </div>
          )}

          {/* Submit */}
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
            {isPending ? "Создаём аккаунт..." : "Зарегистрироваться"}
          </button>
        </form>

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-gray-600">
          Уже есть аккаунт?{" "}
          <Link
            href="/login"
            className="text-blue-600 hover:text-blue-700 font-medium hover:underline"
          >
            Войти
          </Link>
        </p>
      </div>
    </div>
  );
}
