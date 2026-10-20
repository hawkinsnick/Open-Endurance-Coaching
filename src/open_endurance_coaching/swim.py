"""Descriptive pool-length summaries from native FIT length messages."""

from math import isfinite
from .model import timestamp


def summarize_lengths(w, start=0.0, end=None):
    total = (w.samples[-1].timestamp - w.samples[0].timestamp).total_seconds()
    end = total if end is None else end
    if not w.lengths:
        return {
            "status": "unavailable",
            "reason": "No native pool length messages; do not infer pool lengths from GPS",
        }
    selected = []
    for length in w.lengths:
        try:
            a, b = timestamp(length["start"]), timestamp(length["end"])
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        lo, hi = (
            (a - w.samples[0].timestamp).total_seconds(),
            (b - w.samples[0].timestamp).total_seconds(),
        )
        if lo >= start and hi <= end:
            selected.append(length)
    active = [x for x in selected if x.get("type") == "active"]
    rests = [x for x in selected if x.get("type") == "idle"]
    pools = {
        s.get("pool_length_m")
        for s in w.metadata.get("sessions", [])
        if s.get("sport") == "swimming"
    }
    pool = next(iter(pools)) if len(pools) == 1 else None
    if pool is not None and (not isfinite(pool) or pool <= 0):
        pool = None

    def valid(v):
        return isinstance(v, (float, int)) and isfinite(v) and v >= 0

    timers = [x.get("timer_seconds") for x in active if valid(x.get("timer_seconds"))]
    strokes = [x.get("strokes") for x in active if valid(x.get("strokes"))]
    seconds = sum(timers) if len(timers) == len(active) and active else None
    distance = pool * len(active) if pool is not None and active else None
    return {
        "status": "descriptive_only",
        "window": [start, end],
        "active_lengths": len(active),
        "idle_lengths": len(rests),
        "selected_native_lengths": len(selected),
        "pool_length_m": pool,
        "active_length_timer_seconds": seconds,
        "pool_distance_m": distance,
        "pace_seconds_per_100m": seconds / distance * 100
        if seconds is not None and distance
        else None,
        "recorded_strokes": sum(strokes)
        if len(strokes) == len(active) and active
        else None,
        "method": "Native active lengths * single unambiguous session pool length; fully contained lengths only",
        "limitations": "Device length detection may be wrong. No automatic drill correction, stroke classification, set inference or SWOLF comparison. Mixed pool lengths suppress distance.",
    }
