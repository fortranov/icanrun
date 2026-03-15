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

/** Return the first and last ISO date strings visible in the calendar grid. */
function getCalendarDateRange(year: number, month: number): { dateFrom: string; dateTo: string } {
  // First day of month → find Monday of that week
  const firstOfMonth = new Date(year, month - 1, 1);
  let startDow = firstOfMonth.getDay(); // 0=Sun
  startDow = startDow === 0 ? 6 : startDow - 1; // Mon=0
  const gridStart = new Date(year, month - 1, 1 - startDow);

  // Last day of month → find Sunday of that week
  const daysInMonth = new Date(year, month, 0).getDate();
  const lastOfMonth = new Date(year, month - 1, daysInMonth);
  let endDow = lastOfMonth.getDay();
  endDow = endDow === 0 ? 6 : endDow - 1;
  const daysToEnd = endDow === 6 ? 0 : 6 - endDow;
  const gridEnd = new Date(year, month - 1, daysInMonth + daysToEnd);

  return {
    dateFrom: gridStart.toISOString().split("T")[0],
    dateTo: gridEnd.toISOString().split("T")[0],
  };
}

export default function DashboardPage() {
  const { currentYear, currentMonth } = useCalendarStore();

  // ---- Data fetching ----
  const { dateFrom, dateTo } = getCalendarDateRange(currentYear, currentMonth);
  const { data: workoutsData, isLoading: workoutsLoading } = useWorkouts({
    date_from: dateFrom,
    date_to: dateTo,
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
