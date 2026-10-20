"""Opt-in Open-Meteo ERA5 enrichment, also usable with offline provider fixtures."""

import hashlib
import json
import os
from math import isfinite
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen
from .model import timestamp, haversine

HOST = "https://archive-api.open-meteo.com/v1/archive"
VARIABLES = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "wind_speed_10m": "m/s",
    "wind_direction_10m": "°",
}


def anchors(w, max_anchors=24):
    result = []
    for s in w.samples:
        if s.latitude is None or not s.active:
            continue
        if (
            not result
            or (s.timestamp - result[-1].timestamp).total_seconds() >= 1800
            or haversine(
                s.latitude, s.longitude, result[-1].latitude, result[-1].longitude
            )
            >= 10000
        ):
            result.append(s)
        if len(result) > max_anchors:
            raise ValueError(
                "Route exceeds 24 weather anchors; select a shorter workout"
            )
    return result


def request_for(sample):
    # Coordinates still leave the machine. Rounding is minimization, not anonymization.
    return {
        "latitude": round(sample.latitude, 2),
        "longitude": round(sample.longitude, 2),
        "start_date": (sample.timestamp - timedelta(days=1)).date().isoformat(),
        "end_date": (sample.timestamp + timedelta(days=1)).date().isoformat(),
        "hourly": ",".join(VARIABLES),
        "timezone": "UTC",
        "wind_speed_unit": "ms",
        "models": "era5",
    }


def fetch_archive(request, cache_dir, allow_network=False):
    key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    cache = Path(cache_dir)
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(cache, 0o700)
    path = cache / f"{key}.json"
    if path.exists():
        if path.is_symlink():
            raise ValueError("Refuse symlink weather cache")
        envelope = json.loads(path.read_text())
    else:
        if not allow_network:
            raise PermissionError(
                "Weather needs explicit network consent: coordinates will be sent to Open-Meteo"
            )
        with urlopen(HOST + "?" + urlencode(request), timeout=30) as response:
            payload = response.read(5_000_001)
        if len(payload) > 5_000_000:
            raise ValueError("Weather response too large")
        body = json.loads(payload)
        envelope = {
            "provider": "Open-Meteo",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "request_sha256": key,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "canonical_body_sha256": hashlib.sha256(
                json.dumps(body, sort_keys=True, allow_nan=False).encode()
            ).hexdigest(),
            "body": body,
        }
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(envelope, f, allow_nan=False)
    if envelope.get("request_sha256") != key:
        raise ValueError("Weather cache request mismatch")
    digest = hashlib.sha256(
        json.dumps(envelope["body"], sort_keys=True, allow_nan=False).encode()
    ).hexdigest()
    if envelope.get("canonical_body_sha256") != digest:
        raise ValueError(
            "Weather cache body integrity mismatch; remove and refetch the cache entry"
        )
    return envelope


def match(sample, envelope, max_seconds=3600, max_distance_m=50000):
    body = envelope["body"]
    hourly, units = body.get("hourly", {}), body.get("hourly_units", {})
    for field, unit in VARIABLES.items():
        if units.get(field) != unit:
            raise ValueError(f"Unexpected weather unit for {field}: {units.get(field)}")
    times = hourly.get("time", [])
    if not times:
        return {"status": "unavailable", "reason": "No hourly weather data"}
    if any(len(hourly.get(k, [])) != len(times) for k in VARIABLES):
        raise ValueError("Weather arrays differ in length")
    index = min(
        range(len(times)),
        key=lambda i: abs(
            (timestamp(times[i] + "+00:00") - sample.timestamp).total_seconds()
        ),
    )
    seconds = abs(
        (timestamp(times[index] + "+00:00") - sample.timestamp).total_seconds()
    )
    distance = haversine(
        sample.latitude,
        sample.longitude,
        float(body["latitude"]),
        float(body["longitude"]),
    )
    if seconds > max_seconds or distance > max_distance_m:
        return {
            "status": "unavailable",
            "reason": "Weather exceeds time or spatial match limit",
            "time_offset_seconds": seconds,
            "grid_distance_m": distance,
        }
    values = {k: hourly[k][index] for k in VARIABLES}
    for key, value in values.items():
        if value is not None and (
            not isinstance(value, (float, int))
            or isinstance(value, bool)
            or not isfinite(value)
        ):
            raise ValueError(f"Invalid weather value for {key}")
    if (
        values["relative_humidity_2m"] is not None
        and not 0 <= values["relative_humidity_2m"] <= 100
    ):
        raise ValueError("Weather humidity outside 0-100%")
    if values["wind_speed_10m"] is not None and values["wind_speed_10m"] < 0:
        raise ValueError("Negative weather wind speed")
    if (
        values["wind_direction_10m"] is not None
        and not 0 <= values["wind_direction_10m"] <= 360
    ):
        raise ValueError("Weather direction outside 0-360 degrees")
    return {
        "status": "matched"
        if all(v is not None for v in values.values())
        else "partial",
        "weather_time_utc": times[index] + "Z",
        "time_offset_seconds": seconds,
        "grid_distance_m": distance,
        "values": values,
        "units": VARIABLES,
        "provider": envelope.get("provider", "unspecified_fixture"),
        "retrieved_at": envelope.get("retrieved_at"),
        "payload_sha256": envelope.get("payload_sha256"),
        "request_sha256": envelope.get("request_sha256"),
    }


def enrich(w, cache_dir, allow_network=False, provider=None):
    selected = anchors(w)
    if not selected:
        return {"status": "unavailable", "reason": "No timestamped GPS coordinates"}
    matches = []
    for s in selected:
        request = request_for(s)
        envelope = (
            provider(request)
            if provider
            else fetch_archive(request, cache_dir, allow_network)
        )
        m = match(s, envelope)
        m["elapsed_seconds"] = (s.timestamp - w.samples[0].timestamp).total_seconds()
        matches.append(m)
    return {
        "status": "complete"
        if all(m["status"] == "matched" for m in matches)
        else "partial",
        "model_requested": "ERA5",
        "nominal_spatial_resolution_degrees": 0.25,
        "temporal_resolution_seconds": 3600,
        "anchor_policy": "every 30 min or 10 km; up to 24",
        "matching": "nearest hourly value; <=3600 s and <=50 km to returned grid point",
        "matches": matches,
        "attribution": "Weather data by Open-Meteo.com; ERA5 by ECMWF/Copernicus; CC BY 4.0",
        "limitations": [
            "Reanalysis grid estimates, not measurements at the athlete",
            "Wind is at 10 m, not athlete height; no headwind or heat-causation inference",
            "Anchors summarize route conditions; not continuous exposure or physiological correction",
            "Check provider service terms for intended use; offline cache contains sensitive location context",
        ],
    }
