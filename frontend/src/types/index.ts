/**
 * Shared TypeScript types mirroring the backend Pydantic schemas.
 * Keep in sync with backend/app/schemas/ and backend/app/utils/enums.py
 */

// ---- Enums ----

export type SportType =
  | "running"
  | "swimming"
  | "cycling"
  | "strength"
  | "triathlon";

export type WorkoutType = "recovery" | "long" | "interval" | "threshold" | "aerobic";

export type WorkoutSource = "planned" | "manual" | "garmin";

export type CompetitionType =
  | "run_5k"
  | "run_10k"
  | "half_marathon"
  | "marathon"
  | "swimming"
  | "cycling"
  | "super_sprint"
  | "sprint"
  | "olympic"
  | "half_iron"
  | "iron";

export type CompetitionImportance = "key" | "secondary";

export type UserRole = "user" | "admin";

export type SubscriptionPlan = "trial" | "basic" | "pro";

export type GenderType = "male" | "female" | "other";

// ---- Auth ----

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ---- User ----

export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  google_oauth_enabled: boolean;
  email_confirmed: boolean;
  birth_year: number | null;
  gender: GenderType | null;
  weight_kg: number | null;
  height_cm: number | null;
  created_at: string;
}

// ---- Subscription ----

export interface Subscription {
  id: number;
  user_id: number;
  plan: SubscriptionPlan;
  started_at: string;
  expires_at: string | null;
  is_active: boolean;
}

// ---- Workout ----

export interface Workout {
  id: number;
  user_id: number;
  sport_type: SportType;
  workout_type: WorkoutType | null;
  source: WorkoutSource;
  date: string; // ISO date string "YYYY-MM-DD"
  duration_minutes: number;
  is_completed: boolean;
  comment: string | null;
  plan_id: number | null;
  garmin_activity_id: string | null;
  created_at: string;
}

export interface WorkoutCreate {
  sport_type: SportType;
  workout_type?: WorkoutType | null;
  date: string;
  duration_minutes: number;
  comment?: string | null;
}

export interface WorkoutUpdate {
  sport_type?: SportType;
  workout_type?: WorkoutType | null;
  date?: string;
  duration_minutes?: number;
  comment?: string | null;
  is_completed?: boolean;
}

export interface WorkoutCompleteRequest {
  actual_duration_minutes?: number;
  comment?: string;
}

export interface WorkoutListResponse {
  items: Workout[];
  total: number;
}

export interface WorkoutFilters {
  year?: number;
  month?: number;
  date_from?: string;
  date_to?: string;
  sport_type?: SportType;
  is_completed?: boolean;
  skip?: number;
  limit?: number;
}

// ---- Competition ----

export interface Competition {
  id: number;
  user_id: number;
  sport_type: SportType;
  competition_type: CompetitionType;
  importance: CompetitionImportance;
  date: string;
  name: string;
  distance: number | null;
  created_at: string;
}

export interface CompetitionCreate {
  sport_type: SportType;
  competition_type: CompetitionType;
  importance: CompetitionImportance;
  date: string;
  name: string;
  distance?: number | null;
}

export interface CompetitionUpdate {
  sport_type?: SportType;
  competition_type?: CompetitionType;
  importance?: CompetitionImportance;
  date?: string;
  name?: string;
  distance?: number | null;
}

export interface CompetitionResultRequest {
  finish_time_seconds?: number;
  result_comment?: string;
}

export interface CompetitionListResponse {
  items: Competition[];
  total: number;
}

export interface CompetitionFilters {
  sport_type?: SportType;
  importance?: CompetitionImportance;
  date_from?: string;
  date_to?: string;
}

// ---- Training Plan ----

export interface TrainingPlan {
  id: number;
  user_id: number;
  sport_type: SportType;
  competition_id: number | null;
  target_date: string | null;
  weeks_count: number;
  preferred_days: number[];
  max_hours_per_week: number;
  is_active: boolean;
  created_at: string;
}

export type AthleteLevel = "beginner" | "intermediate" | "advanced";
export type TriathlonDistance = "sprint" | "olympic" | "half" | "full";

export interface PlanSettings {
  athlete_level?: AthleteLevel;
  distance_type?: TriathlonDistance | null;
  sessions_per_week?: number;
  swim_priority?: number;
  bike_priority?: number;
  run_priority?: number;
  long_run_pace?: number | null;
  swim_pace_min?: number | null;
  swim_pace_sec?: number | null;
  long_ride_speed?: number | null;
  include_strength?: boolean;
}

export interface PlanGenerateRequest {
  sport_type: SportType;
  competition_id?: number;
  preferred_days: number[];
  max_hours_per_week: number;
  settings?: PlanSettings;
}

export interface PlannedWorkoutSummary {
  id: number;
  sport_type: SportType;
  workout_type: WorkoutType | null;
  date: string;
  duration_minutes: number;
  is_completed: boolean;
  comment: string | null;
}

export interface WeeklyVolumeBreakdown {
  swimming: number;
  cycling: number;
  running: number;
  strength: number;
}

export interface PeriodWeek {
  week_number: number;
  start_date: string;
  end_date: string;
  is_recovery: boolean;
  total_minutes: number;
  volume: WeeklyVolumeBreakdown;
  workouts: PlannedWorkoutSummary[];
}

export interface PeriodDetail {
  name: string;
  label: string;
  start_date: string;
  end_date: string;
  weeks: PeriodWeek[];
  focus: string;
  intensity_pct: number;
  volume_pct: number;
}

export interface PlanDetailResponse extends TrainingPlan {
  periods: PeriodDetail[];
  total_workouts: number;
  preview_weeks: number;
  preview_total_hours: number;
}

// ---- API Responses ----

export interface ApiError {
  detail: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---- Analytics ----

export interface SportBreakdown {
  total_minutes: number;
  completed_minutes: number;
  total_workouts: number;
  completed_workouts: number;
}

export interface MonthlyStats {
  year: number;
  month: number;
  total_minutes: number;
  completed_minutes: number;
  total_workouts: number;
  completed_workouts: number;
  /** Completion rate computed only from workouts on/before today. */
  completion_rate: number;
  /** Counts used for completion_rate (past days only). */
  past_total_workouts: number;
  past_completed_workouts: number;
  by_sport: Partial<Record<SportType, SportBreakdown>>;
}

export interface DayStats {
  date: string;
  completed_minutes: number;
  planned_minutes: number;
  total_minutes: number;
}

export interface DailyStatsResponse {
  year: number;
  month: number;
  days: DayStats[];
  summary: MonthlyStats;
}

// ---- Calendar ----

export interface CalendarDay {
  date: string;
  workouts: Workout[];
  competitions: Competition[];
  is_current_month: boolean;
  is_today: boolean;
}
