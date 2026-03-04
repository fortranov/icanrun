/**
 * Hook for calendar grid computation.
 * Returns a 6x7 grid of CalendarDay objects for the given month.
 */
"use client";

import { useMemo } from "react";
import type { CalendarDay, Competition, Workout } from "@/types";

export function useCalendarGrid(
  year: number,
  month: number,
  workouts: Workout[] = [],
  competitions: Competition[] = []
): CalendarDay[][] {
  return useMemo(() => {
    const today = new Date().toISOString().split("T")[0];

    // Build lookup maps for O(1) access per date
    const workoutsByDate = new Map<string, Workout[]>();
    for (const w of workouts) {
      if (!workoutsByDate.has(w.date)) workoutsByDate.set(w.date, []);
      workoutsByDate.get(w.date)!.push(w);
    }

    const competitionsByDate = new Map<string, Competition[]>();
    for (const c of competitions) {
      if (!competitionsByDate.has(c.date)) competitionsByDate.set(c.date, []);
      competitionsByDate.get(c.date)!.push(c);
    }

    // First day of month (0=Sunday in JS, convert to 0=Monday)
    const firstDay = new Date(year, month - 1, 1);
    let startWeekday = firstDay.getDay(); // 0=Sun
    startWeekday = startWeekday === 0 ? 6 : startWeekday - 1; // convert to Mon=0

    const daysInMonth = new Date(year, month, 0).getDate();
    const daysInPrevMonth = new Date(year, month - 1, 0).getDate();

    const grid: CalendarDay[][] = [];
    let dayCounter = 1 - startWeekday;

    for (let week = 0; week < 6; week++) {
      const weekRow: CalendarDay[] = [];
      for (let dow = 0; dow < 7; dow++) {
        const dayNum = dayCounter;
        let cellYear = year;
        let cellMonth = month;
        let cellDay: number;
        let isCurrentMonth = true;

        if (dayNum < 1) {
          // Days from previous month
          cellDay = daysInPrevMonth + dayNum;
          cellMonth = month - 1;
          if (cellMonth < 1) {
            cellMonth = 12;
            cellYear = year - 1;
          }
          isCurrentMonth = false;
        } else if (dayNum > daysInMonth) {
          // Days from next month
          cellDay = dayNum - daysInMonth;
          cellMonth = month + 1;
          if (cellMonth > 12) {
            cellMonth = 1;
            cellYear = year + 1;
          }
          isCurrentMonth = false;
        } else {
          cellDay = dayNum;
        }

        const dateStr = `${cellYear}-${String(cellMonth).padStart(2, "0")}-${String(cellDay).padStart(2, "0")}`;

        weekRow.push({
          date: dateStr,
          workouts: workoutsByDate.get(dateStr) ?? [],
          competitions: competitionsByDate.get(dateStr) ?? [],
          is_current_month: isCurrentMonth,
          is_today: dateStr === today,
        });

        dayCounter++;
      }
      grid.push(weekRow);

      // Stop if we've passed the end of the month and filled at least 4 weeks
      if (week >= 3 && dayCounter > daysInMonth + 1) break;
    }

    return grid;
  }, [year, month, workouts, competitions]);
}
