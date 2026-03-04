/**
 * SportStats — summary stats cards for the Results page.
 *
 * Shows: Total hours, Total workouts, Completion rate.
 * Accepts a MonthlyStats object from the analytics endpoint.
 */
"use client";

import { cn, formatDuration, getSportLabel } from "@/lib/utils";
import type { MonthlyStats, SportType } from "@/types";

interface SportStatsProps {
  stats: MonthlyStats;
  selectedSport: string;
}

const SPORT_COLORS: Record<string, string> = {
  all:       "text-blue-600 bg-blue-50",
  running:   "text-red-600 bg-red-50",
  swimming:  "text-blue-600 bg-blue-50",
  cycling:   "text-amber-600 bg-amber-50",
  strength:  "text-violet-600 bg-violet-50",
  triathlon: "text-emerald-600 bg-emerald-50",
};

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  colorClass?: string;
}

function StatCard({ label, value, sub, colorClass = "text-gray-900" }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-5 py-4">
      <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
      <p className={cn("text-2xl font-bold", colorClass)}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function SportStats({ stats, selectedSport }: SportStatsProps) {
  const colorClass = SPORT_COLORS[selectedSport] ?? "text-gray-900 bg-gray-50";
  const primaryColor = colorClass.split(" ")[0]; // just the text color

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <StatCard
        label="Всего часов"
        value={formatDuration(stats.total_minutes)}
        sub={`Выполнено: ${formatDuration(stats.completed_minutes)}`}
        colorClass={primaryColor}
      />
      <StatCard
        label="Тренировок"
        value={String(stats.total_workouts)}
        sub={`Выполнено: ${stats.completed_workouts}`}
        colorClass="text-gray-900"
      />
      <StatCard
        label="Выполнение"
        value={`${stats.completion_rate}%`}
        sub={`${stats.completed_workouts} из ${stats.total_workouts}`}
        colorClass={
          stats.completion_rate >= 80
            ? "text-green-600"
            : stats.completion_rate >= 50
            ? "text-orange-500"
            : "text-red-500"
        }
      />
      <StatCard
        label="Запланировано"
        value={formatDuration(stats.total_minutes - stats.completed_minutes)}
        sub="Не выполнено"
        colorClass="text-gray-500"
      />
    </div>
  );
}
