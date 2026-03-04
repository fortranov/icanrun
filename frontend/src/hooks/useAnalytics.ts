/**
 * React Query hooks for analytics data.
 *
 * Query key strategy:
 *   ["analytics", "monthly", year, month, sport]
 *   ["analytics", "daily", year, month, sport]
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import type { DailyStatsResponse, MonthlyStats } from "@/types";

export const analyticsKeys = {
  monthly: (year: number, month: number, sport?: string) =>
    ["analytics", "monthly", year, month, sport ?? "all"] as const,
  daily: (year: number, month: number, sport?: string) =>
    ["analytics", "daily", year, month, sport ?? "all"] as const,
};

export function useMonthlyStats(year: number, month: number, sport?: string) {
  return useQuery<MonthlyStats>({
    queryKey: analyticsKeys.monthly(year, month, sport),
    queryFn: async () => {
      const res = await analyticsApi.monthly(year, month, sport);
      return res.data as MonthlyStats;
    },
    staleTime: 60 * 1000,
  });
}

export function useDailyStats(year: number, month: number, sport?: string) {
  return useQuery<DailyStatsResponse>({
    queryKey: analyticsKeys.daily(year, month, sport),
    queryFn: async () => {
      const res = await analyticsApi.daily(year, month, sport);
      return res.data as DailyStatsResponse;
    },
    staleTime: 60 * 1000,
  });
}
