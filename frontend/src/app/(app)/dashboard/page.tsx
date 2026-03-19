/**
 * Dashboard page — main calendar view.
 *
 * Portrait mobile: shows add-workout button + today's day card.
 * Landscape / desktop: shows full MonthCalendar.
 *
 * State management:
 *   - Month navigation: Zustand calendarStore
 *   - Server data: React Query (useWorkouts, useCompetitions)
 *   - Modal open/close: local useState
 *   - Drag-and-drop rescheduling: useMoveWorkout mutation
 */
"use client";

import { useState, useCallback, useMemo } from "react";
import { useCalendarStore } from "@/stores/calendarStore";
import { useWorkouts, useMoveWorkout, useToggleComplete } from "@/hooks/useWorkouts";
import { useCompetitions } from "@/hooks/useCompetitions";
import { MonthCalendar } from "@/components/calendar/MonthCalendar";
import { WorkoutCard } from "@/components/calendar/WorkoutCard";
import { CompetitionBadge } from "@/components/calendar/CompetitionBadge";
import { AddWorkoutModal } from "@/components/modals/AddWorkoutModal";
import { WorkoutDetailModal } from "@/components/modals/WorkoutDetailModal";
import { AddCompetitionModal } from "@/components/modals/AddCompetitionModal";
import { MobileRotatePrompt } from "@/components/layout/MobileRotatePrompt";
import type { Competition, Workout } from "@/types";

/** Return the first and last ISO date strings visible in the calendar grid. */
function getCalendarDateRange(year: number, month: number): { dateFrom: string; dateTo: string } {
  const firstOfMonth = new Date(year, month - 1, 1);
  let startDow = firstOfMonth.getDay();
  startDow = startDow === 0 ? 6 : startDow - 1;
  const gridStart = new Date(year, month - 1, 1 - startDow);

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
    (id: number) => { toggleComplete(id); },
    [toggleComplete]
  );

  const handleCompetitionClick = useCallback((competition: Competition) => {
    setSelectedCompetition(competition);
  }, []);

  const handleMoveWorkout = useCallback(
    (workoutId: number, newDate: string) => { moveWorkout({ id: workoutId, newDate }); },
    [moveWorkout]
  );

  const workouts = workoutsData?.items ?? [];
  const competitions = competitionsData?.items ?? [];
  const isLoading = workoutsLoading || competitionsLoading;

  // ---- Today's data for mobile portrait view ----
  const todayStr = useMemo(() => new Date().toISOString().split("T")[0], []);
  const todayDate = useMemo(() => new Date(), []);
  const todayDayNum = todayDate.getDate();
  const todayDayName = todayDate.toLocaleDateString("ru-RU", { weekday: "long" });
  const todayMonthName = todayDate.toLocaleDateString("ru-RU", { month: "long" });

  const todayWorkouts = useMemo(
    () => workouts.filter((w) => w.date === todayStr),
    [workouts, todayStr]
  );
  const todayCompetitions = useMemo(
    () => competitions.filter((c) => c.date === todayStr),
    [competitions, todayStr]
  );

  return (
    <>
      {/* Rotate prompt — small banner, portrait mobile only, shown once per session */}
      <MobileRotatePrompt />

      {/* ------------------------------------------------------------------ */}
      {/* Desktop / landscape: full calendar view                             */}
      {/* ------------------------------------------------------------------ */}
      <div className="hidden md:block landscape:block">
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

      {/* ------------------------------------------------------------------ */}
      {/* Portrait mobile: add button + today's day card                      */}
      {/* ------------------------------------------------------------------ */}
      <div className="md:hidden landscape:hidden space-y-3">
        <h1 className="text-xl font-bold text-gray-900">Тренировки</h1>

        {/* Primary add workout button */}
        <button
          type="button"
          onClick={() => handleAddWorkout(todayStr)}
          className="w-full flex items-center justify-center gap-2 py-3.5 bg-blue-600 text-white rounded-xl font-semibold text-base hover:bg-blue-700 active:bg-blue-800 transition-colors shadow-sm"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Добавить тренировку
        </button>

        {/* Today card — one calendar square */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Card header with date */}
          <div className="px-4 py-3 border-b border-gray-100 bg-blue-50/40 flex items-center gap-3">
            <span className="w-9 h-9 flex items-center justify-center bg-blue-600 text-white text-sm font-bold rounded-full flex-shrink-0">
              {todayDayNum}
            </span>
            <div>
              <p className="text-sm font-semibold text-gray-900 capitalize">{todayDayName}</p>
              <p className="text-xs text-gray-400 capitalize">{todayMonthName}</p>
            </div>
          </div>

          {/* Card body — workouts and competitions */}
          <div className="p-3">
            {isLoading ? (
              <div className="py-3 text-sm text-gray-400 animate-pulse text-center">
                Загрузка...
              </div>
            ) : todayWorkouts.length === 0 && todayCompetitions.length === 0 ? (
              <p className="py-3 text-sm text-gray-400 text-center">
                Тренировок на сегодня нет
              </p>
            ) : (
              <div className="space-y-1.5">
                {todayCompetitions.map((comp) => (
                  <CompetitionBadge
                    key={comp.id}
                    competition={comp}
                    onClick={handleCompetitionClick}
                  />
                ))}
                {todayWorkouts.map((workout) => (
                  <WorkoutCard
                    key={workout.id}
                    workout={workout}
                    onClick={handleWorkoutClick}
                    onToggleComplete={handleToggleComplete}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
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
