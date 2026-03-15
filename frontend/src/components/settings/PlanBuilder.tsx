/**
 * PlanBuilder — training plan generation UI.
 *
 * Available only for Trial and Pro subscribers.
 * Allows users to:
 *  1. Select sport
 *  2. Choose a key competition (from their competitions list) or maintenance mode
 *  3. Set preferred training days (weekday checkboxes)
 *  4. Set max hours per week
 *  5. Configure athlete level, sessions per week
 *  6. Generate or delete the plan
 *
 * On generate: calls POST /plans/generate
 * On delete: calls DELETE /plans/{id}
 */
"use client";

import { useState } from "react";
import { useSubscription } from "@/hooks/useSubscription";
import { usePlans, useGeneratePlan, useDeletePlan } from "@/hooks/usePlans";
import { useCompetitions } from "@/hooks/useCompetitions";
import { cn, getSportLabel, WEEKDAY_NAMES_FULL, formatDuration } from "@/lib/utils";
import type {
  AthleteLevel,
  PlanGenerateRequest,
  SportType,
  TriathlonDistance,
} from "@/types";

const SPORTS: { value: SportType; label: string; color: string }[] = [
  { value: "running",   label: "Бег",        color: "bg-red-500" },
  { value: "swimming",  label: "Плавание",   color: "bg-blue-500" },
  { value: "cycling",   label: "Велосипед",  color: "bg-amber-500" },
  { value: "strength",  label: "Силовые",    color: "bg-violet-500" },
  { value: "triathlon", label: "Триатлон",   color: "bg-emerald-500" },
];

const ATHLETE_LEVELS: { value: AthleteLevel; label: string }[] = [
  { value: "beginner",     label: "Начинающий" },
  { value: "intermediate", label: "Средний" },
  { value: "advanced",     label: "Продвинутый" },
];

const TRIATHLON_DISTANCES: { value: TriathlonDistance; label: string }[] = [
  { value: "sprint",  label: "Спринт" },
  { value: "olympic", label: "Олимпийская" },
  { value: "half",    label: "Half Ironman" },
  { value: "full",    label: "Ironman" },
];

// 0 = Monday, 6 = Sunday (backend convention)
const WEEKDAYS = WEEKDAY_NAMES_FULL;

export function PlanBuilder() {
  const { canUsePlans } = useSubscription();

  // ---- Form state ----
  const [sport, setSport] = useState<SportType>("running");
  const [competitionId, setCompetitionId] = useState<number | null>(null);
  const [preferredDays, setPreferredDays] = useState<number[]>([1, 3, 5]); // Tue, Thu, Sat
  const [maxHours, setMaxHours] = useState<number>(8);
  const [athleteLevel, setAthleteLevel] = useState<AthleteLevel>("intermediate");
  const [sessionsPerWeek, setSessionsPerWeek] = useState<number>(4);
  const [distanceType, setDistanceType] = useState<TriathlonDistance>("olympic");
  const [longRunPace, setLongRunPace] = useState<string>("");
  const [swimPaceMin, setSwimPaceMin] = useState<string>("");
  const [swimPaceSec, setSwimPaceSec] = useState<string>("");
  const [longRideSpeed, setLongRideSpeed] = useState<string>("");
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // ---- Data ----
  const { data: plans, isLoading: plansLoading } = usePlans();
  const { data: competitionsData } = useCompetitions({ sport_type: sport });
  const { mutateAsync: generatePlan, isPending: isGenerating } = useGeneratePlan();
  const { mutateAsync: deletePlan, isPending: isDeleting } = useDeletePlan();

  const activePlan = plans?.find((p) => p.sport_type === sport && p.is_active);
  const competitions = competitionsData?.items ?? [];
  const futureCompetitions = competitions.filter(
    (c) => new Date(c.date) > new Date()
  );

  const toggleDay = (day: number) => {
    setPreferredDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort()
    );
  };

  const handleGenerate = async () => {
    if (preferredDays.length === 0) {
      setServerError("Выберите хотя бы один день тренировки");
      return;
    }
    setServerError(null);
    setSuccessMsg(null);
    try {
      const req: PlanGenerateRequest = {
        sport_type: sport,
        competition_id: competitionId ?? undefined,
        preferred_days: preferredDays,
        max_hours_per_week: maxHours,
        settings: {
          athlete_level: athleteLevel,
          sessions_per_week: sessionsPerWeek,
          distance_type: sport === "triathlon" ? distanceType : null,
          long_run_pace: sport === "running" && longRunPace !== "" ? Number(longRunPace) : null,
          swim_pace_min: sport === "swimming" && swimPaceMin !== "" ? Number(swimPaceMin) : null,
          swim_pace_sec: sport === "swimming" && swimPaceSec !== "" ? Number(swimPaceSec) : null,
          long_ride_speed: sport === "cycling" && longRideSpeed !== "" ? Number(longRideSpeed) : null,
        },
      };
      const result = await generatePlan(req);
      setSuccessMsg(
        `План создан: ${result.preview_weeks} недель, ${result.total_workouts} тренировок (${result.preview_total_hours}ч)`
      );
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Не удалось создать план";
      setServerError(msg);
    }
  };

  const handleDelete = async (planId: number) => {
    try {
      await deletePlan(planId);
      setDeleteConfirmId(null);
      setSuccessMsg("План удалён. Прошлые тренировки сохранены.");
    } catch {
      setServerError("Не удалось удалить план");
    }
  };

  if (!canUsePlans) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Планы тренировок
        </h2>
        <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          Создание планов тренировок доступно в тарифах Trial и Pro.
          Обновите подписку для доступа к этой функции.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-5 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">
          Планы тренировок
        </h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Персонализированные планы по методологии Джо Фрила
        </p>
      </div>

      <div className="px-6 py-5 space-y-6">
        {/* Active plan info */}
        {activePlan && (
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-blue-800">
                  Активный план: {getSportLabel(activePlan.sport_type)}
                </p>
                <p className="text-xs text-blue-600 mt-0.5">
                  {activePlan.weeks_count} нед. •{" "}
                  {activePlan.max_hours_per_week}ч/нед. •{" "}
                  {activePlan.target_date
                    ? `до ${new Date(activePlan.target_date).toLocaleDateString("ru-RU")}`
                    : "Поддерживающий план"}
                </p>
              </div>
              {deleteConfirmId === activePlan.id ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleDelete(activePlan.id)}
                    disabled={isDeleting}
                    className="px-3 py-1 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    {isDeleting ? "..." : "Удалить"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteConfirmId(null)}
                    className="px-3 py-1 border border-blue-200 text-blue-600 text-xs rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    Отмена
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setDeleteConfirmId(activePlan.id)}
                  className="text-xs text-red-500 hover:text-red-700 transition-colors"
                >
                  Удалить план
                </button>
              )}
            </div>
          </div>
        )}

        {/* Sport selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Вид спорта
          </label>
          <div className="flex flex-wrap gap-2">
            {SPORTS.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => {
                  setSport(s.value);
                  setCompetitionId(null);
                }}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border transition-all",
                  sport === s.value
                    ? `${s.color} text-white border-transparent`
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                )}
              >
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    sport === s.value ? "bg-white/60" : s.color
                  )}
                />
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Competition selector / maintenance */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Целевое соревнование
          </label>
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="competition"
                checked={competitionId === null}
                onChange={() => setCompetitionId(null)}
                className="text-blue-600"
              />
              <span className="text-sm text-gray-700">
                Поддерживающий план (6 месяцев без соревнования)
              </span>
            </label>
            {futureCompetitions.map((c) => (
              <label key={c.id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="competition"
                  checked={competitionId === c.id}
                  onChange={() => setCompetitionId(c.id)}
                  className="text-blue-600"
                />
                <span className="text-sm text-gray-700">
                  {c.name}{" "}
                  <span className="text-gray-400">
                    ({new Date(c.date).toLocaleDateString("ru-RU")})
                  </span>
                  {c.importance === "key" && (
                    <span className="ml-1 text-amber-500 text-xs">★ Ключевое</span>
                  )}
                </span>
              </label>
            ))}
            {futureCompetitions.length === 0 && (
              <p className="text-xs text-gray-400 pl-5">
                Нет предстоящих соревнований по{" "}
                {getSportLabel(sport).toLowerCase()}.
                Добавьте соревнование на странице Главная.
              </p>
            )}
          </div>
        </div>

        {/* Athlete level */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Уровень подготовки
          </label>
          <div className="flex gap-2">
            {ATHLETE_LEVELS.map((l) => (
              <button
                key={l.value}
                type="button"
                onClick={() => setAthleteLevel(l.value)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm border transition-all",
                  athleteLevel === l.value
                    ? "bg-gray-800 text-white border-transparent"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                )}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Triathlon distance type */}
        {sport === "triathlon" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Дистанция триатлона
            </label>
            <div className="flex flex-wrap gap-2">
              {TRIATHLON_DISTANCES.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDistanceType(d.value)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-sm border transition-all",
                    distanceType === d.value
                      ? "bg-emerald-600 text-white border-transparent"
                      : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                  )}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Running: long run pace */}
        {sport === "running" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Темп длительной тренировки (сейчас)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={3}
                max={20}
                step={0.1}
                placeholder="5.5"
                value={longRunPace}
                onChange={(e) => setLongRunPace(e.target.value)}
                className="w-28 border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="text-sm text-gray-500">мин/км</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Например, 5.5 = 5:30/км. Используется для калибровки зон интенсивности.
            </p>
          </div>
        )}

        {/* Swimming: pace per 100m */}
        {sport === "swimming" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Темп на 100м (сейчас)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={0}
                max={10}
                step={1}
                placeholder="2"
                value={swimPaceMin}
                onChange={(e) => setSwimPaceMin(e.target.value)}
                className="w-20 border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="text-sm text-gray-500">мин</span>
              <input
                type="number"
                min={0}
                max={59}
                step={1}
                placeholder="00"
                value={swimPaceSec}
                onChange={(e) => setSwimPaceSec(e.target.value)}
                className="w-20 border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="text-sm text-gray-500">сек</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Темп длительного заплыва на 100м. Используется для калибровки зон интенсивности.
            </p>
          </div>
        )}

        {/* Cycling: long ride speed */}
        {sport === "cycling" && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Скорость длительной тренировки (сейчас)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={10}
                max={60}
                step={0.5}
                placeholder="28"
                value={longRideSpeed}
                onChange={(e) => setLongRideSpeed(e.target.value)}
                className="w-28 border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="text-sm text-gray-500">км/ч</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Средняя скорость на длинной поездке. Используется для калибровки зон интенсивности.
            </p>
          </div>
        )}

        {/* Preferred training days */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Дни тренировок
          </label>
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map((name, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => toggleDay(idx)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm border transition-all",
                  preferredDays.includes(idx)
                    ? "bg-blue-600 text-white border-transparent"
                    : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                )}
              >
                {name.slice(0, 2)}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Выбрано: {preferredDays.length} дней
          </p>
        </div>

        {/* Max hours + sessions per week */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Макс. часов в неделю
            </label>
            <input
              type="number"
              min={1}
              max={40}
              step={0.5}
              value={maxHours}
              onChange={(e) => setMaxHours(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Занятий в неделю
            </label>
            <input
              type="number"
              min={3}
              max={6}
              step={1}
              value={sessionsPerWeek}
              onChange={(e) => setSessionsPerWeek(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Errors / success */}
        {serverError && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {serverError}
          </div>
        )}
        {successMsg && (
          <div className="rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
            {successMsg}
          </div>
        )}

        {/* Generate button */}
        <button
          type="button"
          onClick={handleGenerate}
          disabled={isGenerating || preferredDays.length === 0}
          className={cn(
            "w-full py-2.5 rounded-lg text-sm font-semibold transition-colors",
            "bg-blue-600 text-white hover:bg-blue-700",
            "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
            (isGenerating || preferredDays.length === 0) && "opacity-60 cursor-not-allowed"
          )}
        >
          {isGenerating
            ? "Генерируем план..."
            : activePlan
            ? "Пересоздать план"
            : "Создать план тренировок"}
        </button>

        <p className="text-xs text-gray-400 text-center">
          При создании нового плана существующий для этого вида спорта будет заменён.
          Прошлые тренировки сохранятся.
        </p>
      </div>
    </div>
  );
}
