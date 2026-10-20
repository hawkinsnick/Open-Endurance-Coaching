from datetime import datetime, timezone, timedelta
import pytest
from open_endurance_coaching.synthetic import workout, write_csv
from open_endurance_coaching.workspace import Workspace
from open_endurance_coaching.discovery import bind_alias, find_workouts, day_window

NOW = datetime(2025, 6, 2, 1, tzinfo=timezone.utc)  # Sunday evening in Chicago


def test_bobs_sunday_run(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.authorize("athlete01", "synthetic")
    file = tmp_path / "run.csv"
    write_csv(workout(), file)
    wid = ws.ingest("athlete01", file)["workout_id"]
    bind_alias(ws, "athlete01", "Bob", "America/Chicago")
    r = find_workouts(ws, "bob", "Sunday", "run", NOW)
    assert r["status"] == "matched"
    assert r["candidates"][0]["workout_id"] == wid
    assert r["date_resolution"]["local_date"] == "2025-06-01"
    assert r["date_resolution"]["timezone"] == "America/Chicago"
    assert r["live_platform_fetch"] is False
    assert r["source"] == "authorized_local_workspace"
    assert (
        find_workouts(ws, "Bob", "Sunday", "swim", NOW)["status"] == "workout_not_found"
    )
    assert (
        find_workouts(ws, "Robert", "Sunday", "run", NOW)["status"]
        == "athlete_not_found"
    )
    ws.revoke("athlete01")
    assert (
        find_workouts(ws, "Bob", "Sunday", "run", NOW)["status"] == "athlete_not_found"
    )
    assert "bob" not in (ws.root / "roster.json").read_text()


def test_duplicate_bobs_and_runs_are_not_guessed(tmp_path):
    ws = Workspace(tmp_path / "ws")
    f = tmp_path / "run.csv"
    write_csv(workout(), f)
    for aid in ["a", "b"]:
        ws.authorize(aid, "synthetic")
        bind_alias(ws, aid, "Bob", "America/Chicago")
        ws.ingest(aid, f)
    assert (
        find_workouts(ws, "Bob", "Sunday", "run", NOW)["status"] == "ambiguous_athlete"
    )
    assert (
        find_workouts(ws, "Bob", "Sunday", "run", NOW, athlete_id="a")["status"]
        == "matched"
    )
    w = workout()
    for s in w.samples:
        s.timestamp += timedelta(hours=4)
    write_csv(w, f)
    ws.ingest("a", f)
    assert (
        find_workouts(ws, "Bob", "Sunday", "run", NOW, athlete_id="a")["status"]
        == "ambiguous_workout"
    )


def test_daylight_saving_calendar_windows():
    assert day_window("2026-03-08", "America/Chicago")["duration_seconds"] == 23 * 3600
    assert day_window("2026-11-01", "America/Chicago")["duration_seconds"] == 25 * 3600
    # UTC Monday, local Sunday: never choose a day using UTC weekday alone.
    assert day_window("Sunday", "America/Chicago", NOW)["local_date"] == "2025-06-01"
    assert (
        day_window("last Sunday", "America/Chicago", NOW)["local_date"] == "2025-05-25"
    )
    assert day_window("yesterday", "America/Chicago", NOW)["local_date"] == "2025-05-31"
    with pytest.raises(ValueError):
        day_window("this Sunday", "America/Chicago", NOW)


def test_alias_requires_consent(tmp_path):
    ws = Workspace(tmp_path)
    with pytest.raises(PermissionError):
        bind_alias(ws, "a", "Bob", "America/Chicago")
