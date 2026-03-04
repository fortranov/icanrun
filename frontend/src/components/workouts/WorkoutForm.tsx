/**
 * WorkoutForm — create or edit a workout.
 *
 * Used inside modals for both creating new workouts and editing existing ones.
 * Validates with Zod + react-hook-form.
 * On submit calls onSave(data) — the parent decides whether to create or update.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { cn, formatDuration, getSportLabel, getWorkoutTypeLabel, todayString, WEEKDAY_NAMES_SHORT } from "@/lib/utils";
import type { SportType, Workout, WorkoutCreate, WorkoutType } from "@/types";

// ---------------------------------------------------------------------------
// Validation schema
// ---------------------------------------------------------------------------

const workoutSchema = z.object({
  sport_type: z.enum([
    "running", "swimming", "cycling", "strength", "triathlon"
  ] as const),
  workout_type: z.enum([
    "recovery", "long", "interval", "threshold"
  ] as const).nullable().optional(),
  date: z.string().min(1, "Выберите дату"),
  duration_minutes: z
    .number({ invalid_type_error: "Введите число" })
    .int("Целое число минут")
    .min(1, "Минимум 1 минута")
    .max(1440, "Максимум 24 часа"),
  comment: z.string().max(2000).nullable().optional(),
});

type WorkoutFormValues = z.infer<typeof workoutSchema>;

// ---------------------------------------------------------------------------
// Sport type options
// ---------------------------------------------------------------------------

const SPORT_OPTIONS: { value: SportType; label: string; color: string }[] = [
  { value: "running",   label: "Бег",        color: "bg-red-500" },
  { value: "swimming",  label: "Плавание",   color: "bg-blue-500" },
  { value: "cycling",   label: "Велосипед",  color: "bg-amber-500" },
  { value: "strength",  label: "Силовые",    color: "bg-violet-500" },
  { value: "triathlon", label: "Триатлон",   color: "bg-emerald-500" },
];

const WORKOUT_TYPE_OPTIONS: { value: WorkoutType; label: string }[] = [
  { value: "recovery",  label: "Восстановление" },
  { value: "long",      label: "Длинная" },
  { value: "interval",  label: "Интервалы" },
  { value: "threshold", label: "Пороговая" },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface WorkoutFormProps {
  /** If provided, pre-fills the form for editing. */
  initial?: Partial<Workout>;
  /** Default date to pre-select (e.g. clicked calendar cell). */
  defaultDate?: string;
  /** Called when the form is submitted successfully. */
  onSave: (data: WorkoutCreate) => void | Promise<void>;
  /** Called when the user cancels. */
  onCancel: () => void;
  /** Whether the parent mutation is in-flight. */
  isLoading?: boolean;
  /** Server error message to display. */
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function WorkoutForm({
  initial,
  defaultDate,
  onSave,
  onCancel,
  isLoading = false,
  error,
}: WorkoutFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<WorkoutFormValues>({
    resolver: zodResolver(workoutSchema),
    defaultValues: {
      sport_type: (initial?.sport_type as SportType) ?? "running",
      workout_type: initial?.workout_type ?? null,
      date: initial?.date ?? defaultDate ?? todayString(),
      duration_minutes: initial?.duration_minutes ?? 60,
      comment: initial?.comment ?? null,
    },
  });

  const selectedSport = watch("sport_type");

  const onSubmit = async (values: WorkoutFormValues) => {
    await onSave({
      sport_type: values.sport_type,
      workout_type: values.workout_type ?? undefined,
      date: values.date,
      duration_minutes: values.duration_minutes,
      comment: values.comment ?? undefined,
    });
  };

  const inputClass = (hasError?: boolean) =>
    cn(
      "w-full border rounded-lg px-3 py-2 text-sm outline-none transition-colors",
      "focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
      "disabled:bg-gray-50 disabled:text-gray-500",
      hasError ? "border-red-400 bg-red-50" : "border-gray-300 bg-white"
    );

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {/* Sport type selector — pill buttons */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Вид спорта
        </label>
        <div className="flex flex-wrap gap-2">
          {SPORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setValue("sport_type", opt.value)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all",
                selectedSport === opt.value
                  ? `${opt.color} text-white border-transparent`
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              )}
            >
              <span
                className={cn(
                  "w-2 h-2 rounded-full",
                  selectedSport === opt.value ? "bg-white/60" : opt.color
                )}
              />
              {opt.label}
            </button>
          ))}
        </div>
        {errors.sport_type && (
          <p className="mt-1 text-xs text-red-600">{errors.sport_type.message}</p>
        )}
      </div>

      {/* Workout type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Тип тренировки
          <span className="text-gray-400 font-normal ml-1">(необязательно)</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {/* "No type" option */}
          <button
            type="button"
            onClick={() => setValue("workout_type", null)}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm border transition-all",
              watch("workout_type") == null
                ? "bg-gray-700 text-white border-transparent"
                : "bg-white text-gray-500 border-gray-200 hover:border-gray-300"
            )}
          >
            Не указан
          </button>
          {WORKOUT_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setValue("workout_type", opt.value)}
              className={cn(
                "px-3 py-1.5 rounded-full text-sm border transition-all",
                watch("workout_type") === opt.value
                  ? "bg-gray-700 text-white border-transparent"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Date + Duration row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Дата
          </label>
          <input
            type="date"
            disabled={isLoading}
            {...register("date")}
            className={inputClass(!!errors.date)}
          />
          {errors.date && (
            <p className="mt-1 text-xs text-red-600">{errors.date.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Длительность (мин)
          </label>
          <input
            type="number"
            min={1}
            max={1440}
            step={5}
            disabled={isLoading}
            {...register("duration_minutes", { valueAsNumber: true })}
            className={inputClass(!!errors.duration_minutes)}
          />
          {errors.duration_minutes ? (
            <p className="mt-1 text-xs text-red-600">
              {errors.duration_minutes.message}
            </p>
          ) : (
            <p className="mt-1 text-xs text-gray-400">
              {formatDuration(watch("duration_minutes") || 0)}
            </p>
          )}
        </div>
      </div>

      {/* Comment */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Комментарий
          <span className="text-gray-400 font-normal ml-1">(необязательно)</span>
        </label>
        <textarea
          rows={3}
          placeholder="Заметки о тренировке..."
          disabled={isLoading}
          {...register("comment")}
          className={cn(inputClass(!!errors.comment), "resize-none")}
        />
        {errors.comment && (
          <p className="mt-1 text-xs text-red-600">{errors.comment.message}</p>
        )}
      </div>

      {/* Server error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={isLoading}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
        >
          Отмена
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className={cn(
            "px-5 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white",
            "hover:bg-blue-700 transition-colors",
            "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
            isLoading && "opacity-60 cursor-not-allowed"
          )}
        >
          {isLoading ? "Сохранение..." : initial ? "Сохранить" : "Добавить"}
        </button>
      </div>
    </form>
  );
}
