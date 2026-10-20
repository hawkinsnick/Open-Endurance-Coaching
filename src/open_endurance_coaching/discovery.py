"""Coach roster and calendar lookup over authorized local workouts, never Strava APIs."""

import json
import unicodedata
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from .model import timestamp, sport_name
from .workspace import identifier

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def alias_key(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        raise ValueError("Alias must contain 1-100 characters")
    return unicodedata.normalize("NFKC", value).strip().casefold()


def day_window(expression, timezone_name, now=None):
    zone = ZoneInfo(timezone_name)
    now = timestamp(now or datetime.now(timezone.utc))
    today = now.astimezone(zone).date()
    value = expression.strip().lower()
    rule = "explicit_calendar_date"
    if value == "today":
        selected, rule = today, "today_in_athlete_timezone"
    elif value == "yesterday":
        selected, rule = (
            today - timedelta(days=1),
            "previous_calendar_day_in_athlete_timezone",
        )
    elif value in WEEKDAYS or value.startswith("last ") and value[5:] in WEEKDAYS:
        strict = value.startswith("last ")
        weekday = WEEKDAYS.index(value[5:] if strict else value)
        delta = (today.weekday() - weekday) % 7
        if strict and delta == 0:
            delta = 7
        selected = today - timedelta(days=delta)
        rule = (
            "most_recent_weekday_strictly_before_today"
            if strict
            else "most_recent_weekday_including_today"
        )
    else:
        try:
            selected = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "Use YYYY-MM-DD, today, yesterday, a weekday, or last weekday; clarify other phrases"
            ) from exc
    start = datetime.combine(selected, time.min, tzinfo=zone)
    end = datetime.combine(selected + timedelta(days=1), time.min, tzinfo=zone)
    return {
        "local_date": selected.isoformat(),
        "timezone": timezone_name,
        "resolution_rule": rule,
        "start_utc": start.astimezone(timezone.utc).isoformat(),
        "end_utc": end.astimezone(timezone.utc).isoformat(),
        "duration_seconds": (
            end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
        ).total_seconds(),
    }


def _roster_path(ws):
    return ws._file(ws.root, "roster.json")


def bind_alias(ws, athlete_id, alias, timezone_name):
    ws._authorized(athlete_id)
    ZoneInfo(timezone_name)
    key = alias_key(alias)
    path = _roster_path(ws)
    roster = json.loads(path.read_text()) if path.exists() else []
    roster = [
        x
        for x in roster
        if not (x["athlete_id"] == athlete_id and x["alias_key"] == key)
    ]
    roster.append(
        {"athlete_id": athlete_id, "alias_key": key, "timezone": timezone_name}
    )
    ws._write(path, json.dumps(roster))
    return {
        "athlete_id": athlete_id,
        "alias": alias,
        "timezone": timezone_name,
        "source": "local_roster",
    }


def find_workouts(ws, athlete_alias, day, sport="running", now=None, athlete_id=None):
    path = _roster_path(ws)
    roster = json.loads(path.read_text()) if path.exists() else []
    key = alias_key(athlete_alias)
    entries = []
    for entry in roster:
        if entry["alias_key"] != key or (
            athlete_id is not None and entry["athlete_id"] != identifier(athlete_id)
        ):
            continue
        try:
            ws._authorized(entry["athlete_id"])
        except PermissionError:
            continue
        entries.append(entry)
    if not entries:
        return {
            "status": "athlete_not_found",
            "source": "authorized_local_workspace",
            "message": "No authorized athlete matches this alias; connect/import or clarify identity",
        }
    unique = {entry["athlete_id"] for entry in entries}
    if len(unique) > 1:
        return {
            "status": "ambiguous_athlete",
            "candidates": sorted(unique),
            "message": "Choose an athlete ID; no workout selected",
        }
    entry = entries[0]
    window = day_window(day, entry["timezone"], now)
    desired = sport_name(sport)
    if desired not in {"running", "cycling", "swimming", "transition"}:
        raise ValueError("Choose running/cycling/swimming/transition")
    matches = []
    for item in ws.history(entry["athlete_id"]):
        t = timestamp(item["start_utc"])
        if (
            timestamp(window["start_utc"]) <= t < timestamp(window["end_utc"])
            and desired in item["report"]["sports"]
        ):
            r = item["report"]
            matches.append(
                {
                    "workout_id": item["workout_id"],
                    "start_local": t.astimezone(
                        ZoneInfo(entry["timezone"])
                    ).isoformat(),
                    "elapsed_seconds": r["elapsed_seconds"],
                    "sports": r["sports"],
                    "multisport": len(r["sports"]) > 1,
                    "source_sha256": r["source"]["sha256"],
                }
            )
    return {
        "status": "matched"
        if len(matches) == 1
        else "ambiguous_workout"
        if matches
        else "workout_not_found",
        "athlete_id": entry["athlete_id"],
        "date_resolution": window,
        "sport_requested": desired,
        "candidates": matches,
        "source": "authorized_local_workspace",
        "live_platform_fetch": False,
        "message": "Select among multiple matches; never guess. Multisport candidates require a run-segment selection.",
    }
