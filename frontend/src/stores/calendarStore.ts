/**
 * Zustand store for calendar navigation state.
 */
"use client";

import { create } from "zustand";

interface CalendarState {
  currentYear: number;
  currentMonth: number; // 1-12

  setMonth: (year: number, month: number) => void;
  prevMonth: () => void;
  nextMonth: () => void;
  goToToday: () => void;
}

const now = new Date();

export const useCalendarStore = create<CalendarState>((set, get) => ({
  currentYear: now.getFullYear(),
  currentMonth: now.getMonth() + 1,

  setMonth: (year, month) => set({ currentYear: year, currentMonth: month }),

  prevMonth: () => {
    const { currentYear, currentMonth } = get();
    if (currentMonth === 1) {
      set({ currentYear: currentYear - 1, currentMonth: 12 });
    } else {
      set({ currentMonth: currentMonth - 1 });
    }
  },

  nextMonth: () => {
    const { currentYear, currentMonth } = get();
    if (currentMonth === 12) {
      set({ currentYear: currentYear + 1, currentMonth: 1 });
    } else {
      set({ currentMonth: currentMonth + 1 });
    }
  },

  goToToday: () => {
    const now = new Date();
    set({ currentYear: now.getFullYear(), currentMonth: now.getMonth() + 1 });
  },
}));
