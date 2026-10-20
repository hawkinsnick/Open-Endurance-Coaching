"""JSON command line. Raw athlete data is never uploaded by default."""

import argparse
import json
import sys
from xml.etree.ElementTree import ParseError
from defusedxml.common import DefusedXmlException
from fitdecode import FitError
from pathlib import Path
from .analysis import analyze, compare, drift, zones, lap_reports
from .importers import load_workout
from .workspace import Workspace
from .synthetic import export_examples
from .weather import enrich


def parser():
    p = argparse.ArgumentParser(description="Open Endurance Coaching engineering alpha")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("analyze", "compare", "drift", "zones", "laps", "weather"):
        cmd = sub.add_parser(name)
        cmd.add_argument("file", type=Path)
        if name in {"analyze", "drift", "zones"}:
            cmd.add_argument("--start", type=float, default=0)
            cmd.add_argument("--end", type=float)
        if name != "weather":
            cmd.add_argument("--max-gap", type=float, default=30)
        if name == "analyze":
            cmd.add_argument("--include-location", action="store_true")
        if name in {"zones", "drift"}:
            cmd.add_argument(
                "--channel",
                default="heart_rate_bpm" if name == "zones" else "speed_m_s",
            )
        if name == "zones":
            cmd.add_argument("--boundaries", type=float, nargs="+", required=True)
        if name == "compare":
            cmd.add_argument("--first", type=float, nargs=2, required=True)
            cmd.add_argument("--second", type=float, nargs=2, required=True)
        if name == "weather":
            cmd.add_argument("--cache", type=Path, required=True)
            cmd.add_argument("--allow-location-network", action="store_true")
    s = sub.add_parser("synthetic")
    s.add_argument("output", type=Path)
    for name in (
        "authorize",
        "ingest",
        "history",
        "history-compare",
        "weekly",
        "annotate",
        "revoke",
        "bind-alias",
        "find",
    ):
        s = sub.add_parser(name)
        s.add_argument("--workspace", type=Path, required=True)
        s.add_argument("--athlete", required=True)
        if name == "bind-alias":
            s.add_argument("--alias", required=True)
            s.add_argument("--timezone", required=True)
        if name == "find":
            s.add_argument("--day", required=True)
            s.add_argument("--sport", default="running")
        if name == "authorize":
            s.add_argument("--reference", required=True)
        if name == "ingest":
            s.add_argument("file", type=Path)
        if name == "annotate":
            s.add_argument("workout_id")
            s.add_argument("context_file", type=Path)
        if name == "history-compare":
            s.add_argument("first_id")
            s.add_argument("second_id")
    return p


def run(a):
    if a.command == "synthetic":
        return export_examples(a.output)
    if hasattr(a, "workspace"):
        ws = Workspace(a.workspace)
        if a.command == "bind-alias":
            from .discovery import bind_alias

            return bind_alias(ws, a.athlete, a.alias, a.timezone)
        if a.command == "find":
            from .discovery import find_workouts

            return find_workouts(ws, a.athlete, a.day, a.sport)
        if a.command == "authorize":
            return ws.authorize(a.athlete, a.reference)
        if a.command == "ingest":
            return ws.ingest(a.athlete, a.file)
        if a.command == "annotate":
            return ws.annotate(
                a.athlete, a.workout_id, json.loads(a.context_file.read_text())
            )
        if a.command == "weekly":
            return ws.weekly_totals(a.athlete)
        if a.command == "history":
            return ws.history(a.athlete)
        if a.command == "history-compare":
            return ws.compare_history(a.athlete, a.first_id, a.second_id)
        return ws.revoke(a.athlete)
    w = load_workout(a.file)
    if a.command == "analyze":
        return analyze(w, a.start, a.end, a.max_gap, a.include_location)
    if a.command == "compare":
        return compare(w, a.first, a.second, a.max_gap)
    if a.command == "drift":
        return drift(w, a.channel, a.start, a.end, a.max_gap)
    if a.command == "zones":
        return zones(w, a.channel, a.boundaries, a.start, a.end, a.max_gap)
    if a.command == "laps":
        return lap_reports(w, a.max_gap)
    return enrich(w, a.cache, a.allow_location_network)


def main():
    args = sys.argv[1:]
    # Preserve the scaffold's `oec file.csv` invocation.
    if (
        args
        and args[0]
        not in {
            "analyze",
            "compare",
            "drift",
            "zones",
            "laps",
            "weather",
            "synthetic",
            "authorize",
            "ingest",
            "history",
            "history-compare",
            "weekly",
            "annotate",
            "revoke",
            "bind-alias",
            "find",
        }
        and not args[0].startswith("-")
    ):
        args.insert(0, "analyze")
    p = parser()
    a = p.parse_args(args)
    try:
        print(json.dumps(run(a), indent=2, allow_nan=False))
    except (
        ValueError,
        OSError,
        PermissionError,
        KeyError,
        ParseError,
        DefusedXmlException,
        FitError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
