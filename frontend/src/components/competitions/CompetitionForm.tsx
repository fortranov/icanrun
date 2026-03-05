/**
 * CompetitionForm — create or edit a competition entry.
 *
 * Handles sport/type pairing, conditional distance field (swimming/cycling),
 * importance toggle, date, name, and validates with Zod + react-hook-form.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { cn, todayString } from "@/lib/utils";
import type {
  Competition,
  CompetitionCreate,
  CompetitionImportance,
  CompetitionType,
  SportType,
} from "@/types";

// ---------------------------------------------------------------------------
// Competition type options grouped by sport
// ---------------------------------------------------------------------------

const COMPETITION_TYPES: Record<
  string,
  { value: CompetitionType; label: string; sport: SportType }[]
> = {
  running: [
    { value: "run_5k",         label: "5 км",            sport: "running" },
    { value: "run_10k",        label: "10 км",           sport: "running" },
    { value: "half_marathon",  label: "Полумарафон",      sport: "running" },
    { value: "marathon",       label: "Марафон",          sport: "running" },
  ],
  swimming: [
    { value: "swimming",       label: "Плавание (дистанция)", sport: "swimming" },
  ],
  cycling: [
    { value: "cycling",        label: "Велогонка (дистанция)", sport: "cycling" },
  ],
  triathlon: [
    { value: "super_sprint",   label: "Суперспринт",    sport: "triathlon" },
    { value: "sprint",         label: "Спринт",          sport: "triathlon" },
    { value: "olympic",        label: "Олимпийская",     sport: "triathlon" },
    { value: "half_iron",      label: "Полужелезная",    sport: "triathlon" },
    { value: "iron",           label: "Железная",        sport: "triathlon" },
  ],
};

const SPORT_OPTIONS: { value: SportType; label: string }[] = [
  { value: "running",   label: "Бег" },
  { value: "swimming",  label: "Плавание" },
  { value: "cycling",   label: "Велосипед" },
  { value: "triathlon", label: "Триатлон" },
];

// ---------------------------------------------------------------------------
// Validation schema
// ---------------------------------------------------------------------------

// Input schema — all fields as strings (as the user types in the form)
const competitionSchema = z.object({
  name: z.string().min(1, "Введите название").max(255),
  sport_type: z.enum([
    "running", "swimming", "cycling", "strength", "triathlon"
  ] as const),
  competition_type: z.string().min(1, "Выберите тип"),
  importance: z.enum(["key", "secondary"] as const),
  date: z.string().min(1, "Выберите дату"),
  distance: z.string().optional(),
});

type CompetitionFormValues = z.infer<typeof competitionSchema>;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CompetitionFormProps {
  initial?: Partial<Competition>;
  defaultDate?: string;
  onSave: (data: CompetitionCreate) => void | Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CompetitionForm({
  initial,
  defaultDate,
  onSave,
  onCancel,
  isLoading = false,
  error,
}: CompetitionFormProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<CompetitionFormValues>({
    resolver: zodResolver(competitionSchema),
    defaultValues: {
      name: initial?.name ?? "",
      sport_type: (initial?.sport_type as SportType) ?? "running",
      competition_type: initial?.competition_type ?? "marathon",
      importance: (initial?.importance as CompetitionImportance) ?? "key",
      date: initial?.date ?? defaultDate ?? todayString(),
      distance: initial?.distance ? String(initial.distance) : "",
    },
  });

  const selectedSport = watch("sport_type");
  const selectedType = watch("competition_type");
  const needsDistance =
    selectedType === "swimming" || selectedType === "cycling";

  // Reset competition_type when sport changes to avoid invalid combos
  useEffect(() => {
    const options = COMPETITION_TYPES[selectedSport] ?? [];
    const currentValid = options.some((o) => o.value === selectedType);
    if (!currentValid && options.length > 0) {
      setValue("competition_type", options[0].value);
    }
  }, [selectedSport, selectedType, setValue]);

  const onSubmit = async (values: CompetitionFormValues) => {
    // Validate distance required for swimming/cycling
    const needsDist =
      values.competition_type === "swimming" ||
      values.competition_type === "cycling";
    if (needsDist && (!values.distance || values.distance === "")) {
      return; // HTML5 required attr will show the error
    }
    const distanceNum =
      values.distance && values.distance !== ""
        ? parseFloat(values.distance)
        : undefined;
    await onSave({
      name: values.name,
      sport_type: values.sport_type,
      competition_type: values.competition_type as CompetitionType,
      importance: values.importance,
      date: values.date,
      distance: distanceNum,
    });
  };

  const inputClass = (hasError?: boolean) =>
    cn(
      "w-full border rounded-lg px-3 py-2 text-sm outline-none transition-colors",
      "focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
      "disabled:bg-gray-50 disabled:text-gray-500",
      hasError ? "border-red-400 bg-red-50" : "border-gray-300 bg-white"
    );

  const competitionOptions =
    COMPETITION_TYPES[selectedSport] ?? COMPETITION_TYPES.running;

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Название соревнования
        </label>
        <input
          type="text"
          placeholder="City Marathon 2026"
          disabled={isLoading}
          {...register("name")}
          className={inputClass(!!errors.name)}
        />
        {errors.name && (
          <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>
        )}
      </div>

      {/* Sport type */}
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
                "px-3 py-1.5 rounded-full text-sm border transition-all",
                selectedSport === opt.value
                  ? "bg-blue-600 text-white border-transparent"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Competition type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Тип / дистанция
        </label>
        <select
          disabled={isLoading}
          {...register("competition_type")}
          className={inputClass(!!errors.competition_type)}
        >
          {competitionOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {errors.competition_type && (
          <p className="mt-1 text-xs text-red-600">
            {errors.competition_type.message}
          </p>
        )}
      </div>

      {/* Distance (conditional) */}
      {needsDistance && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Дистанция{" "}
            <span className="text-gray-500 font-normal">
              {selectedType === "swimming" ? "(метры)" : "(км)"}
            </span>
          </label>
          <input
            type="number"
            min={1}
            step={selectedType === "swimming" ? 100 : 1}
            placeholder={selectedType === "swimming" ? "1500" : "100"}
            disabled={isLoading}
            {...register("distance")}
            className={inputClass(!!errors.distance)}
          />
          {errors.distance && (
            <p className="mt-1 text-xs text-red-600">
              {errors.distance.message}
            </p>
          )}
        </div>
      )}

      {/* Date + Importance row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Дата старта
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
            Приоритет
          </label>
          <div className="flex gap-2">
            {(["key", "secondary"] as const).map((imp) => (
              <button
                key={imp}
                type="button"
                onClick={() => setValue("importance", imp)}
                className={cn(
                  "flex-1 py-2 rounded-lg text-sm border transition-all",
                  watch("importance") === imp
                    ? imp === "key"
                      ? "bg-amber-500 text-white border-transparent"
                      : "bg-gray-500 text-white border-transparent"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                )}
              >
                {imp === "key" ? "A-старт" : "B-старт"}
              </button>
            ))}
          </div>
        </div>
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
          {isLoading ? "Сохранение..." : initial ? "Сохранить" : "Добавить старт"}
        </button>
      </div>
    </form>
  );
}
