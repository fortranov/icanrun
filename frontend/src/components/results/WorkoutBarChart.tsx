/**
 * WorkoutBarChart — monthly training bar chart.
 *
 * X-axis: days of the month (1–31)
 * Y-axis: hours
 * Each bar is split into two stacked segments:
 *   1. Completed workouts (solid sport color)
 *   2. Planned but not completed (lighter / striped)
 *
 * Uses Recharts ComposedChart with BarChart stacking.
 */
"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatDuration } from "@/lib/utils";
import type { DayStats } from "@/types";

interface WorkoutBarChartProps {
  days: DayStats[];
  /** Recharts color for completed bar */
  completedColor?: string;
  /** Recharts color for planned-not-completed bar */
  plannedColor?: string;
}

interface TooltipPayloadEntry {
  name: string;
  value: number;
  color?: string;
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
        <p className="text-green-600">
          Выполнено: {formatDuration(completed)}
        </p>
      )}
      {planned > 0 && (
        <p className="text-orange-400">
          Запланировано: {formatDuration(planned)}
        </p>
      )}
      <p className="text-gray-600 mt-1 border-t border-gray-100 pt-1">
        Итого: {formatDuration(total)}
      </p>
    </div>
  );
}

export function WorkoutBarChart({
  days,
  completedColor = "#3b82f6",
  plannedColor = "#bfdbfe",
}: WorkoutBarChartProps) {
  // Convert minutes to hours for Y-axis, keep day number for X-axis
  const chartData = days.map((d) => ({
    day: parseInt(d.date.split("-")[2], 10),
    dateStr: d.date,
    completed: d.completed_minutes,
    planned: d.planned_minutes,
    total: d.total_minutes,
  }));

  // Max Y value in hours (rounded up to nearest whole)
  const maxMinutes = Math.max(...chartData.map((d) => d.total), 60);
  const maxHours = Math.ceil(maxMinutes / 60);

  const formatYAxis = (minutes: number) => {
    if (minutes === 0) return "0";
    const h = minutes / 60;
    return h >= 1 ? `${h}h` : `${minutes}m`;
  };

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={chartData}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
        barSize={12}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          // Show every 5th day label to avoid crowding
          tickFormatter={(v) => (v % 5 === 0 || v === 1 ? String(v) : "")}
        />
        <YAxis
          tickFormatter={formatYAxis}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          domain={[0, maxHours * 60]}
          width={36}
        />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: "#f8fafc" }}
        />
        {/* Completed bar (bottom of stack) */}
        <Bar
          dataKey="completed"
          stackId="workouts"
          name="completed"
          fill={completedColor}
          radius={[0, 0, 0, 0]}
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
