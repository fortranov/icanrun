/**
 * CompetitionBadge — compact row shown on a calendar day cell for a competition.
 *
 * Displays a trophy icon + competition name (truncated).
 * Key competitions are shown with gold color, secondary with gray.
 */
"use client";

import { cn } from "@/lib/utils";
import type { Competition } from "@/types";

const COMPETITION_TYPE_LABELS: Record<string, string> = {
  run_5k:        "5 км",
  run_10k:       "10 км",
  half_marathon: "Полумарафон",
  marathon:      "Марафон",
  swimming:      "Плавание",
  cycling:       "Велогонка",
  super_sprint:  "Супер-спринт",
  sprint:        "Спринт",
  olympic:       "Олимпийская",
  half_iron:     "Half Ironman",
  iron:          "Ironman",
};

interface CompetitionBadgeProps {
  competition: Competition;
  onClick: (competition: Competition) => void;
}

export function CompetitionBadge({ competition, onClick }: CompetitionBadgeProps) {
  const isKey = competition.importance === "key";
  const typeLabel = COMPETITION_TYPE_LABELS[competition.competition_type] ?? competition.competition_type;

  return (
    <div
      className={cn(
        "flex items-center gap-1 px-1.5 py-0.5 rounded text-xs cursor-pointer select-none",
        "border transition-colors hover:shadow-sm",
        isKey
          ? "bg-amber-50 border-amber-300 text-amber-800"
          : "bg-gray-50 border-gray-200 text-gray-600"
      )}
      onClick={(e) => {
        e.stopPropagation();
        onClick(competition);
      }}
      title={`${competition.name} — ${typeLabel}`}
    >
      {/* Trophy icon */}
      <svg
        viewBox="0 0 24 24"
        className={cn("w-3 h-3 flex-shrink-0", isKey ? "text-amber-500" : "text-gray-400")}
        fill={isKey ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={isKey ? 0 : 2}
      >
        <path d="M12 2l2.4 4.8L20 7.6l-4 3.9.9 5.5-4.9-2.6L7.1 17l.9-5.5-4-3.9 5.6-.8L12 2z" />
      </svg>
      <span className="truncate font-medium">{competition.name}</span>
    </div>
  );
}
