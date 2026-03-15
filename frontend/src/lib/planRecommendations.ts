/**
 * Smart defaults for "max hours per week" and "sessions per week"
 * based on competition type, athlete level, and current pace / speed.
 *
 * Sources:
 *   - Joe Friel, "The Triathlete's Training Bible" (2004)
 *   - Jack Daniels, "Daniels' Running Formula" (2014)
 *   - Joe Friel, "Cycling Past 50" / "The Cyclist's Training Bible"
 *   - TrainingPeaks Annual Training Plan guidelines
 *   - USA Triathlon coaching certification materials
 */

import type { AthleteLevel, CompetitionType, SportType } from "@/types";

// ---------------------------------------------------------------------------
// Base volume table
// ---------------------------------------------------------------------------

type LevelKey = "beginner" | "intermediate" | "advanced";

interface VolumeRec {
  sessions: number; // sessions per week
  hours: number;    // max hours per week (peak week target)
}

// [beginner, intermediate, advanced]
type LevelTriplet = [VolumeRec, VolumeRec, VolumeRec];

const BASE_VOLUME: Partial<Record<CompetitionType | "maintenance", LevelTriplet>> = {
  // ---- Running ----
  run_5k: [
    { sessions: 3, hours: 4 },
    { sessions: 4, hours: 6 },
    { sessions: 5, hours: 8 },
  ],
  run_10k: [
    { sessions: 3, hours: 5 },
    { sessions: 4, hours: 7 },
    { sessions: 5, hours: 9 },
  ],
  half_marathon: [
    { sessions: 4, hours: 6 },
    { sessions: 4, hours: 8 },
    { sessions: 5, hours: 11 },
  ],
  marathon: [
    { sessions: 4, hours: 8 },
    { sessions: 5, hours: 11 },
    { sessions: 6, hours: 15 },
  ],
  // ---- Swimming ----
  swimming: [
    { sessions: 3, hours: 3 },
    { sessions: 4, hours: 5 },
    { sessions: 5, hours: 8 },
  ],
  // ---- Cycling ----
  cycling: [
    { sessions: 3, hours: 6 },
    { sessions: 4, hours: 9 },
    { sessions: 5, hours: 12 },
  ],
  // ---- Triathlon ----
  super_sprint: [
    { sessions: 4, hours: 6 },
    { sessions: 5, hours: 8 },
    { sessions: 5, hours: 10 },
  ],
  sprint: [
    { sessions: 4, hours: 7 },
    { sessions: 5, hours: 9 },
    { sessions: 6, hours: 12 },
  ],
  olympic: [
    { sessions: 5, hours: 8 },
    { sessions: 5, hours: 11 },
    { sessions: 6, hours: 14 },
  ],
  half_iron: [
    { sessions: 5, hours: 10 },
    { sessions: 6, hours: 13 },
    { sessions: 6, hours: 17 },
  ],
  iron: [
    { sessions: 6, hours: 12 },
    { sessions: 6, hours: 16 },
    { sessions: 6, hours: 20 },
  ],
  // ---- Maintenance (no competition) ----
  maintenance: [
    { sessions: 3, hours: 4 },
    { sessions: 4, hours: 6 },
    { sessions: 5, hours: 8 },
  ],
};

const LEVEL_INDEX: Record<LevelKey, number> = {
  beginner: 0,
  intermediate: 1,
  advanced: 2,
};

// ---------------------------------------------------------------------------
// Pace / speed multiplier for hours
// ---------------------------------------------------------------------------

/**
 * Running pace in min/km → volume multiplier.
 * Slower runners need less volume; faster runners have higher aerobic capacity.
 */
function runPaceMultiplier(paceMinPerKm: number): number {
  if (paceMinPerKm > 7.5) return 0.80;
  if (paceMinPerKm > 6.5) return 0.90;
  if (paceMinPerKm > 5.5) return 1.00;
  if (paceMinPerKm > 4.5) return 1.10;
  return 1.20;
}

/**
 * Swimming pace in total seconds per 100m → volume multiplier.
 */
function swimPaceMultiplier(totalSeconds: number): number {
  if (totalSeconds > 150) return 0.80; // > 2:30/100m
  if (totalSeconds > 120) return 0.90; // 2:00–2:30
  if (totalSeconds > 95)  return 1.00; // 1:35–2:00
  if (totalSeconds > 75)  return 1.10; // 1:15–1:35
  return 1.20;                          // < 1:15
}

/**
 * Cycling speed in km/h → volume multiplier.
 */
function cyclingSpeedMultiplier(kmh: number): number {
  if (kmh < 18) return 0.80;
  if (kmh < 22) return 0.90;
  if (kmh < 28) return 1.00;
  if (kmh < 34) return 1.10;
  return 1.20;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface VolumeRecommendation {
  hours: number;
  sessions: number;
}

/**
 * Return suggested maxHoursPerWeek and sessionsPerWeek based on
 * competition type, athlete level, and current baseline pace / speed.
 *
 * @param sport        Selected sport type
 * @param compType     CompetitionType value or null for maintenance plan
 * @param level        Athlete self-reported level
 * @param runPace      Long-run pace in min/km (e.g. 5.5 for 5:30/km)
 * @param swimMin      Swim pace minutes part per 100m
 * @param swimSec      Swim pace seconds part per 100m
 * @param rideSpeed    Long-ride average speed in km/h
 */
export function getVolumeRecommendation(
  sport: SportType,
  compType: CompetitionType | null,
  level: AthleteLevel,
  runPace?: number | null,
  swimMin?: number | null,
  swimSec?: number | null,
  rideSpeed?: number | null,
): VolumeRecommendation {
  const key = compType ?? "maintenance";
  const triplet = BASE_VOLUME[key as CompetitionType | "maintenance"]
    ?? BASE_VOLUME["maintenance"]!;

  const base = triplet[LEVEL_INDEX[level]];

  // Compute pace/speed multiplier for hours (sessions count stays fixed)
  let mult = 1.0;
  if (sport === "running" && runPace != null && runPace > 0) {
    mult = runPaceMultiplier(runPace);
  } else if (sport === "swimming" && (swimMin != null || swimSec != null)) {
    const totalSec = (swimMin ?? 0) * 60 + (swimSec ?? 0);
    if (totalSec > 0) mult = swimPaceMultiplier(totalSec);
  } else if (sport === "cycling" && rideSpeed != null && rideSpeed > 0) {
    mult = cyclingSpeedMultiplier(rideSpeed);
  }

  const hours = Math.min(40, Math.max(1, Math.round(base.hours * mult * 2) / 2));

  return { hours, sessions: base.sessions };
}
