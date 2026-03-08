/**
 * WorkoutCard — compact card displayed on a calendar day cell.
 *
 * Shows:
 *   - Sport color stripe on the left
 *   - Sport icon + optional workout type badge
 *   - Duration formatted as "Xh Ym"
 *   - Checkbox (top-right) for is_completed toggle
 *   - Click opens WorkoutDetailModal
 *
 * When used inside drag-and-drop context, the card renders as a draggable item.
 */
"use client";

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { cn, formatDuration } from "@/lib/utils";
import { Bike, Dumbbell, Footprints, Medal, Waves, type LucideIcon } from "lucide-react";
import type { Workout } from "@/types";

// Sport icon map — recognizable sport-specific icons
const SPORT_ICONS: Record<string, LucideIcon> = {
  running: Footprints,
  swimming: Waves,
  cycling: Bike,
  strength: Dumbbell,
  triathlon: Medal,
};

const SPORT_COLORS_BORDER: Record<string, string> = {
  running:   "border-l-red-400",
  swimming:  "border-l-blue-400",
  cycling:   "border-l-amber-400",
  strength:  "border-l-violet-400",
  triathlon: "border-l-emerald-400",
};

const SPORT_TEXT_COLORS: Record<string, string> = {
  running:   "text-red-700",
  swimming:  "text-blue-700",
  cycling:   "text-amber-700",
  strength:  "text-violet-700",
  triathlon: "text-emerald-700",
};

const SPORT_BG_LIGHT: Record<string, string> = {
  running:   "bg-red-50",
  swimming:  "bg-blue-50",
  cycling:   "bg-amber-50",
  strength:  "bg-violet-50",
  triathlon: "bg-emerald-50",
};

interface WorkoutCardProps {
  workout: Workout;
  onClick: (workout: Workout) => void;
  onToggleComplete: (id: number) => void;
  isDragging?: boolean;
}

export function WorkoutCard({
  workout,
  onClick,
  onToggleComplete,
  isDragging = false,
}: WorkoutCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging: dndDragging } =
    useDraggable({ id: `workout-${workout.id}`, data: { workout } });

  const style = transform
    ? { transform: CSS.Translate.toString(transform) }
    : undefined;

  const isCompleted = workout.is_completed;
  const sportColor = SPORT_COLORS_BORDER[workout.sport_type] ?? "border-l-gray-300";
  const sportBg = SPORT_BG_LIGHT[workout.sport_type] ?? "bg-gray-50";
  const sportText = SPORT_TEXT_COLORS[workout.sport_type] ?? "text-gray-600";
  const SportIcon = SPORT_ICONS[workout.sport_type];

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className={cn(
        "group relative flex items-center gap-1.5 px-1.5 py-1 rounded border-l-2 cursor-pointer select-none",
        "transition-all text-xs leading-tight",
        sportColor,
        dndDragging ? "opacity-50 shadow-lg z-50 scale-105" : "hover:shadow-sm",
        isCompleted ? "opacity-60" : sportBg,
        isCompleted && "bg-gray-50"
      )}
      onClick={(e) => {
        e.stopPropagation();
        onClick(workout);
      }}
    >
      {/* Drag handle — invisible, covers left portion */}
      <div
        {...listeners}
        className="absolute inset-y-0 left-0 w-4 cursor-grab active:cursor-grabbing"
        onClick={(e) => e.stopPropagation()}
      />

      {/* Sport icon */}
      {SportIcon ? (
        <SportIcon className={cn("w-3.5 h-3.5 flex-shrink-0", sportText)} strokeWidth={2.2} />
      ) : null}

      {/* Duration */}
      <span
        className={cn(
          "flex-1 font-medium truncate",
          isCompleted ? "text-gray-400 line-through" : sportText
        )}
      >
        {formatDuration(workout.duration_minutes)}
      </span>

      {/* Completed checkbox — top-right */}
      <button
        type="button"
        className={cn(
          "flex-shrink-0 w-3.5 h-3.5 rounded border transition-colors",
          isCompleted
            ? "bg-green-500 border-green-500 text-white"
            : "border-gray-300 bg-white hover:border-green-400"
        )}
        onClick={(e) => {
          e.stopPropagation();
          onToggleComplete(workout.id);
        }}
        title={isCompleted ? "Отметить как невыполненную" : "Отметить как выполненную"}
      >
        {isCompleted && (
          <svg viewBox="0 0 12 12" fill="none" className="w-full h-full">
            <path
              d="M2 6l3 3 5-5"
              stroke="white"
              strokeWidth={1.8}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </button>

      {/* Planned indicator (not completed, planned source) */}
      {workout.source === "planned" && !isCompleted && (
        <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-blue-400 opacity-70" />
      )}
    </div>
  );
}
