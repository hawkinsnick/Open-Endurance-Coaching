"""Bounded, offline file ingestion. Unsupported information is never fabricated."""

import csv
import hashlib
from pathlib import Path
from datetime import timezone
from defusedxml import ElementTree as ET
from .model import CHANNELS, Sample, Workout, timestamp, sport_name

MAX_BYTES = 50 * 1024 * 1024
MAX_SAMPLES = 500_000


def _text(node, path):
    child = node.find(path)
    return None if child is None or child.text is None else child.text.strip()


def _value(node, path):
    t = _text(node, path)
    return None if t in (None, "") else float(t)


def _csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "timestamp" not in reader.fieldnames:
            raise ValueError("CSV requires timestamp column")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Duplicate CSV columns")
        rows = []
        unknown = (
            set(reader.fieldnames)
            - set(CHANNELS)
            - {"timestamp", "lap", "sport", "active", "segment"}
        )
        for line, raw in enumerate(reader, 2):
            try:
                if None in raw:
                    raise ValueError("extra CSV cells")
                values = {k: float(raw[k]) for k in CHANNELS if raw.get(k, "").strip()}
                active = raw.get("active", "true").strip().lower()
                if active not in {"true", "false", "1", "0"}:
                    raise ValueError("active must be true/false/1/0")
                rows.append(
                    Sample(
                        raw["timestamp"],
                        **values,
                        active=active in {"true", "1"},
                        lap=raw.get("lap") or "1",
                        sport=raw.get("sport") or "unknown",
                        segment=raw.get("segment") or "1",
                    )
                )
                if len(rows) > MAX_SAMPLES:
                    raise ValueError("too many samples")
            except (ValueError, TypeError, AttributeError) as e:
                raise ValueError(f"Invalid CSV line {line}: {e}") from e
    return Workout(
        rows,
        warnings=[f"Ignored CSV columns: {', '.join(sorted(unknown))}"]
        if unknown
        else [],
    )


def _gpx(path):
    root = ET.parse(path).getroot()
    if root.tag.split("}")[-1] != "gpx":
        raise ValueError("Expected GPX root")
    rows = []
    for seg_i, seg in enumerate(root.findall("./{*}trk/{*}trkseg"), 1):
        for p in seg.findall("{*}trkpt"):
            t = _text(p, "{*}time")
            if not t:
                raise ValueError(
                    "GPX trackpoint lacks time; route-only files cannot be analyzed"
                )
            rows.append(
                Sample(
                    t,
                    latitude=float(p.attrib["lat"]),
                    longitude=float(p.attrib["lon"]),
                    elevation_m=_value(p, "{*}ele"),
                    heart_rate_bpm=_value(p, ".//{*}TrackPointExtension/{*}hr"),
                    cadence_rpm=_value(p, ".//{*}TrackPointExtension/{*}cad"),
                    segment=str(seg_i),
                )
            )
    return Workout(
        rows,
        warnings=[
            "GPX sport unknown; no speed or power inferred from absent channels",
            "Track segment boundaries are excluded from integration",
        ],
    )


def _tcx(path):
    root = ET.parse(path).getroot()
    if root.tag.split("}")[-1] != "TrainingCenterDatabase":
        raise ValueError("Expected TrainingCenterDatabase root")
    rows, track_i = [], 0
    activities = root.findall("./{*}Activities/{*}Activity")
    for activity_i, activity in enumerate(activities, 1):
        sport = sport_name(activity.attrib.get("Sport", "unknown"))
        for lap_i, lap in enumerate(activity.findall("{*}Lap"), 1):
            for track in lap.findall("{*}Track"):
                track_i += 1
                for p in track.findall("{*}Trackpoint"):
                    t = _text(p, "{*}Time")
                    if not t:
                        raise ValueError("TCX trackpoint lacks Time")
                    cadence = _value(p, "{*}Cadence")
                    run_cadence = _value(p, ".//{*}TPX/{*}RunCadence")
                    # RunCadence is strides/min; preserve device convention, never silently double.
                    if cadence is None and run_cadence is not None:
                        cadence = run_cadence
                    rows.append(
                        Sample(
                            t,
                            heart_rate_bpm=_value(p, "{*}HeartRateBpm/{*}Value"),
                            latitude=_value(p, "{*}Position/{*}LatitudeDegrees"),
                            longitude=_value(p, "{*}Position/{*}LongitudeDegrees"),
                            power_w=_value(p, ".//{*}TPX/{*}Watts"),
                            speed_m_s=_value(p, ".//{*}TPX/{*}Speed"),
                            distance_m=_value(p, "{*}DistanceMeters"),
                            elevation_m=_value(p, "{*}AltitudeMeters"),
                            cadence_rpm=cadence,
                            lap=f"{activity_i}:{lap_i}",
                            sport=sport,
                            segment=str(track_i),
                        )
                    )
    return Workout(
        rows,
        warnings=[
            "TCX track boundaries excluded; exact timer pauses may be unavailable"
        ],
        metadata={
            "running_cadence": "RunCadence is strides/min; Cadence retained as supplied; conventions differ across devices"
        },
    )


def _fit(path):
    import fitdecode

    rows, pauses, lengths, warnings, sessions, laps = [], [], [], [], [], []
    stopped = None
    with fitdecode.FitReader(
        str(path),
        check_crc=fitdecode.CrcCheck.RAISE,
        error_handling=fitdecode.ErrorHandling.RAISE,
    ) as fit:
        for frame in fit:
            if frame.frame_type != fitdecode.FIT_FRAME_DATA:
                continue
            d = {
                f.name: f.value
                for f in frame.fields
                if not isinstance(f.field, fitdecode.types.DevField)
            }
            name = frame.name
            t = d.get("timestamp")
            if t is not None:
                # FIT date_time fields are UTC even when decoder returns naive datetime.
                t = timestamp(t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t)
            if name == "record":
                if t is None:
                    raise ValueError("FIT record without timestamp")
                v = {}
                for src, dst in {
                    "heart_rate": "heart_rate_bpm",
                    "power": "power_w",
                    "distance": "distance_m",
                    "cadence": "cadence_rpm",
                }.items():
                    v[dst] = d.get(src)
                v["speed_m_s"] = (
                    d.get("enhanced_speed")
                    if d.get("enhanced_speed") is not None
                    else d.get("speed")
                )
                v["elevation_m"] = (
                    d.get("enhanced_altitude")
                    if d.get("enhanced_altitude") is not None
                    else d.get("altitude")
                )
                for src, dst in [
                    ("position_lat", "latitude"),
                    ("position_long", "longitude"),
                ]:
                    v[dst] = d.get(src)
                    if v[dst] is not None:
                        v[dst] *= 180 / 2**31
                rows.append(Sample(t, **v))
            elif name == "event" and d.get("event") == "timer" and t:
                event = d.get("event_type")
                if (
                    event in {"stop", "stop_all", "stop_disable", "stop_disable_all"}
                    and stopped is None
                ):
                    stopped = t
                elif event == "start" and stopped is not None:
                    if t > stopped:
                        pauses.append((stopped, t))
                    stopped = None
            elif name == "session":
                sessions.append(
                    {
                        "start": d.get("start_time"),
                        "end": t,
                        "sport": sport_name(d.get("sport", "unknown")),
                        "pool_length_m": d.get("pool_length"),
                    }
                )
            elif name == "lap":
                laps.append((d.get("start_time"), t))
            elif name == "length":
                lengths.append(
                    {
                        "start": str(d.get("start_time")),
                        "end": t.isoformat() if t else None,
                        "timer_seconds": d.get("total_timer_time"),
                        "strokes": d.get("total_strokes"),
                        "type": str(d.get("length_type")),
                        "stroke": str(d.get("swim_stroke")),
                    }
                )
            if len(rows) > MAX_SAMPLES:
                raise ValueError("too many samples")
    if not rows:
        raise ValueError(
            "FIT has no timestamped records; length-only swim files are not supported in this alpha"
        )

    def utc(v):
        return timestamp(v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v)

    for row in rows:
        if sessions and row.timestamp == sessions[-1]["end"]:
            row.sport, row.segment = sessions[-1]["sport"], str(len(sessions))
        if laps and row.timestamp == laps[-1][1]:
            row.lap = str(len(laps))
        for i, s in enumerate(sessions, 1):
            if s["start"] and s["end"] and utc(s["start"]) <= row.timestamp < s["end"]:
                row.sport, row.segment = s["sport"], str(i)
                break
        for i, (a, b) in enumerate(laps, 1):
            if a and b and utc(a) <= row.timestamp < b:
                row.lap = str(i)
                break
    if stopped and stopped < rows[-1].timestamp:
        pauses.append((stopped, rows[-1].timestamp))
    warnings.extend(
        [
            "FIT developer fields are not interpreted",
            "FIT cadence retained as device cycles/min; do not compare across devices without cadence convention",
        ]
    )
    # Re-run normalization after attaching session sport.
    for row in rows:
        row.__post_init__()
    return Workout(
        rows,
        warnings=warnings,
        pauses=pauses,
        lengths=lengths,
        metadata={
            "sessions": [
                {**s, "start": str(s["start"]), "end": str(s["end"])} for s in sessions
            ]
        },
    )


def load_workout(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Workout exceeds 50 MiB input limit")
    parser = {".csv": _csv, ".gpx": _gpx, ".tcx": _tcx, ".fit": _fit}.get(
        path.suffix.lower()
    )
    if parser is None:
        raise ValueError("Supported formats: CSV, GPX, TCX, FIT")
    w = parser(path)
    if len(w.samples) > MAX_SAMPLES:
        raise ValueError("too many samples")
    w.source = {
        "format": path.suffix[1:].lower(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "parser": "open-endurance-coaching/0.8.0a1",
    }
    return w
