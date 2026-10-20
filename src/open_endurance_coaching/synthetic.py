"""Original synthetic data with known answers; not athlete or device validation."""

import csv
import json
import struct
from pathlib import Path
from datetime import datetime, timedelta, timezone
from .model import Sample, Workout

ORIGIN = datetime(2025, 6, 1, 12, tzinfo=timezone.utc)


def workout(kind="run", duration=7200, step=5):
    if kind not in {"run", "bike", "swim", "brick", "gaps"}:
        raise ValueError("Unknown synthetic scenario")
    if duration < 1 or duration > 86400 or step < 1 or step > duration:
        raise ValueError("Choose 1 <= step <= duration <= 86400")
    samples = []
    for t in sorted(set(range(0, duration + 1, step)) | {duration}):
        if kind == "gaps" and 1800 < t < 2100:
            continue
        sport = "running"
        power = None
        speed, hr, cadence = 3.0, 140 if t < duration / 2 else 154, 170
        segment = "1"
        if kind == "bike":
            sport, speed, power, hr, cadence = (
                "cycling",
                8.0,
                150 if (t // 600) % 2 == 0 else 250,
                145,
                85,
            )
        elif kind == "swim":
            sport, speed, hr, cadence = "swimming", 1.0, 130, 30
        elif kind == "brick":
            if t < duration * 0.6:
                sport, speed, power, segment = "cycling", 8.0, 200, "bike"
            elif t < duration * 0.625:
                sport, speed, segment = "transition", 0.0, "t2"
            else:
                segment = "run"
        samples.append(
            Sample(
                ORIGIN + timedelta(seconds=t),
                heart_rate_bpm=hr,
                speed_m_s=speed,
                power_w=power,
                cadence_rpm=cadence,
                lap=str(t // 600 + 1),
                sport=sport,
                segment=segment,
                latitude=41.88 + t * 0.000001,
                longitude=-87.63,
                elevation_m=180.0,
                active=not (kind == "gaps" and 3600 <= t < 3660),
            )
        )
    return Workout(
        samples,
        source={"kind": "synthetic", "scenario": kind},
        warnings=["Synthetic fixture; no physiological validation"],
    )


def write_csv(w, path):
    from dataclasses import asdict

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(w.samples[0])))
        writer.writeheader()
        for sample in w.samples:
            row = asdict(sample)
            row["timestamp"] = sample.timestamp.isoformat()
            writer.writerow(row)


def fit_bytes(swim=False):
    """Small CRC-valid original FIT fixture: file_id, timer events, records, lap, session."""
    from fitdecode.utils import compute_crc

    data = bytearray()

    def define(local, global_id, fields):
        data.extend(struct.pack("<BBBHB", 0x40 | local, 0, 0, global_id, len(fields)))
        for field in fields:
            data.extend(bytes(field))

    def record(local, fmt, *values):
        data.extend(bytes([local]) + struct.pack("<" + fmt, *values))

    base = int((ORIGIN - datetime(1989, 12, 31, tzinfo=timezone.utc)).total_seconds())
    define(0, 0, [(0, 1, 0), (1, 2, 132), (4, 4, 134)])
    record(0, "BHI", 4, 255, base)
    define(1, 21, [(253, 4, 134), (0, 1, 0), (1, 1, 0)])
    record(1, "IBB", base, 0, 0)
    define(
        2,
        20,
        [
            (253, 4, 134),
            (3, 1, 2),
            (6, 2, 132),
            (7, 2, 132),
            (0, 4, 133),
            (1, 4, 133),
            (5, 4, 134),
        ],
    )
    for t in range(0, 61, 5):
        if t == 20:
            record(1, "IBB", base + t, 0, 1)
        if t == 30:
            record(1, "IBB", base + t, 0, 0)
        record(
            2,
            "IBH HiiI".replace(" ", ""),
            base + t,
            140,
            3000,
            200,
            round(41.88 * 2**31 / 180),
            round(-87.63 * 2**31 / 180),
            t * 300,
        )
    record(1, "IBB", base + 60, 0, 1)
    define(3, 19, [(253, 4, 134), (2, 4, 134)])
    record(3, "II", base + 60, base)
    if swim:
        define(
            5, 101, [(253, 4, 134), (2, 4, 134), (4, 4, 134), (5, 2, 132), (12, 1, 0)]
        )
        record(5, "IIIHB", base + 30, base, 30000, 20, 1)
        record(5, "IIIHB", base + 60, base + 30, 30000, 21, 1)
        define(4, 18, [(253, 4, 134), (2, 4, 134), (5, 1, 0), (44, 2, 132)])
        record(4, "IIBH", base + 60, base, 5, 2500)
    else:
        define(4, 18, [(253, 4, 134), (2, 4, 134), (5, 1, 0)])
        record(4, "IIB", base + 60, base, 1)
    header = struct.pack("<BBHI4s", 14, 0x20, 2160, len(data), b".FIT")
    header += struct.pack("<H", compute_crc(header))
    payload = header + data
    return payload + struct.pack("<H", compute_crc(payload))


def export_examples(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for kind in ("run", "bike", "swim", "brick", "gaps"):
        write_csv(workout(kind), folder / f"synthetic_{kind}.csv")
    (folder / "synthetic.fit").write_bytes(fit_bytes())
    points = "".join(
        f'<trkpt lat="41.88" lon="-87.63"><ele>180</ele><time>{(ORIGIN + timedelta(seconds=t)).isoformat()}</time></trkpt>'
        for t in (0, 5, 10)
    )
    (folder / "synthetic.gpx").write_text(
        f'<gpx version="1.1" creator="OEC synthetic" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>{points}</trkseg></trk></gpx>'
    )
    points = "".join(
        f'<Trackpoint><Time>{(ORIGIN + timedelta(seconds=t)).isoformat()}</Time><DistanceMeters>{t * 3}</DistanceMeters><HeartRateBpm><Value>140</Value></HeartRateBpm><Extensions><TPX xmlns="http://www.garmin.com/xmlschemas/ActivityExtension/v2"><Speed>3</Speed><Watts>200</Watts></TPX></Extensions></Trackpoint>'
        for t in (0, 5, 10)
    )
    (folder / "synthetic.tcx").write_text(
        f'<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"><Activities><Activity Sport="Running"><Lap StartTime="{ORIGIN.isoformat()}"><Track>{points}</Track></Lap></Activity></Activities></TrainingCenterDatabase>'
    )
    (folder / "expected.json").write_text(
        json.dumps(
            {
                "run": {
                    "elapsed_seconds": 7200,
                    "distance_m": 21600,
                    "heart_rate_mean": 147,
                    "first_30_min_hr": 140,
                    "last_30_min_hr": 154,
                    "efficiency_decline_percent": 100 * (1 - 140 / 154),
                },
                "fit": {"elapsed_seconds": 60, "active_seconds": 50, "work_kj": 10},
            },
            indent=2,
        )
    )
    return {
        "output": str(folder),
        "scenarios": 5,
        "formats": ["CSV", "FIT", "TCX", "GPX"],
        "kind": "synthetic_only",
    }
