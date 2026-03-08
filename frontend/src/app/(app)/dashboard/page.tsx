/**
 * Dashboard page — main calendar view.
 *
 * Fetches workouts and competitions for the current month, renders the
 * MonthCalendar component, and manages modal state for add/edit/view flows.
 *
 * State management:
 *   - Month navigation: Zustand calendarStore
 *   - Server data: React Query (useWorkouts, useCompetitions)
 *   - Modal open/close: local useState
 *   - Drag-and-drop rescheduling: useMoveWorkout mutation
 */
"use client";

import { useState, useCallback } from "react";
import { useCalendarStore } from "@/stores/calendarStore";
import { useWorkouts, useMoveWorkout, useToggleComplete } from "@/hooks/useWorkouts";
import { useCompetitions } from "@/hooks/useCompetitions";
import { MonthCalendar } from "@/components/calendar/MonthCalendar";
import { AddWorkoutModal } from "@/components/modals/AddWorkoutModal";
import { WorkoutDetailModal } from "@/components/modals/WorkoutDetailModal";
import { AddCompetitionModal } from "@/components/modals/AddCompetitionModal";
import { MobileRotatePrompt } from "@/components/layout/MobileRotatePrompt";
import type { Competition, Workout } from "@/types";

export default function DashboardPage() {
  const { currentYear, currentMonth } = useCalendarStore();

  // ---- Data fetching ----
  const { data: workoutsData, isLoading: workoutsLoading } = useWorkouts({
    year: currentYear,
    month: currentMonth,
  });

  const { data: competitionsData, isLoading: competitionsLoading } =
    useCompetitions({});

  const { mutate: moveWorkout } = useMoveWorkout();
  const { mutate: toggleComplete } = useToggleComplete();

  // ---- Modal state ----
  const [addWorkoutDate, setAddWorkoutDate] = useState<string | null>(null);
  const [selectedWorkout, setSelectedWorkout] = useState<Workout | null>(null);
  const [selectedCompetition, setSelectedCompetition] = useState<Competition | null>(null);
  const [addCompetitionOpen, setAddCompetitionOpen] = useState(false);

  // ---- Event handlers ----
  const handleAddWorkout = useCallback((date: string) => {
    setAddWorkoutDate(date || new Date().toISOString().split("T")[0]);
  }, []);

  const handleWorkoutClick = useCallback((workout: Workout) => {
    setSelectedWorkout(workout);
  }, []);

  const handleToggleComplete = useCallback(
    (id: number) => {
      toggleComplete(id);
    },
    [toggleComplete]
  );

  const handleCompetitionClick = useCallback((competition: Competition) => {
    setSelectedCompetition(competition);
  }, []);

  const handleMoveWorkout = useCallback(
    (workoutId: number, newDate: string) => {
      moveWorkout({ id: workoutId, newDate });
    },
    [moveWorkout]
  );

  const workouts = workoutsData?.items ?? [];
  const competitions = competitionsData?.items ?? [];

  // Filter competitions to current month for calendar display
  // (we show all competitions in the calendar regardless of current month nav)
  const isLoading = workoutsLoading || competitionsLoading;

  return (
    <>
      {/* Mobile rotate prompt — shown only on portrait mobile */}
      <MobileRotatePrompt />

      {/* Calendar (hidden on portrait mobile via MobileRotatePrompt CSS) */}
      <div>
        {/* Page actions row */}
        <div className="flex items-center justify-between mb-4 gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Тренировки</h1>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setAddCompetitionOpen(true)}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              + Соревнование
            </button>
            <button
              type="button"
              onClick={() => handleAddWorkout("")}
              className="px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              + Тренировка
            </button>
          </div>
        </div>

        <MonthCalendar
          workouts={workouts}
          competitions={competitions}
          onAddWorkout={handleAddWorkout}
          onWorkoutClick={handleWorkoutClick}
          onToggleComplete={handleToggleComplete}
          onCompetitionClick={handleCompetitionClick}
          onMoveWorkout={handleMoveWorkout}
          isLoading={isLoading}
        />
      </div>

      {/* Modals */}
      <AddWorkoutModal
        isOpen={addWorkoutDate !== null}
        onClose={() => setAddWorkoutDate(null)}
        defaultDate={addWorkoutDate ?? undefined}
      />

      <WorkoutDetailModal
        workout={selectedWorkout}
        isOpen={selectedWorkout !== null}
        onClose={() => setSelectedWorkout(null)}
      />

      <AddCompetitionModal
        isOpen={addCompetitionOpen || selectedCompetition !== null}
        onClose={() => {
          setAddCompetitionOpen(false);
          setSelectedCompetition(null);
        }}
        competition={selectedCompetition}
      />
    </>
  );
}
