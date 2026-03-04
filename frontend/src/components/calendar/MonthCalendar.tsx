/**
 * MonthCalendar — full monthly calendar with drag-and-drop workout rescheduling.
 *
 * Layout:
 *   - Header: month navigation (prev/next arrows, month-year label, "Today" button)
 *   - 7-column weekday header (Пн–Вс)
 *   - Calendar grid: rows of DayCells
 *   - Right sidebar: SportSummaryPanel
 *
 * Drag-and-drop:
 *   - Uses @dnd-kit/core DndContext wrapping the entire grid
 *   - On drop: calls onMoveWorkout(workoutId, newDate)
 *   - Works within the visible week rows; cross-month drops allowed
 *
 * Data flow:
 *   - workouts and competitions are received as arrays (pre-fetched by parent)
 *   - useCalendarGrid() derives the 6x7 grid from raw arrays
 */
"use client";

import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { useCallback, useState } from "react";
import { useCalendarStore } from "@/stores/calendarStore";
import { useCalendarGrid } from "@/hooks/useCalendar";
import { DayCell } from "./DayCell";
import { SportSummaryPanel } from "./SportSummaryPanel";
import { WorkoutCard } from "./WorkoutCard";
import { cn, getMonthName, WEEKDAY_NAMES_SHORT } from "@/lib/utils";
import type { Competition, Workout } from "@/types";

interface MonthCalendarProps {
  workouts: Workout[];
  competitions: Competition[];
  onAddWorkout: (date: string) => void;
  onWorkoutClick: (workout: Workout) => void;
  onToggleComplete: (id: number) => void;
  onCompetitionClick: (competition: Competition) => void;
  onMoveWorkout: (workoutId: number, newDate: string) => void;
  isLoading?: boolean;
}

export function MonthCalendar({
  workouts,
  competitions,
  onAddWorkout,
  onWorkoutClick,
  onToggleComplete,
  onCompetitionClick,
  onMoveWorkout,
  isLoading = false,
}: MonthCalendarProps) {
  const { currentYear, currentMonth, prevMonth, nextMonth, goToToday } =
    useCalendarStore();

  const grid = useCalendarGrid(currentYear, currentMonth, workouts, competitions);

  // Track the workout being dragged for DragOverlay
  const [activeWorkout, setActiveWorkout] = useState<Workout | null>(null);

  const sensors = useSensors(
    useSensor(MouseSensor, {
      // Require 5px of movement before drag starts (avoids accidental drags on click)
      activationConstraint: { distance: 5 },
    }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 250, tolerance: 5 },
    })
  );

  const handleDragStart = useCallback(
    (event: { active: { data: { current?: { workout?: Workout } } } }) => {
      const workout = event.active.data.current?.workout ?? null;
      setActiveWorkout(workout);
    },
    []
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveWorkout(null);
      const { active, over } = event;
      if (!over) return;

      const workout = active.data.current?.workout as Workout | undefined;
      const newDate = over.data.current?.date as string | undefined;

      if (workout && newDate && newDate !== workout.date) {
        onMoveWorkout(workout.id, newDate);
      }
    },
    [onMoveWorkout]
  );

  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === currentYear &&
    today.getMonth() + 1 === currentMonth;

  return (
    <div className="flex gap-4">
      {/* Main calendar area */}
      <div className="flex-1 min-w-0">
        {/* Calendar header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={prevMonth}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
              aria-label="Предыдущий месяц"
            >
              <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            <h2 className="text-lg font-semibold text-gray-900 min-w-[160px] text-center">
              {getMonthName(currentMonth)} {currentYear}
            </h2>

            <button
              type="button"
              onClick={nextMonth}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
              aria-label="Следующий месяц"
            >
              <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {!isCurrentMonth && (
              <button
                type="button"
                onClick={goToToday}
                className="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
              >
                Сегодня
              </button>
            )}

            {/* Add competition button */}
            <button
              type="button"
              onClick={() => onAddWorkout("")}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
            >
              + Тренировка
            </button>
          </div>
        </div>

        {/* Loading overlay */}
        {isLoading && (
          <div className="text-center py-2 text-sm text-gray-400 animate-pulse">
            Загрузка...
          </div>
        )}

        {/* Calendar grid */}
        <DndContext
          sensors={sensors}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
            {/* Weekday header row */}
            <div className="grid grid-cols-7 border-b border-gray-200 bg-gray-50">
              {WEEKDAY_NAMES_SHORT.map((name) => (
                <div
                  key={name}
                  className="py-2 text-center text-xs font-semibold text-gray-500 uppercase tracking-wide"
                >
                  {name}
                </div>
              ))}
            </div>

            {/* Week rows */}
            {grid.map((week, weekIdx) => (
              <div key={weekIdx} className="grid grid-cols-7">
                {week.map((day) => (
                  <DayCell
                    key={day.date}
                    day={day}
                    onAddWorkout={onAddWorkout}
                    onWorkoutClick={onWorkoutClick}
                    onToggleComplete={onToggleComplete}
                    onCompetitionClick={onCompetitionClick}
                  />
                ))}
              </div>
            ))}
          </div>

          {/* Drag overlay — renders a preview of the dragged workout */}
          <DragOverlay>
            {activeWorkout ? (
              <div className="opacity-90 pointer-events-none shadow-xl">
                <WorkoutCard
                  workout={activeWorkout}
                  onClick={() => {}}
                  onToggleComplete={() => {}}
                  isDragging
                />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Right sidebar */}
      <SportSummaryPanel
        workouts={workouts}
        year={currentYear}
        month={currentMonth}
      />
    </div>
  );
}
