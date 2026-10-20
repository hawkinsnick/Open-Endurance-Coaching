"""Deterministic interval analytics; left-held values, bounded interpolation horizon."""

from math import sqrt, isfinite
from .model import CHANNELS, Workout, Sample, haversine
from . import __version__


def load_csv(path):
    """Compatibility API: load the original CSV into dictionaries."""
    from .importers import load_workout

    return [vars(s).copy() for s in load_workout(path).samples]


def summarize(rows):
    """Compatibility API: preserve the explicitly labeled v0.1 sample means."""
    w = Workout([Sample(**r) for r in rows])
    out = {
        "samples": len(rows),
        "elapsed_seconds": (
            w.samples[-1].timestamp - w.samples[0].timestamp
        ).total_seconds(),
        "metrics": {},
        "warnings": [
            "Means are sample-weighted, not time-weighted",
            "Elapsed time is not moving time",
        ],
    }
    for k in CHANNELS:
        vals = [getattr(s, k) for s in w.samples if getattr(s, k) is not None]
        if vals:
            out["metrics"][k] = {
                "sample_mean": sum(vals) / len(vals),
                "observations": len(vals),
            }
    return out


def _config(w, start, end, max_gap):
    total = (w.samples[-1].timestamp - w.samples[0].timestamp).total_seconds()
    end = total if end is None else end
    if not all(isfinite(v) for v in (start, end, max_gap)) or max_gap <= 0:
        raise ValueError("Finite bounds and a positive max_gap are required")
    if not 0 <= start <= end <= total:
        raise ValueError(f"Window must satisfy 0 <= start <= end <= {total}")
    return total, end


def intervals(w, start=0.0, end=None, max_gap=30.0):
    """Yield clipped, active intervals. Long gaps and segment crossings are excluded."""
    _, end = _config(w, start, end, max_gap)
    origin = w.samples[0].timestamp
    pauses = [
        ((a - origin).total_seconds(), (b - origin).total_seconds())
        for a, b in w.pauses
    ]
    for a, b in zip(w.samples, w.samples[1:]):
        x, y = (
            (a.timestamp - origin).total_seconds(),
            (b.timestamp - origin).total_seconds(),
        )
        if (
            y - x > max_gap
            or a.segment != b.segment
            or a.sport != b.sport
            or not a.active
        ):
            continue
        lo, hi = max(start, x), min(end, y)
        if hi <= lo:
            continue
        pieces = [(lo, hi)]
        for p, q in pauses:
            pieces = [
                (left, right)
                for u, v in pieces
                for left, right in [(u, min(v, p)), (max(u, q), v)]
                if right > left
            ]
        for lo, hi in pieces:
            yield a, b, lo, hi, y - x


def _expected_active(w, start, end):
    origin = w.samples[0].timestamp
    paused = sum(
        max(
            0,
            min(end, (b - origin).total_seconds())
            - max(start, (a - origin).total_seconds()),
        )
        for a, b in w.pauses
    )
    # Explicit sample-level active=false intervals, excluding timer-pause overlap.
    for a, b in zip(w.samples, w.samples[1:]):
        if not a.active:
            x, y = (
                max(start, (a.timestamp - origin).total_seconds()),
                min(end, (b.timestamp - origin).total_seconds()),
            )
            if y > x:
                overlap = sum(
                    max(
                        0,
                        min(y, (q - origin).total_seconds())
                        - max(x, (p - origin).total_seconds()),
                    )
                    for p, q in w.pauses
                )
                paused += y - x - overlap
    return max(0.0, end - start - paused)


def analyze(w, start=0.0, end=None, max_gap=30.0, include_location=False):
    _, end = _config(w, start, end, max_gap)
    expected = _expected_active(w, start, end)
    accum = {
        k: [0.0, 0.0, 0.0, None, None]
        for k in CHANNELS
        if k not in {"latitude", "longitude", "distance_m"}
    }
    covered, moving, distance, distance_seconds, ascent, elevation_seconds = (
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    )
    distance_sources, warnings = set(), list(w.warnings)
    for a, b, lo, hi, raw_dt in intervals(w, start, end, max_gap):
        dt = hi - lo
        covered += dt
        for k, stats in accum.items():
            v = getattr(a, k)
            if v is not None:
                stats[0] += v * dt
                stats[1] += dt
                stats[2] += v * v * dt
                stats[3] = v if stats[3] is None else min(stats[3], v)
                stats[4] = v if stats[4] is None else max(stats[4], v)
        if a.speed_m_s is not None and a.speed_m_s > 0.5:
            moving += dt
        delta = None
        if a.distance_m is not None and b.distance_m is not None:
            delta = b.distance_m - a.distance_m
            if delta < 0:
                warnings.append("Device distance reset; interval omitted from distance")
                delta = None
            else:
                distance_sources.add("device_distance_delta")
        elif a.speed_m_s is not None:
            delta = a.speed_m_s * raw_dt
            distance_sources.add("left_held_speed")
        elif a.latitude is not None and b.latitude is not None:
            delta = haversine(a.latitude, a.longitude, b.latitude, b.longitude)
            if delta / raw_dt > 100:
                warnings.append("GPS jump above 100 m/s excluded from distance")
                delta = None
            else:
                distance_sources.add("gps_haversine_estimate")
        if delta is not None:
            distance += delta * dt / raw_dt
            distance_seconds += dt
        if a.elevation_m is not None and b.elevation_m is not None:
            ascent += max(0, b.elevation_m - a.elevation_m) * dt / raw_dt
            elevation_seconds += dt
        if a.heart_rate_bpm is not None and a.heart_rate_bpm > 250:
            warnings.append("Heart rate above 250 bpm: inspect sensor data")
    metrics = {}
    for k, (integral, seconds, squares, minimum, maximum) in accum.items():
        if seconds:
            mean = integral / seconds
            metrics[k] = {
                "time_weighted_mean": mean,
                "unit": CHANNELS[k],
                "covered_seconds": seconds,
                "coverage_fraction": seconds / expected if expected else None,
                "minimum": minimum,
                "maximum": maximum,
                "coefficient_of_variation": sqrt(
                    max(0, squares / seconds - mean * mean)
                )
                / mean
                if mean
                else None,
            }
    if expected - covered > 1e-7:
        warnings.append(
            "Uncovered active time: gaps or segment boundaries; excluded from integration"
        )
    warnings += [
        "Left-held samples; no extrapolation beyond final sample; gaps above max_gap excluded",
        "Moving estimate uses recorded speed >0.5 m/s; missing speed is not inferred movement",
        "Ascent is unsmoothed positive elevation change and may reflect sensor noise",
        "Observed associations do not establish fatigue, dehydration, heat effects, or causation",
    ]
    result = {
        "schema_version": "1.0",
        "engine_version": __version__,
        "source": w.source,
        "window": {
            "start_seconds": start,
            "end_seconds": end,
            "time_basis": "elapsed_from_first_sample",
        },
        "method": {"integration": "left_rectangle", "max_gap_seconds": max_gap},
        "elapsed_seconds": end - start,
        "expected_active_seconds": expected,
        "covered_seconds": covered,
        "uncovered_active_seconds": max(0, expected - covered),
        "moving_estimate_seconds": moving,
        "metrics": metrics,
        "distance": {
            "covered_distance_m": distance if distance_seconds else None,
            "covered_seconds": distance_seconds,
            "methods": sorted(distance_sources),
        },
        "ascent_unsmoothed_m": ascent if elevation_seconds else None,
        "elevation_covered_seconds": elevation_seconds,
        "mechanical_work_kj": accum["power_w"][0] / 1000
        if accum["power_w"][1]
        else None,
        "sports": sorted(
            {
                s.sport
                for s in w.samples
                if start <= (s.timestamp - w.samples[0].timestamp).total_seconds() < end
            }
        ),
        "warnings": sorted(set(warnings)),
        "swim_lengths": w.lengths,
        "metadata": w.metadata,
        "quality": {
            "sample_count": len(w.samples),
            "present_channels": [
                k for k in CHANNELS if any(getattr(s, k) is not None for s in w.samples)
            ],
            "missing_sample_counts": {
                k: sum(getattr(s, k) is None for s in w.samples) for k in CHANNELS
            },
            "scope": "whole input; metric coverage above is window-specific",
        },
    }
    from .swim import summarize_lengths

    result["pool_swim"] = summarize_lengths(w, start, end)
    if include_location:
        result["route"] = [
            {
                "timestamp": s.timestamp.isoformat(),
                "latitude": s.latitude,
                "longitude": s.longitude,
            }
            for s in w.samples
            if s.latitude is not None
            and start <= (s.timestamp - w.samples[0].timestamp).total_seconds() <= end
        ]
    return result


def zones(w, channel, boundaries, start=0.0, end=None, max_gap=30.0):
    if channel not in {"heart_rate_bpm", "power_w", "speed_m_s"}:
        raise ValueError("Zones require heart_rate_bpm, power_w, or speed_m_s")
    if (
        not boundaries
        or any(not isfinite(b) or b < 0 for b in boundaries)
        or any(b <= a for a, b in zip(boundaries, boundaries[1:]))
    ):
        raise ValueError(
            "Zone boundaries must be finite, nonnegative and strictly increasing"
        )
    seconds = [0.0] * (len(boundaries) + 1)
    for a, _, lo, hi, _ in intervals(w, start, end, max_gap):
        v = getattr(a, channel)
        if v is not None:
            seconds[sum(v >= b for b in boundaries)] += hi - lo
    return {
        "channel": channel,
        "unit": CHANNELS[channel],
        "boundaries": boundaries,
        "rule": "lower inclusive, upper exclusive",
        "seconds": seconds,
        "covered_seconds": sum(seconds),
        "threshold_source": "coach_supplied_absolute_boundaries",
    }


def compare(w, first, second, max_gap=30.0):
    reports = [analyze(w, *window, max_gap) for window in (first, second)]
    delta = {}
    for k in reports[0]["metrics"].keys() & reports[1]["metrics"].keys():
        a, b = [r["metrics"][k]["time_weighted_mean"] for r in reports]
        delta[k] = {
            "absolute_change": b - a,
            "percent_change": (b / a - 1) * 100 if a else None,
            "unit": CHANNELS[k],
        }
    return {
        "first": reports[0],
        "second": reports[1],
        "change_second_minus_first": delta,
        "interpretation": "Descriptive comparison; inspect coverage and matching conditions",
    }


def drift(w, channel="speed_m_s", start=0.0, end=None, max_gap=30.0):
    _, end = _config(w, start, end, max_gap)
    if channel not in {"speed_m_s", "power_w"}:
        raise ValueError("Drift channel must be speed_m_s or power_w")
    sports = {
        s.sport
        for s in w.samples
        if start <= (s.timestamp - w.samples[0].timestamp).total_seconds() < end
    }
    reasons = []
    if len(sports) != 1 or not sports <= {"running", "cycling"}:
        reasons.append("Select a single running or cycling sport window")
    if end - start < 1200:
        reasons.append("At least 20 minutes required by this engineering guardrail")
    halves = []
    for left, right in [(start, (start + end) / 2), ((start + end) / 2, end)]:
        xsum, hsum, seconds = 0.0, 0.0, 0.0
        for a, _, lo, hi, _ in intervals(w, left, right, max_gap):
            x, h = getattr(a, channel), a.heart_rate_bpm
            if x is not None and x > 0 and h is not None and h > 0:
                xsum += x * (hi - lo)
                hsum += h * (hi - lo)
                seconds += hi - lo
        coverage = seconds / (right - left) if right > left else 0
        halves.append(
            {
                "output_to_hr_ratio": xsum / hsum if hsum else None,
                "paired_seconds": seconds,
                "paired_elapsed_coverage_fraction": coverage,
            }
        )
        if coverage < 0.9:
            reasons.append(
                "Each half requires >=90% paired elapsed coverage; pauses count as uncovered"
            )
    first, second = [h["output_to_hr_ratio"] for h in halves]
    return {
        "status": "unavailable" if reasons else "descriptive_only",
        "channel": channel,
        "window": [start, end],
        "halves": halves,
        "efficiency_decline_percent": (1 - second / first) * 100
        if not reasons and first
        else None,
        "reasons": sorted(set(reasons)),
        "method": "100*(1-(mean_output_second/mean_hr_second)/(mean_output_first/mean_hr_first)); paired intervals only",
        "limitations": "Use only for coach-confirmed steady efforts; terrain, wind, intensity changes and sensor errors confound interpretation. No diagnostic cutoff.",
    }


def lap_reports(w, max_gap=30.0):
    origin = w.samples[0].timestamp
    runs, begin = [], 0
    for i in range(1, len(w.samples)):
        a, b = w.samples[i - 1], w.samples[i]
        if (a.lap, a.sport, a.segment) != (b.lap, b.sport, b.segment):
            runs.append((begin, i))
            begin = i
    runs.append((begin, len(w.samples) - 1))
    return [
        {
            "lap": w.samples[i].lap,
            "sport": w.samples[i].sport,
            "segment": w.samples[i].segment,
            "report": analyze(
                w,
                (w.samples[i].timestamp - origin).total_seconds(),
                (w.samples[j].timestamp - origin).total_seconds(),
                max_gap,
            ),
        }
        for i, j in runs
    ]
