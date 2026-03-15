/**
 * Results (analytics) page.
 *
 * Features:
 *  - Sport selector tabs: All / Running / Swimming / Cycling / Strength / Triathlon
 *  - Month navigation (prev/next)
 *  - Monthly bar chart (completed + planned-not-completed stacked bars)
 *  - Summary stats cards: total hours, total workouts, completion rate
 *
 * Data: fetched via /analytics/daily endpoint which returns per-day stats.
 */
"use client";

import { useState } from "react";
import { useCalendarStore } from "@/stores/calendarStore";
import { useDailyStats } from "@/hooks/useAnalytics";
import { WorkoutBarChart } from "@/components/results/WorkoutBarChart";
import { SportStats } from "@/components/results/SportStats";
import { cn, getMonthName } from "@/lib/utils";
import type { SportType } from "@/types";

// ---------------------------------------------------------------------------
// Sport tab definitions
// ---------------------------------------------------------------------------

const SPORT_TABS: { value: string; label: string; color: string; chartColor: string; lightColor: string }[] = [
  { value: "all",       label: "Все",       color: "text-blue-600 border-blue-600",    chartColor: "#3b82f6", lightColor: "#bfdbfe" },
  { value: "running",   label: "Бег",        color: "text-red-600 border-red-600",     chartColor: "#ef4444", lightColor: "#fecaca" },
  { value: "swimming",  label: "Плавание",   color: "text-blue-600 border-blue-500",   chartColor: "#3b82f6", lightColor: "#bfdbfe" },
  { value: "cycling",   label: "Велосипед",  color: "text-amber-600 border-amber-600", chartColor: "#f59e0b", lightColor: "#fde68a" },
  { value: "strength",  label: "Силовые",    color: "text-violet-600 border-violet-600", chartColor: "#8b5cf6", lightColor: "#ddd6fe" },
  { value: "triathlon", label: "Триатлон",   color: "text-emerald-600 border-emerald-600", chartColor: "#10b981", lightColor: "#a7f3d0" },
];

export default function ResultsPage() {
  const { currentYear, currentMonth, prevMonth, nextMonth } = useCalendarStore();
  const [selectedSport, setSelectedSport] = useState<string>("all");

  const sport = selectedSport === "all" ? undefined : selectedSport;
  const { data, isLoading, isError } = useDailyStats(currentYear, currentMonth, sport);

  const activeTab = SPORT_TABS.find((t) => t.value === selectedSport) ?? SPORT_TABS[0];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Результаты</h1>

        {/* Month navigation */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={prevMonth}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
          >
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <span className="text-sm font-medium text-gray-700 min-w-[130px] text-center">
            {getMonthName(currentMonth)} {currentYear}
          </span>
          <button
            type="button"
            onClick={nextMonth}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
          >
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      {/* Sport selector tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-gray-200 pb-0">
        {SPORT_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setSelectedSport(tab.value)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors",
              selectedSport === tab.value
                ? tab.color
                : "text-gray-500 border-transparent hover:text-gray-700 hover:border-gray-300"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Summary stats cards */}
      {data?.summary ? (
        <SportStats stats={data.summary} selectedSport={selectedSport} />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 px-5 py-4 h-20 animate-pulse">
              <div className="h-3 bg-gray-100 rounded w-1/2 mb-2" />
              <div className="h-7 bg-gray-100 rounded w-3/4" />
            </div>
          ))}
        </div>
      )}

      {/* Bar chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">
            Объём тренировок по неделям
          </h2>
          {/* Legend */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-3 rounded"
                style={{ backgroundColor: activeTab.chartColor }}
              />
              Выполнено
            </span>
            <span className="flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-3 rounded"
                style={{ backgroundColor: activeTab.lightColor }}
              />
              Запланировано
            </span>
          </div>
        </div>

        {isLoading && (
          <div className="h-[280px] flex items-center justify-center">
            <div className="text-sm text-gray-400 animate-pulse">Загрузка данных...</div>
          </div>
        )}

        {isError && (
          <div className="h-[280px] flex items-center justify-center">
            <div className="text-sm text-red-500">Не удалось загрузить данные</div>
          </div>
        )}

        {data && !isLoading && (
          <WorkoutBarChart
            days={data.days}
            completedColor={activeTab.chartColor}
            plannedColor={activeTab.lightColor}
          />
        )}

        {data && data.days.every((d) => d.total_minutes === 0) && (
          <div className="text-center text-sm text-gray-400 mt-4">
            Нет тренировок за этот месяц
          </div>
        )}
      </div>

      {/* Per-sport breakdown table */}
      {data?.summary && Object.keys(data.summary.by_sport).length > 0 && selectedSport === "all" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Разбивка по видам спорта</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                <th className="text-left px-6 py-3 font-medium">Вид спорта</th>
                <th className="text-right px-6 py-3 font-medium">Тренировок</th>
                <th className="text-right px-6 py-3 font-medium">Объём</th>
                <th className="text-right px-6 py-3 font-medium">Выполнено</th>
                <th className="text-right px-6 py-3 font-medium">%</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.summary.by_sport).map(([sport, breakdown]) => {
                const tab = SPORT_TABS.find((t) => t.value === sport);
                const pct =
                  breakdown.total_workouts > 0
                    ? Math.round(
                        (breakdown.completed_workouts / breakdown.total_workouts) * 100
                      )
                    : 0;
                return (
                  <tr key={sport} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: tab?.chartColor ?? "#94a3b8" }}
                        />
                        <span className="font-medium text-gray-800">
                          {tab?.label ?? sport}
                        </span>
                      </div>
                    </td>
                    <td className="text-right px-6 py-3 text-gray-600">
                      {breakdown.total_workouts}
                    </td>
                    <td className="text-right px-6 py-3 text-gray-800 font-medium">
                      {Math.round(breakdown.total_minutes / 60 * 10) / 10}h
                    </td>
                    <td className="text-right px-6 py-3 text-green-600">
                      {Math.round(breakdown.completed_minutes / 60 * 10) / 10}h
                    </td>
                    <td className="text-right px-6 py-3">
                      <span
                        className={cn(
                          "font-semibold",
                          pct >= 80
                            ? "text-green-600"
                            : pct >= 50
                            ? "text-orange-500"
                            : "text-red-500"
                        )}
                      >
                        {pct}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
