/**
 * General utility functions for the frontend.
 */
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { SportType, WorkoutType } from "@/types";

/**
 * Merge Tailwind CSS class names safely (handles conflicts).
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format duration in minutes to "Xh Ym" display string.
 */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0 && mins > 0) return `${hours}h ${mins}m`;
  if (hours > 0) return `${hours}h`;
  return `${mins}m`;
}

/**
 * Get Tailwind color class for a sport type.
 */
export function getSportColor(sport: SportType): string {
  const colors: Record<SportType, string> = {
    running: "bg-red-500",
    swimming: "bg-blue-500",
    cycling: "bg-amber-500",
    strength: "bg-violet-500",
    triathlon: "bg-emerald-500",
  };
  return colors[sport] ?? "bg-gray-400";
}

/**
 * Get sport display name in Russian.
 */
export function getSportLabel(sport: SportType): string {
  const labels: Record<SportType, string> = {
    running: "Бег",
    swimming: "Плавание",
    cycling: "Велосипед",
    strength: "Силовые",
    triathlon: "Триатлон",
  };
  return labels[sport] ?? sport;
}

/**
 * Get workout type display name in Russian.
 */
export function getWorkoutTypeLabel(type: WorkoutType | null): string {
  if (!type) return "";
  const labels: Record<WorkoutType, string> = {
    recovery: "Восстановление",
    long: "Длинная",
    interval: "Интервалы",
    threshold: "Пороговая",
  };
  return labels[type] ?? type;
}

/**
 * Get Russian month name for a month number (1-12).
 */
export function getMonthName(month: number): string {
  const months = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
  ];
  return months[month - 1] ?? "";
}

/**
 * Get Russian short weekday names starting from Monday.
 */
export const WEEKDAY_NAMES_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export const WEEKDAY_NAMES_FULL = [
  "Понедельник", "Вторник", "Среда",
  "Четверг", "Пятница", "Суббота", "Воскресенье",
];

/**
 * Format ISO date string to "DD.MM.YYYY".
 */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}.${month}.${year}`;
}

/**
 * Get today's date as "YYYY-MM-DD" string.
 */
export function todayString(): string {
  return new Date().toISOString().split("T")[0];
}

/**
 * Check if a subscription plan has access to training plans.
 */
export function canUsePlans(plan: string | undefined): boolean {
  return plan === "trial" || plan === "pro";
}

/**
 * Check if a subscription plan has access to Garmin integration.
 */
export function canUseGarmin(plan: string | undefined): boolean {
  return plan === "trial" || plan === "basic" || plan === "pro";
}
