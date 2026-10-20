import json
from datetime import timedelta
import pytest
from open_endurance_coaching.weather import (
    enrich,
    match,
    fetch_archive,
    request_for,
    VARIABLES,
)
from open_endurance_coaching.synthetic import workout, write_csv
from open_endurance_coaching.workspace import Workspace


def provider(request):
    return {
        "provider": "synthetic_fixture",
        "retrieved_at": "2025-06-02T00:00:00Z",
        "payload_sha256": "synthetic",
        "body": {
            "latitude": request["latitude"],
            "longitude": request["longitude"],
            "hourly_units": VARIABLES,
            "hourly": {
                "time": ["2025-06-01T12:00", "2025-06-01T13:00", "2025-06-01T14:00"],
                "temperature_2m": [20, 21, 22],
                "relative_humidity_2m": [60, 55, 50],
                "wind_speed_10m": [2, 3, 4],
                "wind_direction_10m": [180, 190, 200],
            },
        },
    }


def test_weather_offline_known_answer(tmp_path):
    r = enrich(workout(), tmp_path, provider=provider)
    assert r["status"] == "complete"
    assert len(r["matches"]) == 5
    assert r["matches"][-1]["values"]["temperature_2m"] == 22
    assert r["matches"][0]["grid_distance_m"] < 1000
    assert r["temporal_resolution_seconds"] == 3600
    assert "latitude" not in r["matches"][0]


def test_weather_network_requires_opt_in(tmp_path):
    with pytest.raises(PermissionError, match="consent"):
        fetch_archive(request_for(workout().samples[0]), tmp_path)


def test_weather_partial_unit_spatial_and_time_gates():
    sample = workout().samples[0]
    envelope = provider(request_for(sample))
    envelope["body"]["hourly"]["temperature_2m"][0] = None
    assert match(sample, envelope)["status"] == "partial"
    envelope["body"]["hourly_units"] = dict(VARIABLES, temperature_2m="F")
    with pytest.raises(ValueError, match="unit"):
        match(sample, envelope)
    envelope = provider(request_for(sample))
    envelope["body"]["latitude"] = -40
    assert match(sample, envelope)["status"] == "unavailable"
    envelope = provider(request_for(sample))
    sample.timestamp += timedelta(days=2)
    assert match(sample, envelope)["status"] == "unavailable"


def test_weather_missing_gps(tmp_path):
    w = workout()
    for s in w.samples:
        s.latitude = s.longitude = None
    assert enrich(w, tmp_path)["status"] == "unavailable"


def test_weather_cache_reused_offline(tmp_path, monkeypatch):
    import io
    import open_endurance_coaching.weather as mod

    req = request_for(workout().samples[0])
    body = provider(req)["body"]
    calls = []

    def fake_url(url, timeout):
        calls.append(url)
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr(mod, "urlopen", fake_url)
    first = fetch_archive(req, tmp_path, True)
    assert fetch_archive(req, tmp_path, False) == first
    assert len(calls) == 1
    assert "models=era5" in calls[0]


@pytest.fixture
def stored(tmp_path):
    file = tmp_path / "workout.csv"
    write_csv(workout(), file)
    ws = Workspace(tmp_path / "private")
    return ws, file


def test_workspace_consent_roundtrip_isolation_revoke(stored):
    ws, file = stored
    with pytest.raises(PermissionError):
        ws.ingest("a", file)
    ws.authorize("a", "consent-reference-1")
    result = ws.ingest("a", file)
    wid = result["workout_id"]
    assert ws.load("a", wid).source == result["source"]
    assert len(ws.history("a")) == 1
    ws.authorize("b", "consent-reference-2")
    with pytest.raises(FileNotFoundError):
        ws.load("b", wid)
    assert (
        ws.compare_history("a", wid, wid)["changes"]["heart_rate_bpm"][
            "absolute_change"
        ]
        == 0
    )
    assert ws.revoke("a")["workspace_data_removed"]
    with pytest.raises(PermissionError):
        ws.load("a", wid)
    assert list((ws.root / "a").iterdir()) == [ws.root / "a" / "consent.json"]
    ws.authorize("a", "new-consent")
    assert ws.history("a") == []


@pytest.mark.parametrize("name", ["../a", "a/b", "", ".", "a" * 65])
def test_workspace_path_rejection(stored, name):
    ws, _ = stored
    with pytest.raises(ValueError):
        ws.authorize(name, "ref")


def test_workspace_symlink_refusal(stored, tmp_path):
    ws, file = stored
    (ws.root / "a").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        ws.authorize("a", "ref")


def test_file_symlink_refusal(stored, tmp_path):
    ws, _ = stored
    ws.authorize("a", "ref")
    (ws.root / "a" / "consent.json").unlink()
    (ws.root / "a" / "consent.json").symlink_to(tmp_path / "secret")
    with pytest.raises(ValueError, match="symlink"):
        ws.history("a")


def test_private_permissions(stored):
    ws, file = stored
    ws.authorize("a", "ref")
    wid = ws.ingest("a", file)["workout_id"]
    assert (ws.root.stat().st_mode & 0o777) == 0o700
    assert ((ws.root / "a" / wid / "samples.csv").stat().st_mode & 0o777) == 0o600


def test_annotations_and_weekly_totals(stored):
    ws, file = stored
    ws.authorize("a", "synthetic")
    wid = ws.ingest("a", file)["workout_id"]
    ws.annotate(
        "a",
        wid,
        {
            "rpe": 4,
            "threshold_profile": "coach-v1",
            "threshold_effective_date": "2025-06-01",
        },
    )
    assert ws.load("a", wid).metadata["coach_context"]["rpe"] == 4
    assert ws.compare_history("a", wid, wid)["threshold_profiles_match"] is True
    week = next(iter(ws.weekly_totals("a")["weeks"].values()))
    assert week["covered_seconds"] == 7200
    assert week["covered_distance_m"] == 21600
    with pytest.raises(ValueError):
        ws.annotate("a", wid, {"rpe": float("nan")})
    with pytest.raises(ValueError):
        ws.annotate("a", wid, {"unsupported": "field"})


def test_normalized_file_integrity(stored):
    ws, file = stored
    ws.authorize("a", "ref")
    wid = ws.ingest("a", file)["workout_id"]
    p = ws.root / "a" / wid / "samples.csv"
    p.write_text(p.read_text().replace(",140.0,", ",141.0,"))
    with pytest.raises(ValueError, match="integrity"):
        ws.load("a", wid)


def test_weather_cache_integrity(tmp_path, monkeypatch):
    import io
    import open_endurance_coaching.weather as mod

    req = request_for(workout().samples[0])
    monkeypatch.setattr(
        mod,
        "urlopen",
        lambda *a, **k: io.BytesIO(json.dumps(provider(req)["body"]).encode()),
    )
    fetch_archive(req, tmp_path, True)
    p = next(tmp_path.glob("*.json"))
    body = json.loads(p.read_text())
    body["body"]["hourly"]["temperature_2m"][0] = 999
    p.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="integrity"):
        fetch_archive(req, tmp_path)
