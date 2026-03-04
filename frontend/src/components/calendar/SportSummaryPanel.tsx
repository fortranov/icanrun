/**
 * SportSummaryPanel — right sidebar showing monthly training totals.
 *
 * Displays total hours + breakdown by sport type for the displayed month.
 * Data is derived from the workouts already fetched for the calendar
 * (no extra API call required).
 */
"use client";

import { useMemo } from "react";
import { cn, formatDuration, getSportLabel, getMonthName } from "@/lib/utils";
import type { SportType, Workout } from "@/types";

const SPORT_ORDER: SportType[] = [
  "running", "swimming", "cycling", "strength", "triathlon",
];

const SPORT_COLORS: Record<SportType, string> = {
  running:   "bg-red-500",
  swimming:  "bg-blue-500",
  cycling:   "bg-amber-500",
  strength:  "bg-violet-500",
  triathlon: "bg-emerald-500",
};

const SPORT_BG_LIGHT: Record<SportType, string> = {
  running:   "bg-red-50 text-red-700",
  swimming:  "bg-blue-50 text-blue-700",
  cycling:   "bg-amber-50 text-amber-700",
  strength:  "bg-violet-50 text-violet-700",
  triathlon: "bg-emerald-50 text-emerald-700",
};

interface SportStat {
  sport: SportType;
  totalMinutes: number;
  completedMinutes: number;
  count: number;
  completedCount: number;
}

interface SportSummaryPanelProps {
  workouts: Workout[];
  year: number;
  month: number;
}

export function SportSummaryPanel({
  workouts,
  year,
  month,
}: SportSummaryPanelProps) {
  const stats = useMemo(() => {
    const bySport: Partial<Record<SportType, SportStat>> = {};

    for (const w of workouts) {
      const sport = w.sport_type as SportType;
      if (!bySport[sport]) {
        bySport[sport] = {
          sport,
          totalMinutes: 0,
          completedMinutes: 0,
          count: 0,
          completedCount: 0,
        };
      }
      bySport[sport]!.totalMinutes += w.duration_minutes;
      bySport[sport]!.count += 1;
      if (w.is_completed) {
        bySport[sport]!.completedMinutes += w.duration_minutes;
        bySport[sport]!.completedCount += 1;
      }
    }

    const totalMinutes = workouts.reduce((s, w) => s + w.duration_minutes, 0);
    const completedMinutes = workouts
      .filter((w) => w.is_completed)
      .reduce((s, w) => s + w.duration_minutes, 0);
    const totalCount = workouts.length;
    const completedCount = workouts.filter((w) => w.is_completed).length;

    return {
      bySport,
      totalMinutes,
      completedMinutes,
      totalCount,
      completedCount,
    };
  }, [workouts]);

  const sportRows = SPORT_ORDER.filter(
    (s) => (stats.bySport[s]?.count ?? 0) > 0
  ).map((s) => stats.bySport[s] as SportStat);

  const completionRate =
    stats.totalCount > 0
      ? Math.round((stats.completedCount / stats.totalCount) * 100)
      : 0;

  return (
    <div className="w-48 flex-shrink-0 space-y-4">
      {/* Month header */}
      <div className="text-sm font-semibold text-gray-700">
        {getMonthName(month)} {year}
      </div>

      {/* Total summary card */}
      <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-2">
        <div>
          <p className="text-xs text-gray-500">Всего</p>
          <p className="text-xl font-bold text-gray-900">
            {formatDuration(stats.totalMinutes)}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Выполнено</p>
          <p className="text-sm font-medium text-green-600">
            {formatDuration(stats.completedMinutes)}
            {stats.totalMinutes > 0 && (
              <span className="text-gray-400 font-normal ml-1 text-xs">
                ({completionRate}%)
              </span>
            )}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Тренировок</p>
          <p className="text-sm font-medium text-gray-800">
            {stats.completedCount} / {stats.totalCount}
          </p>
        </div>
      </div>

      {/* Per-sport breakdown */}
      {sportRows.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            По видам
          </p>
          {sportRows.map((stat) => (
            <div
              key={stat.sport}
              className={cn(
                "rounded-lg px-3 py-2",
                SPORT_BG_LIGHT[stat.sport]
              )}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full flex-shrink-0",
                    SPORT_COLORS[stat.sport]
                  )}
                />
                <span className="text-xs font-medium truncate">
                  {getSportLabel(stat.sport)}
                </span>
              </div>
              <p className="text-base font-bold">
                {formatDuration(stat.totalMinutes)}
              </p>
              <p className="text-xs opacity-70">
                {stat.count} тр.
              </p>
            </div>
          ))}
        </div>
      )}

      {workouts.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-4">
          Нет тренировок
        </p>
      )}
    </div>
  );
}
