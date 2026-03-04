/**
 * React Query hooks for training plan data.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { plansApi } from "@/lib/api";
import type { PlanDetailResponse, PlanGenerateRequest, TrainingPlan } from "@/types";

export const planKeys = {
  all: ["plans"] as const,
  lists: () => ["plans", "list"] as const,
  detail: (id: number) => ["plans", "detail", id] as const,
};

export function usePlans() {
  return useQuery<TrainingPlan[]>({
    queryKey: planKeys.lists(),
    queryFn: async () => {
      const res = await plansApi.list();
      return res.data as TrainingPlan[];
    },
    staleTime: 60 * 1000,
  });
}

export function useGeneratePlan() {
  const queryClient = useQueryClient();
  return useMutation<PlanDetailResponse, Error, PlanGenerateRequest>({
    mutationFn: async (data) => {
      const res = await plansApi.generate(data);
      return res.data as PlanDetailResponse;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
      // Invalidate workouts since plan generation creates workout records
      queryClient.invalidateQueries({ queryKey: ["workouts", "list"] });
    },
  });
}

export function useDeletePlan() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      await plansApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: planKeys.lists() });
      queryClient.invalidateQueries({ queryKey: ["workouts", "list"] });
    },
  });
}
