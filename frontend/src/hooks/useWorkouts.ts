/**
 * React Query hooks for workout data fetching and mutations.
 *
 * Query key strategy:
 *   ["workouts"]                       — root invalidation key
 *   ["workouts", "list", filters]      — list with specific filters
 *   ["workouts", "detail", id]         — single workout
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workoutsApi } from "@/lib/api";
import type {
  Workout,
  WorkoutCompleteRequest,
  WorkoutCreate,
  WorkoutFilters,
  WorkoutListResponse,
  WorkoutUpdate,
} from "@/types";

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const workoutKeys = {
  all: ["workouts"] as const,
  lists: () => ["workouts", "list"] as const,
  list: (filters: WorkoutFilters) => ["workouts", "list", filters] as const,
  details: () => ["workouts", "detail"] as const,
  detail: (id: number) => ["workouts", "detail", id] as const,
};

// ---------------------------------------------------------------------------
// useWorkouts — list with filters
// ---------------------------------------------------------------------------

/**
 * Fetch workouts with optional filters.
 * Most common usage: pass { year, month } to get calendar month data.
 */
export function useWorkouts(filters: WorkoutFilters = {}) {
  return useQuery<WorkoutListResponse>({
    queryKey: workoutKeys.list(filters),
    queryFn: async () => {
      const res = await workoutsApi.list(filters);
      return res.data as WorkoutListResponse;
    },
    staleTime: 30 * 1000, // 30 seconds — calendar refreshes often
  });
}

// ---------------------------------------------------------------------------
// useWorkout — single item
// ---------------------------------------------------------------------------

export function useWorkout(id: number) {
  return useQuery<Workout>({
    queryKey: workoutKeys.detail(id),
    queryFn: async () => {
      const res = await workoutsApi.get(id);
      return res.data as Workout;
    },
    enabled: id > 0,
  });
}

// ---------------------------------------------------------------------------
// useCreateWorkout
// ---------------------------------------------------------------------------

export function useCreateWorkout() {
  const queryClient = useQueryClient();
  return useMutation<Workout, Error, WorkoutCreate>({
    mutationFn: async (data) => {
      const res = await workoutsApi.create(data);
      return res.data as Workout;
    },
    onSuccess: () => {
      // Invalidate all list queries so every open calendar view refreshes
      queryClient.invalidateQueries({ queryKey: workoutKeys.lists() });
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateWorkout
// ---------------------------------------------------------------------------

export function useUpdateWorkout() {
  const queryClient = useQueryClient();
  return useMutation<
    Workout,
    Error,
    { id: number; data: WorkoutUpdate }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await workoutsApi.update(id, data);
      return res.data as Workout;
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: workoutKeys.lists() });
      queryClient.setQueryData(workoutKeys.detail(updated.id), updated);
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteWorkout
// ---------------------------------------------------------------------------

export function useDeleteWorkout() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (id) => {
      await workoutsApi.delete(id);
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: workoutKeys.lists() });
      queryClient.removeQueries({ queryKey: workoutKeys.detail(id) });
    },
  });
}

// ---------------------------------------------------------------------------
// useCompleteWorkout
// ---------------------------------------------------------------------------

export function useCompleteWorkout() {
  const queryClient = useQueryClient();
  return useMutation<
    Workout,
    Error,
    { id: number; data?: WorkoutCompleteRequest }
  >({
    mutationFn: async ({ id, data }) => {
      const res = await workoutsApi.complete(id, data);
      return res.data as Workout;
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: workoutKeys.lists() });
      queryClient.setQueryData(workoutKeys.detail(updated.id), updated);
    },
  });
}

// ---------------------------------------------------------------------------
// useToggleComplete — lightweight checkbox toggle
// ---------------------------------------------------------------------------

export function useToggleComplete() {
  const queryClient = useQueryClient();
  return useMutation<Workout, Error, number>({
    mutationFn: async (id) => {
      const res = await workoutsApi.toggleComplete(id);
      return res.data as Workout;
    },
    // Optimistic update: flip the flag immediately in the cache
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: workoutKeys.detail(id) });
      const previous = queryClient.getQueryData<Workout>(workoutKeys.detail(id));
      if (previous) {
        queryClient.setQueryData(workoutKeys.detail(id), {
          ...previous,
          is_completed: !previous.is_completed,
        });
      }
      return { previous };
    },
    onError: (_err, id, context) => {
      const ctx = context as { previous?: Workout } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData(workoutKeys.detail(id), ctx.previous);
      }
    },
    onSettled: (updated) => {
      if (updated) {
        queryClient.invalidateQueries({ queryKey: workoutKeys.lists() });
      }
    },
  });
}

// ---------------------------------------------------------------------------
// useMoveWorkout — drag-and-drop date change
// ---------------------------------------------------------------------------

export function useMoveWorkout() {
  const queryClient = useQueryClient();
  return useMutation<Workout, Error, { id: number; newDate: string }>({
    mutationFn: async ({ id, newDate }) => {
      const res = await workoutsApi.move(id, newDate);
      return res.data as Workout;
    },
    onSuccess: (updated) => {
      // Invalidate all lists since workout may have crossed month boundaries
      queryClient.invalidateQueries({ queryKey: workoutKeys.lists() });
      queryClient.setQueryData(workoutKeys.detail(updated.id), updated);
    },
  });
}
