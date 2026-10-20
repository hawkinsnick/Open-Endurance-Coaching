from datetime import timedelta
import math
import pytest
from open_endurance_coaching.model import Sample, Workout
from open_endurance_coaching.synthetic import workout, ORIGIN
from open_endurance_coaching.analysis import (
    analyze,
    compare,
    drift,
    zones,
    intervals,
    lap_reports,
)


def w_at(times, values, **kwargs):
    return Workout(
        [
            Sample(ORIGIN + timedelta(seconds=t), heart_rate_bpm=v, **kwargs)
            for t, v in zip(times, values)
        ]
    )


def test_two_hour_known_answer():
    w = workout()
    r = analyze(w)
    assert r["elapsed_seconds"] == r["covered_seconds"] == 7200
    assert r["metrics"]["heart_rate_bpm"]["time_weighted_mean"] == 147
    assert r["distance"]["covered_distance_m"] == 21600
    c = compare(w, (0, 1800), (5400, 7200))
    assert c["change_second_minus_first"]["heart_rate_bpm"]["absolute_change"] == 14
    assert c["change_second_minus_first"]["heart_rate_bpm"][
        "percent_change"
    ] == pytest.approx(10)
    assert drift(w)["efficiency_decline_percent"] == pytest.approx(
        100 * (1 - 140 / 154)
    )


def test_irregular_weighting_and_clipping():
    w = w_at([0, 1, 10], [100, 200, 250])
    assert analyze(w)["metrics"]["heart_rate_bpm"]["time_weighted_mean"] == 190
    assert analyze(w, 0.5, 5)["metrics"]["heart_rate_bpm"][
        "time_weighted_mean"
    ] == pytest.approx(850 / 4.5)


def test_gaps_not_interpolated():
    r = analyze(w_at([0, 5, 100, 105], [100, 100, 200, 200]))
    assert r["covered_seconds"] == 10
    assert r["uncovered_active_seconds"] == 95
    assert r["metrics"]["heart_rate_bpm"]["coverage_fraction"] == pytest.approx(
        10 / 105
    )
    assert r["metrics"]["heart_rate_bpm"]["time_weighted_mean"] == 150


def test_missing_is_not_zero():
    r = analyze(w_at([0, 5, 10], [None, 100, 100], power_w=0))
    assert r["metrics"]["heart_rate_bpm"]["covered_seconds"] == 5
    assert r["metrics"]["power_w"]["time_weighted_mean"] == 0
    assert r["mechanical_work_kj"] == 0


def test_hr_zero_is_missing():
    assert Sample(ORIGIN, heart_rate_bpm=0).heart_rate_bpm is None


def test_timer_pause_clips_interval():
    w = w_at([0, 10, 20], [100, 200, 200], power_w=200)
    w.pauses = [(ORIGIN + timedelta(seconds=3), ORIGIN + timedelta(seconds=14))]
    r = analyze(w)
    assert r["expected_active_seconds"] == r["covered_seconds"] == 9
    assert r["metrics"]["heart_rate_bpm"]["time_weighted_mean"] == pytest.approx(
        1500 / 9
    )
    assert r["mechanical_work_kj"] == 1.8


def test_explicit_inactive_with_overlap():
    w = w_at([0, 10, 20], [100, 100, 100])
    w.samples[0].active = False
    w.pauses = [(ORIGIN + timedelta(seconds=5), ORIGIN + timedelta(seconds=15))]
    r = analyze(w)
    assert r["expected_active_seconds"] == r["covered_seconds"] == 5


def test_zone_boundaries_and_unknown_coverage():
    w = w_at([0, 5, 10, 15], [100, 150, None, 160])
    z = zones(w, "heart_rate_bpm", [100, 150])
    assert z["seconds"] == [0, 5, 5]
    assert z["covered_seconds"] == 10


@pytest.mark.parametrize("bounds", [[], [150, 100], [100, 100], [float("nan")], [-1]])
def test_invalid_zones(bounds):
    with pytest.raises(ValueError):
        zones(workout(), "heart_rate_bpm", bounds)


@pytest.mark.parametrize(
    "args",
    [
        (-1, 10, 30),
        (20, 10, 30),
        (0, 8000, 30),
        (0, 10, 0),
        (0, math.inf, 30),
        (0, 10, math.nan),
    ],
)
def test_invalid_windows(args):
    with pytest.raises(ValueError):
        analyze(workout(), *args)


def test_drift_refusals():
    assert drift(workout("brick"))["status"] == "unavailable"
    assert drift(workout(duration=300))["status"] == "unavailable"
    w = workout()
    for s in w.samples:
        s.heart_rate_bpm = None
    assert drift(w)["efficiency_decline_percent"] is None


def test_paired_drift_uses_same_intervals():
    w = workout(duration=1200, step=5)
    # Missing opposite channels must not produce independent means.
    for s in w.samples:
        elapsed = (s.timestamp - ORIGIN).total_seconds()
        if 0 <= elapsed < 60:
            s.speed_m_s = None
        if 600 <= elapsed < 660:
            s.heart_rate_bpm = None
    r = drift(w)
    assert r["status"] == "descriptive_only"
    assert r["halves"][0]["paired_seconds"] == r["halves"][1]["paired_seconds"] == 540


def test_distance_reset_does_not_add_negative_distance():
    w = w_at([0, 5, 10], [100] * 3)
    for s, d in zip(w.samples, [20, 0, 10]):
        s.distance_m = d
    r = analyze(w)
    assert r["distance"]["covered_distance_m"] == 10
    assert r["distance"]["covered_seconds"] == 5


def test_gps_jump_excluded():
    w = Workout(
        [
            Sample(ORIGIN, latitude=0, longitude=0),
            Sample(ORIGIN + timedelta(seconds=5), latitude=40, longitude=0),
        ]
    )
    assert analyze(w)["distance"]["covered_distance_m"] is None


def test_single_sample_and_empty_window():
    r = analyze(w_at([0], [140]))
    assert r["elapsed_seconds"] == 0
    assert r["metrics"] == {}
    assert analyze(workout(), 10, 10)["metrics"] == {}


def test_lap_reports_and_brick_segments():
    r = lap_reports(workout("brick"))
    assert {"cycling", "running", "transition"} <= {x["sport"] for x in r}
    assert all(x["report"]["elapsed_seconds"] >= 0 for x in r)


def test_bike_work_and_swim_distance():
    r = analyze(workout("bike"))
    assert r["mechanical_work_kj"] == 1440
    assert r["metrics"]["power_w"]["time_weighted_mean"] == 200
    assert analyze(workout("swim"))["distance"]["covered_distance_m"] == 7200


def test_integration_partition_invariant():
    w = workout("gaps")
    full = analyze(w)
    parts = [analyze(w, 0, 3711), analyze(w, 3711, 7200)]
    assert sum(x["covered_seconds"] for x in parts) == full["covered_seconds"]
    assert sum(x["distance"]["covered_distance_m"] for x in parts) == pytest.approx(
        full["distance"]["covered_distance_m"]
    )
    for a, b, lo, hi, dt in intervals(w):
        assert 0 < hi - lo <= dt <= 30


@pytest.mark.parametrize(
    "kw",
    [
        {"latitude": 91, "longitude": 0},
        {"latitude": 0},
        {"heart_rate_bpm": -1},
        {"power_w": math.nan},
        {"speed_m_s": math.inf},
        {"active": "false"},
    ],
)
def test_sample_validation(kw):
    with pytest.raises(ValueError):
        Sample(ORIGIN, **kw)


def test_order_and_duplicate():
    w = w_at([10, 0], [100, 200])
    assert w.samples[0].heart_rate_bpm == 200
    assert w.warnings
    with pytest.raises(ValueError):
        w_at([0, 0], [100, 200])


def test_native_swim_lengths():
    w = workout("swim", duration=120, step=5)
    w.metadata["sessions"] = [{"sport": "swimming", "pool_length_m": 25}]
    w.lengths = [
        {
            "start": ORIGIN.isoformat(),
            "end": (ORIGIN + timedelta(seconds=30)).isoformat(),
            "type": "active",
            "timer_seconds": 30,
            "strokes": 20,
        },
        {
            "start": (ORIGIN + timedelta(seconds=30)).isoformat(),
            "end": (ORIGIN + timedelta(seconds=60)).isoformat(),
            "type": "idle",
            "timer_seconds": 30,
            "strokes": 0,
        },
        {
            "start": (ORIGIN + timedelta(seconds=60)).isoformat(),
            "end": (ORIGIN + timedelta(seconds=90)).isoformat(),
            "type": "active",
            "timer_seconds": 30,
            "strokes": 21,
        },
    ]
    r = analyze(w)["pool_swim"]
    assert r["active_lengths"] == 2
    assert r["idle_lengths"] == 1
    assert r["pool_distance_m"] == 50
    assert r["pace_seconds_per_100m"] == 120
    assert r["recorded_strokes"] == 41
    assert analyze(w, 0, 45)["pool_swim"]["pool_distance_m"] == 25
    w.metadata["sessions"].append({"sport": "swimming", "pool_length_m": 50})
    assert analyze(w)["pool_swim"]["pool_distance_m"] is None
