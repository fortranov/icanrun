/**
 * DayCell — one cell in the monthly calendar grid.
 *
 * Features:
 *  - Displays day number (dimmed for out-of-month days)
 *  - Highlights today with a blue circle
 *  - Lists workout cards and competition badges
 *  - Hover state reveals a '+' button (does NOT change cell height)
 *  - Acts as a drop target for drag-and-drop
 */
"use client";

import { useDroppable } from "@dnd-kit/core";
import { cn } from "@/lib/utils";
import { WorkoutCard } from "./WorkoutCard";
import { CompetitionBadge } from "./CompetitionBadge";
import type { CalendarDay, Competition, Workout } from "@/types";

interface DayCellProps {
  day: CalendarDay;
  onAddWorkout: (date: string) => void;
  onWorkoutClick: (workout: Workout) => void;
  onToggleComplete: (id: number) => void;
  onCompetitionClick: (competition: Competition) => void;
}

export function DayCell({
  day,
  onAddWorkout,
  onWorkoutClick,
  onToggleComplete,
  onCompetitionClick,
}: DayCellProps) {
  const { isOver, setNodeRef } = useDroppable({
    id: `day-${day.date}`,
    data: { date: day.date },
  });

  const dayNum = parseInt(day.date.split("-")[2], 10);

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "relative min-h-[90px] p-1 border-b border-r border-gray-100 group",
        "transition-colors duration-100",
        !day.is_current_month && "bg-gray-50/50",
        isOver && "bg-blue-50/60 ring-1 ring-blue-300 ring-inset",
        day.is_today && "bg-blue-50/30"
      )}
    >
      {/* Day number */}
      <div className="flex items-start justify-between mb-1">
        <span
          className={cn(
            "flex items-center justify-center w-6 h-6 text-xs font-medium rounded-full select-none",
            day.is_today
              ? "bg-blue-600 text-white"
              : day.is_current_month
              ? "text-gray-700"
              : "text-gray-300"
          )}
        >
          {dayNum}
        </span>

        {/* '+' button appears on hover — absolutely positioned, no height change */}
        {day.is_current_month && (
          <button
            type="button"
            onClick={() => onAddWorkout(day.date)}
            className={cn(
              "absolute top-1 right-1 w-5 h-5 flex items-center justify-center",
              "rounded-full text-gray-400 hover:text-blue-600 hover:bg-blue-50",
              "opacity-0 group-hover:opacity-100 transition-opacity text-xs font-bold",
              "z-10"
            )}
            title="Добавить тренировку"
          >
            +
          </button>
        )}
      </div>

      {/* Content: competitions first, then workouts */}
      <div className="space-y-0.5 overflow-hidden">
        {day.competitions.map((comp) => (
          <CompetitionBadge
            key={comp.id}
            competition={comp}
            onClick={onCompetitionClick}
          />
        ))}

        {day.workouts.map((workout) => (
          <WorkoutCard
            key={workout.id}
            workout={workout}
            onClick={onWorkoutClick}
            onToggleComplete={onToggleComplete}
          />
        ))}

        {/* Show overflow count if many items */}
        {day.workouts.length + day.competitions.length > 4 && (
          <div className="text-xs text-gray-400 pl-1">
            +{day.workouts.length + day.competitions.length - 4} ещё
          </div>
        )}
      </div>
    </div>
  );
}
