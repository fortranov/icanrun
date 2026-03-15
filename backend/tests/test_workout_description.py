"""
Tests for workout_description.py — Friel-methodology description generator.

Covers:
  - All sport × workout-type combinations
  - Pace / speed zone calculations
  - Descriptions without pace data (fallback text)
  - Period label / week number footer appended correctly
  - Recovery week suffix
  - Formatting helpers (_fmt_run_pace, _fmt_swim_pace, _fmt_speed, _fmt_duration)
  - Zone boundary values
"""
import pytest

from app.services.workout_description import (
    CyclingZones,
    RunZones,
    SwimZones,
    _fmt_duration,
    _fmt_run_pace,
    _fmt_speed,
    _fmt_swim_pace,
    generate_workout_description,
)
from app.utils.enums import SportType, WorkoutType


# ---------------------------------------------------------------------------
# Formatter tests
# ---------------------------------------------------------------------------

class TestFmtRunPace:
    def test_exact_minutes(self):
        assert _fmt_run_pace(5.0) == "5:00/км"

    def test_half_minute(self):
        assert _fmt_run_pace(5.5) == "5:30/км"

    def test_quarter_minute(self):
        assert _fmt_run_pace(4.75) == "4:45/км"

    def test_single_digit_seconds(self):
        # 5:05 — seconds part must be zero-padded
        assert _fmt_run_pace(5.0 + 5 / 60) == "5:05/км"

    def test_six_minute_pace(self):
        assert _fmt_run_pace(6.0) == "6:00/км"


class TestFmtSwimPace:
    def test_two_ten(self):
        assert _fmt_swim_pace(130) == "2:10/100м"

    def test_one_thirty(self):
        assert _fmt_swim_pace(90) == "1:30/100м"

    def test_zero_padding(self):
        assert _fmt_swim_pace(125) == "2:05/100м"


class TestFmtSpeed:
    def test_round_number(self):
        assert _fmt_speed(30.0) == "30.0 км/ч"

    def test_fractional(self):
        assert _fmt_speed(28.5) == "28.5 км/ч"


class TestFmtDuration:
    def test_under_60_minutes(self):
        assert _fmt_duration(45) == "45мин"

    def test_exactly_60_minutes(self):
        assert _fmt_duration(60) == "1ч"

    def test_90_minutes(self):
        assert _fmt_duration(90) == "1ч 30мин"

    def test_120_minutes(self):
        assert _fmt_duration(120) == "2ч"

    def test_75_minutes(self):
        assert _fmt_duration(75) == "1ч 15мин"


# ---------------------------------------------------------------------------
# Zone calculator tests
# ---------------------------------------------------------------------------

class TestRunZones:
    def test_easy_is_one_minute_slower(self):
        z = RunZones(5.5)
        assert z.easy == pytest.approx(6.5)

    def test_aerobic_is_30sec_slower(self):
        z = RunZones(5.5)
        assert z.aerobic == pytest.approx(6.0)

    def test_threshold_is_15sec_faster(self):
        z = RunZones(5.5)
        assert z.threshold == pytest.approx(5.25)

    def test_interval_is_30sec_faster(self):
        z = RunZones(5.5)
        assert z.interval == pytest.approx(5.0)

    def test_easy_str_format(self):
        z = RunZones(5.5)
        assert z.easy_str == "6:30/км"

    def test_aerobic_str_format(self):
        z = RunZones(5.5)
        assert z.aerobic_str == "6:00/км"

    def test_threshold_str_format(self):
        z = RunZones(5.5)
        assert z.threshold_str == "5:15/км"

    def test_interval_str_format(self):
        z = RunZones(5.5)
        assert z.interval_str == "5:00/км"


class TestCyclingZones:
    def test_easy_85pct(self):
        z = CyclingZones(30.0)
        assert z.easy == pytest.approx(25.5)

    def test_aerobic_90pct(self):
        z = CyclingZones(30.0)
        assert z.aerobic == pytest.approx(27.0)

    def test_threshold_105pct(self):
        z = CyclingZones(30.0)
        assert z.threshold == pytest.approx(31.5)

    def test_interval_110pct(self):
        z = CyclingZones(30.0)
        assert z.interval == pytest.approx(33.0)

    def test_str_format(self):
        z = CyclingZones(28.0)
        assert z.aerobic_str == "25.2 км/ч"


class TestSwimZones:
    def test_easy_20sec_slower(self):
        z = SwimZones(120)  # 2:00/100m
        assert z.easy == 140

    def test_aerobic_10sec_slower(self):
        z = SwimZones(120)
        assert z.aerobic == 130

    def test_threshold_5sec_faster(self):
        z = SwimZones(120)
        assert z.threshold == 115

    def test_easy_str(self):
        z = SwimZones(120)
        assert z.easy_str == "2:20/100м"

    def test_aerobic_str(self):
        z = SwimZones(120)
        assert z.aerobic_str == "2:10/100м"

    def test_threshold_str(self):
        z = SwimZones(120)
        assert z.threshold_str == "1:55/100м"


# ---------------------------------------------------------------------------
# Running description tests
# ---------------------------------------------------------------------------

class TestRunningDescriptions:
    BASE_PACE = 5.5  # 5:30/km

    def test_recovery_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=45,
            long_run_pace=self.BASE_PACE,
        )
        assert "45мин" in desc
        assert "6:30/км" in desc        # easy zone = 5.5 + 1.0
        assert "зоны 2" in desc         # "не выше зоны 2" — genitive
        assert "восстановительный" in desc.lower()

    def test_recovery_without_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=45,
        )
        assert "45мин" in desc
        assert "зоны 2" in desc         # "не выше зоны 2" — genitive
        assert "/км" not in desc

    def test_aerobic_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=50,
            long_run_pace=self.BASE_PACE,
        )
        assert "50мин" in desc
        assert "6:00/км" in desc        # aerobic = 5.5 + 0.5
        assert "зона 2" in desc

    def test_long_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.LONG,
            duration_minutes=105,
            long_run_pace=self.BASE_PACE,
        )
        # Warm-up 15 + main 80 + cool-down 10 = 105
        # _fmt_duration(80) = "1ч 20мин", _fmt_duration(10) = "10мин"
        assert "15мин" in desc
        assert "1ч 20мин" in desc       # 80 min formatted
        assert "10мин" in desc
        assert "6:30/км" in desc        # easy pace
        assert "6:00/км" in desc        # aerobic pace
        assert "Разминка" in desc
        assert "заминка" in desc.lower()

    def test_long_without_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.LONG,
            duration_minutes=90,
        )
        assert "Разминка" in desc
        assert "заминка" in desc.lower()
        assert "/км" not in desc

    def test_threshold_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=50,
            long_run_pace=self.BASE_PACE,
        )
        # 15 warm-up + 25 main + 10 cool-down = 50
        assert "25мин" in desc
        assert "5:15/км" in desc        # threshold = 5.5 - 0.25
        assert "пороговом" in desc.lower()

    def test_threshold_without_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=50,
        )
        assert "зона 4" in desc
        assert "/км" not in desc

    def test_interval_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.INTERVAL,
            duration_minutes=60,
            long_run_pace=self.BASE_PACE,
        )
        # work block = 60 - 15 - 10 = 35 min → 35 // 7 = 5 reps
        assert "5×5мин" in desc
        assert "5:00/км" in desc        # interval = 5.5 - 0.5
        assert "трусцой" in desc

    def test_interval_rep_count_scales_with_duration(self):
        # Longer session = more reps
        desc_short = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.INTERVAL,
            duration_minutes=40,
            long_run_pace=self.BASE_PACE,
        )
        desc_long = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.INTERVAL,
            duration_minutes=70,
            long_run_pace=self.BASE_PACE,
        )
        # Extract rep count from "N×5мин"
        import re
        short_reps = int(re.search(r"(\d+)×5мин", desc_short).group(1))
        long_reps  = int(re.search(r"(\d+)×5мин", desc_long).group(1))
        assert long_reps > short_reps


# ---------------------------------------------------------------------------
# Cycling description tests
# ---------------------------------------------------------------------------

class TestCyclingDescriptions:
    BASE_SPEED = 28.0  # km/h

    def test_recovery_with_speed(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=60,
            long_ride_speed=self.BASE_SPEED,
        )
        # _fmt_duration(60) = "1ч"
        assert "1ч" in desc
        assert "23.8 км/ч" in desc      # 28.0 * 0.85
        assert "зона 1" in desc         # "зона 1–2"

    def test_recovery_without_speed(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=60,
        )
        assert "зона 1" in desc
        assert "км/ч" not in desc

    def test_long_with_speed(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.LONG,
            duration_minutes=120,
            long_ride_speed=self.BASE_SPEED,
        )
        assert "Разминка" in desc
        assert "25.2 км/ч" in desc      # aerobic = 28 * 0.90
        assert "23.8 км/ч" in desc      # easy = 28 * 0.85

    def test_threshold_with_speed(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            long_ride_speed=self.BASE_SPEED,
        )
        assert "29.4 км/ч" in desc      # 28 * 1.05
        assert "пороговой" in desc.lower()

    def test_interval_with_speed(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.INTERVAL,
            duration_minutes=60,
            long_ride_speed=self.BASE_SPEED,
        )
        assert "30.8 км/ч" in desc      # 28 * 1.10
        assert "×" in desc


# ---------------------------------------------------------------------------
# Swimming description tests
# ---------------------------------------------------------------------------

class TestSwimmingDescriptions:
    PACE_MIN = 2
    PACE_SEC = 0  # 2:00/100m = 120 seconds

    def test_recovery_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=45,
            swim_pace_min=self.PACE_MIN,
            swim_pace_sec=self.PACE_SEC,
        )
        assert "2:20/100м" in desc      # easy = 120 + 20 = 140 sec
        assert "зона 1" in desc

    def test_aerobic_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=45,
            swim_pace_min=self.PACE_MIN,
            swim_pace_sec=self.PACE_SEC,
        )
        assert "2:10/100м" in desc      # aerobic = 120 + 10 = 130 sec

    def test_threshold_with_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=60,
            swim_pace_min=self.PACE_MIN,
            swim_pace_sec=self.PACE_SEC,
        )
        assert "1:55/100м" in desc      # threshold = 120 - 5 = 115 sec

    def test_interval_uses_200m_reps(self):
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.INTERVAL,
            duration_minutes=60,
            swim_pace_min=self.PACE_MIN,
            swim_pace_sec=self.PACE_SEC,
        )
        assert "×200м" in desc
        assert "45 сек" in desc

    def test_long_structure(self):
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.LONG,
            duration_minutes=60,
            swim_pace_min=self.PACE_MIN,
            swim_pace_sec=self.PACE_SEC,
        )
        assert "Разминка" in desc
        assert "заминка" in desc.lower()

    def test_without_pace(self):
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=45,
        )
        assert "/100м" not in desc
        assert "аэробном" in desc.lower()

    def test_pace_only_min_no_sec_produces_no_zones(self):
        # Providing only minutes part without seconds = no zones (both required)
        desc = generate_workout_description(
            sport_type=SportType.SWIMMING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=45,
            swim_pace_min=2,
            swim_pace_sec=None,
        )
        assert "/100м" not in desc


# ---------------------------------------------------------------------------
# Strength description tests
# ---------------------------------------------------------------------------

class TestStrengthDescriptions:
    def test_structure(self):
        desc = generate_workout_description(
            sport_type=SportType.STRENGTH,
            workout_type=None,
            duration_minutes=60,
        )
        assert "Силовая тренировка" in desc
        assert "тренажёрном" in desc
        assert "10мин" in desc          # warm-up
        assert "40мин" in desc          # main block (60 - 10 - 10)
        assert "растяжка" in desc.lower()

    def test_exercise_list_mentioned(self):
        desc = generate_workout_description(
            sport_type=SportType.STRENGTH,
            workout_type=None,
            duration_minutes=60,
        )
        assert "приседания" in desc.lower()
        assert "тяга" in desc.lower()

    def test_different_duration(self):
        desc = generate_workout_description(
            sport_type=SportType.STRENGTH,
            workout_type=None,
            duration_minutes=75,
        )
        # main block = 75 - 10 - 10 = 55 min
        assert "55мин" in desc

    def test_pace_inputs_ignored_for_strength(self):
        # Strength description should never contain /км or км/ч even if passed
        desc = generate_workout_description(
            sport_type=SportType.STRENGTH,
            workout_type=None,
            duration_minutes=60,
            long_run_pace=5.5,
            long_ride_speed=28.0,
        )
        assert "/км" not in desc
        assert "км/ч" not in desc


# ---------------------------------------------------------------------------
# Triathlon description tests
# ---------------------------------------------------------------------------

class TestTriathlonDescriptions:
    def test_generic_description(self):
        desc = generate_workout_description(
            sport_type=SportType.TRIATHLON,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=60,
        )
        assert "триатлон" in desc.lower()
        assert "зона 2" in desc

    def test_duration_mentioned(self):
        desc = generate_workout_description(
            sport_type=SportType.TRIATHLON,
            workout_type=WorkoutType.LONG,
            duration_minutes=90,
        )
        assert "1ч 30мин" in desc


# ---------------------------------------------------------------------------
# Period label / week number footer tests
# ---------------------------------------------------------------------------

class TestPeriodFooter:
    def test_footer_appended(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=45,
            period_label="База 1",
            week_num=2,
        )
        assert "База 1 — неделя 2" in desc

    def test_recovery_week_suffix(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=40,
            period_label="Строительство 1",
            week_num=4,
            is_recovery_week=True,
        )
        assert "восст. неделя" in desc

    def test_no_recovery_suffix_when_false(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.RECOVERY,
            duration_minutes=40,
            period_label="База 2",
            week_num=1,
            is_recovery_week=False,
        )
        assert "восст. неделя" not in desc
        assert "База 2 — неделя 1" in desc

    def test_period_label_only_no_week_num(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=60,
            period_label="Пик",
        )
        assert "Пик" in desc
        assert "неделя" not in desc

    def test_no_footer_when_no_label(self):
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.AEROBIC,
            duration_minutes=45,
        )
        assert "неделя" not in desc
        assert "База" not in desc


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_very_short_session_does_not_crash(self):
        # Duration shorter than warm-up + cool-down; main block capped at 10 min
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.THRESHOLD,
            duration_minutes=20,
            long_run_pace=5.0,
        )
        assert desc  # non-empty

    def test_very_long_session(self):
        desc = generate_workout_description(
            sport_type=SportType.CYCLING,
            workout_type=WorkoutType.LONG,
            duration_minutes=300,
            long_ride_speed=25.0,
        )
        assert "4ч 35мин" in desc or "4ч" in desc  # 300 - 15 - 10 = 275 min = 4h 35min

    def test_interval_min_one_rep(self):
        # Barely enough time for intervals: should produce at least 1 rep
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=WorkoutType.INTERVAL,
            duration_minutes=27,  # 27 - 15 - 10 = 2 min work → 1 rep minimum
            long_run_pace=5.0,
        )
        assert "1×5мин" in desc

    def test_none_workout_type_running(self):
        # Falls through to the fallback aerobic description
        desc = generate_workout_description(
            sport_type=SportType.RUNNING,
            workout_type=None,
            duration_minutes=45,
            long_run_pace=5.5,
        )
        assert "Бег" in desc
        assert "аэробном" in desc.lower()
