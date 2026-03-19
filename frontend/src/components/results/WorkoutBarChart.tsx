/**
 * WorkoutBarChart — weekly training volume bar chart.
 *
 * X-axis: weeks of the month (Mon–Sun spans)
 * Y-axis: hours
 * Each bar is split into two stacked segments:
 *   1. Completed workouts (solid sport color, bottom)
 *   2. Planned but not completed (lighter color, top)
 *
 * Daily data from the API is aggregated into weeks on the client.
 */
"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatDuration } from "@/lib/utils";
import type { DayStats } from "@/types";

// ---------------------------------------------------------------------------
// Weekly aggregation helpers
// ---------------------------------------------------------------------------

interface WeekBar {
  label: string;       // "24 фев – 2 мар"
  weekStart: string;   // ISO date of Monday
  completed: number;   // minutes
  planned: number;     // planned-not-completed minutes
}

const SHORT_MONTHS = [
  "янв", "фев", "мар", "апр", "май", "июн",
  "июл", "авг", "сен", "окт", "ноя", "дек",
];

function fmtDay(d: Date): string {
  return `${d.getDate()} ${SHORT_MONTHS[d.getMonth()]}`;
}

/** Return the Monday of the ISO week containing `d`. */
function getMonday(d: Date): Date {
  const day = d.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diff);
  return monday;
}

function aggregateToWeeks(days: DayStats[]): WeekBar[] {
  const map = new Map<string, WeekBar>();

  for (const day of days) {
    // Parse as local date to avoid UTC-offset day shift
    const [y, m, dd] = day.date.split("-").map(Number);
    const d = new Date(y, m - 1, dd);
    const monday = getMonday(d);
    const key = monday.toISOString().split("T")[0];

    if (!map.has(key)) {
      const sunday = new Date(monday);
      sunday.setDate(monday.getDate() + 6);
      map.set(key, {
        label: `${fmtDay(monday)} – ${fmtDay(sunday)}`,
        weekStart: key,
        completed: 0,
        planned: 0,
      });
    }

    const week = map.get(key)!;
    week.completed += day.completed_minutes;
    week.planned += day.planned_minutes;
  }

  return Array.from(map.values()).sort((a, b) =>
    a.weekStart.localeCompare(b.weekStart)
  );
}

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

interface TooltipPayloadEntry {
  name: string;
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const completed = payload.find((p) => p.name === "completed")?.value ?? 0;
  const planned = payload.find((p) => p.name === "planned")?.value ?? 0;
  const total = completed + planned;

  if (total === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm">
      <p className="font-semibold text-gray-900 mb-1">{label}</p>
      {completed > 0 && (
        <p className="text-green-600">Выполнено: {formatDuration(completed)}</p>
      )}
      {planned > 0 && (
        <p className="text-orange-400">Не выполнено: {formatDuration(planned)}</p>
      )}
      <p className="text-gray-600 mt-1 border-t border-gray-100 pt-1">
        Итого: {formatDuration(total)}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------

interface WorkoutBarChartProps {
  days: DayStats[];
  completedColor?: string;
  plannedColor?: string;
}

export function WorkoutBarChart({
  days,
  completedColor = "#3b82f6",
  plannedColor = "#bfdbfe",
}: WorkoutBarChartProps) {
  // Hide X-axis week labels on portrait mobile (too narrow to fit)
  const [hideXLabels, setHideXLabels] = useState(false);
  useEffect(() => {
    const check = () => {
      setHideXLabels(window.innerWidth < 768 && window.innerHeight > window.innerWidth);
    };
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  const weeks = aggregateToWeeks(days);

  const maxMinutes = Math.max(...weeks.map((w) => w.completed + w.planned), 60);
  const maxHours = Math.ceil(maxMinutes / 60);

  const formatYAxis = (minutes: number) => {
    if (minutes === 0) return "0";
    const h = minutes / 60;
    return h >= 1 ? `${h}ч` : `${minutes}м`;
  };

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={weeks}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
        barSize={40}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis
          dataKey="label"
          tick={hideXLabels ? false : { fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          interval={0}
        />
        <YAxis
          tickFormatter={formatYAxis}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          domain={[0, maxHours * 60]}
          width={36}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
        {/* Completed bar (bottom of stack) */}
        <Bar
          dataKey="completed"
          stackId="workouts"
          name="completed"
          fill={completedColor}
          radius={[0, 0, 3, 3]}
        />
        {/* Planned-not-completed bar (top of stack) */}
        <Bar
          dataKey="planned"
          stackId="workouts"
          name="planned"
          fill={plannedColor}
          radius={[3, 3, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
