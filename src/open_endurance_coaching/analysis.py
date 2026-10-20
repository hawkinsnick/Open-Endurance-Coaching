"""CSV ingestion and deterministic, non-diagnostic workout summaries."""
import csv
from datetime import datetime
from math import isfinite

NUMERIC = ("heart_rate_bpm", "power_w", "speed_m_s", "latitude", "longitude", "elevation_m", "cadence_rpm")
RANGES = {"heart_rate_bpm": (0, 250), "power_w": (0, 2500), "speed_m_s": (0, 35), "latitude": (-90, 90), "longitude": (-180, 180), "cadence_rpm": (0, 250)}

def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "timestamp" not in reader.fieldnames:
            raise ValueError("CSV requires timestamp column")
        rows = []
        for line, raw in enumerate(reader, 2):
            try:
                t = datetime.fromisoformat(raw["timestamp"].replace("Z", "+00:00"))
                if t.tzinfo is None or t.utcoffset() is None:
                    raise ValueError("timestamp requires UTC offset")
                row = {"timestamp": t}
                for field in NUMERIC:
                    val = raw.get(field, "")
                    row[field] = None if val is None or val.strip() == "" else float(val)
                    if row[field] is not None:
                        if not isfinite(row[field]):
                            raise ValueError(f"non-finite {field}")
                        if field in RANGES and not (RANGES[field][0] <= row[field] <= RANGES[field][1]):
                            raise ValueError(f"out-of-range {field}")
                rows.append(row)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid CSV line {line}: {e}") from e
    if not rows:
        raise ValueError("Workout contains no samples")
    rows.sort(key=lambda r: r["timestamp"])
    if any(b["timestamp"] <= a["timestamp"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Duplicate or non-increasing timestamps")
    return rows

def summarize(rows):
    elapsed = (rows[-1]["timestamp"] - rows[0]["timestamp"]).total_seconds()
    if elapsed < 0:
        raise ValueError("Negative elapsed time")
    result = {"samples": len(rows), "elapsed_seconds": elapsed, "metrics": {}, "warnings": []}
    for field in NUMERIC:
        values = [r[field] for r in rows if r.get(field) is not None]
        if values:
            result["metrics"][field] = {"sample_mean": sum(values) / len(values), "observations": len(values)}
            if len(values) != len(rows):
                result["warnings"].append(f"Missing {field} in {len(rows)-len(values)} samples")
    result["warnings"].append("Means are sample-weighted, not time-weighted; not suitable for irregular sampling without resampling")
    result["warnings"].append("Elapsed time is not moving time")
    return result
