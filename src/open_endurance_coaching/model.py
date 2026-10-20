"""Canonical SI samples. No athlete identifiers are required by the engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite, radians, sin, cos, atan2, sqrt

CHANNELS = {
    "heart_rate_bpm": "bpm",
    "power_w": "W",
    "speed_m_s": "m/s",
    "latitude": "degrees",
    "longitude": "degrees",
    "elevation_m": "m",
    "cadence_rpm": "rpm",
    "distance_m": "m",
}
SPORTS = {"running", "cycling", "swimming", "transition", "unknown"}


def timestamp(value):
    t = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timestamp requires UTC offset")
    return t.astimezone(timezone.utc)


def sport_name(value):
    return {
        "run": "running",
        "bike": "cycling",
        "biking": "cycling",
        "swim": "swimming",
        "other": "unknown",
    }.get(str(value).lower(), str(value).lower())


@dataclass
class Sample:
    timestamp: datetime
    heart_rate_bpm: float | None = None
    power_w: float | None = None
    speed_m_s: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float | None = None
    cadence_rpm: float | None = None
    distance_m: float | None = None
    lap: str = "1"
    sport: str = "unknown"
    active: bool = True
    segment: str = "1"

    def __post_init__(self):
        self.timestamp = timestamp(self.timestamp)
        self.sport = sport_name(self.sport)
        if self.sport not in SPORTS:
            self.sport = "unknown"
        self.lap, self.segment = str(self.lap), str(self.segment)
        if not isinstance(self.active, bool):
            raise ValueError("active must be boolean")
        for name in CHANNELS:
            v = getattr(self, name)
            if v is None:
                continue
            v = float(v)
            if not isfinite(v):
                raise ValueError(f"non-finite {name}")
            if name == "latitude" and not -90 <= v <= 90:
                raise ValueError("latitude outside [-90,90]")
            if name == "longitude" and not -180 <= v <= 180:
                raise ValueError("longitude outside [-180,180]")
            if name not in {"latitude", "longitude", "elevation_m"} and v < 0:
                raise ValueError(f"negative {name}")
            setattr(self, name, v)
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be paired")
        if self.heart_rate_bpm == 0:
            self.heart_rate_bpm = None


@dataclass
class Workout:
    samples: list[Sample]
    source: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    pauses: list[tuple[datetime, datetime]] = field(default_factory=list)
    lengths: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.samples:
            raise ValueError("Workout contains no samples")
        if self.samples != sorted(self.samples, key=lambda s: s.timestamp):
            self.warnings.append("Input samples reordered chronologically")
            self.samples.sort(key=lambda s: s.timestamp)
        if any(
            b.timestamp <= a.timestamp for a, b in zip(self.samples, self.samples[1:])
        ):
            raise ValueError(
                "Duplicate timestamps; resolve source ambiguity before analysis"
            )
        self.pauses = sorted((timestamp(a), timestamp(b)) for a, b in self.pauses)
        for i, (a, b) in enumerate(self.pauses):
            if a >= b or (i and a < self.pauses[i - 1][1]):
                raise ValueError("Pause intervals must be positive and non-overlapping")


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = radians(lat1), radians(lat2)
    dlat, dlon = p2 - p1, radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return 6371008.8 * 2 * atan2(sqrt(max(0, a)), sqrt(max(0, 1 - a)))
