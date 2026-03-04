/**
 * React Query hooks for competition data fetching and mutations.
 *
 * Query key strategy:
 *   ["competitions"]                    — root invalidation key
 *   ["competitions", "list", filters]   — filtered list
 *   ["competitions", "detail", id]      — single item
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { competitionsApi } from "@/lib/api";
import type {
  Competition,
  CompetitionCreate,
  CompetitionFilters,
  CompetitionListResponse,
  CompetitionResultRequest,
  CompetitionUpdate,
} from "@/types";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const competitionKeys = {
  all: ["competitions"] as const,
  lists: () => ["competitions", "list"] as const,
  list: (filters: CompetitionFilters) =>
    ["competitions", "list", filters] as const,
  details: () => ["competitions", "detail"] as const,
  detail: (id: number) => ["competitions", "detail", id] as const,
};

// ---------------------------------------------------------------------------
// useCompetitions — list with filters
// ---------------------------------------------------------------------------

/**
 * Fetch competitions for the current user.
 * Pass filters to narrow by sport, importance, or date range.
 */
export function useCompetitions(filters: CompetitionFilters = {}) {
  return useQuery<CompetitionListResponse>({
    queryKey: competitionKeys.list(filters),
    queryFn: async () => {
      const res = await competitionsApi.list(filters);
      return res.data as CompetitionListResponse;
    },
    staleTime: 60 * 1000, // 1 minute — competitions change infrequently
  });
}

// ---------------------------------------------------------------------------
// useCompetition — single item
// ---------------------------------------------------------------------------

export function useCompetition(id: number) {
  return useQuery<Competition>({
    queryKey: competitionKeys.detail(id),
    queryFn: async () => {
      const res = await competitionsApi.get(id);
      return res.data as Competition;
    },
    enabled: id > 0,
  });
}

// ---------------------------------------------------------------------------
// useCreateCompetition
// ---------------------------------------------------------------------------

export function useCreateCompetition() {
  const queryClient = useQueryClient();
  return useMutation<Competition, Error, CompetitionCreate>({
    mutationFn: async (data) => {
      const res = await competitionsApi.create(data);
      return res.data as Competition;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: competitionKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateCompetition
// ---------------------------------------------------------------------------

export function useUpdateCompetition() {
  const queryClient = useQueryClient();
  return useMutation<
    Competition,
    Error,
    { id: number; data: CompetitionUpdate }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await competitionsApi.update(id, data);
      return res.data as Competition;
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: competitionKeys.lists() });
      queryClient.setQueryData(competitionKeys.detail(updated.id), updated);
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteCompetition
// ---------------------------------------------------------------------------

export function useDeleteCompetition() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      await competitionsApi.delete(id);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: competitionKeys.lists() });
      queryClient.removeQueries({ queryKey: competitionKeys.detail(id) });
    },
  });
}

// ---------------------------------------------------------------------------
// useAddCompetitionResult
// ---------------------------------------------------------------------------

export function useAddCompetitionResult() {
  const queryClient = useQueryClient();
  return useMutation<
    Competition,
    Error,
    { id: number; data: CompetitionResultRequest }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await competitionsApi.addResult(id, data);
      return res.data as Competition;
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: competitionKeys.lists() });
      queryClient.setQueryData(competitionKeys.detail(updated.id), updated);
      // Also invalidate workouts since result recording creates a workout
      queryClient.invalidateQueries({ queryKey: ["workouts", "list"] });
    },
  });
}
