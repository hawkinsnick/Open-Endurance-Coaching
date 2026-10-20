import pytest
from open_endurance_coaching.importers import load_workout
from open_endurance_coaching.synthetic import export_examples, fit_bytes
from open_endurance_coaching.analysis import analyze


@pytest.fixture
def files(tmp_path):
    export_examples(tmp_path)
    return tmp_path


@pytest.mark.parametrize("suffix", ["csv", "fit", "tcx", "gpx"])
def test_formats(files, suffix):
    name = "synthetic_run.csv" if suffix == "csv" else "synthetic." + suffix
    w = load_workout(files / name)
    assert len(w.samples) >= 3
    assert len(w.source["sha256"]) == 64
    assert w.source["format"] == suffix


def test_fit_real_binary_decode(files):
    w = load_workout(files / "synthetic.fit")
    r = analyze(w)
    assert w.samples[0].sport == "running"
    assert w.samples[0].speed_m_s == 3
    assert w.samples[0].latitude == pytest.approx(41.88, abs=1e-6)
    assert len(w.pauses) == 1
    assert r["covered_seconds"] == 50
    assert r["distance"]["covered_distance_m"] == 150
    assert r["mechanical_work_kj"] == 10


def test_fit_crc_rejected(tmp_path):
    p = tmp_path / "broken.fit"
    raw = bytearray(fit_bytes())
    raw[-1] ^= 1
    p.write_bytes(raw)
    with pytest.raises(Exception, match="CRC"):
        load_workout(p)


def test_tcx_extensions(files):
    w = load_workout(files / "synthetic.tcx")
    assert w.samples[0].power_w == 200
    assert w.samples[0].speed_m_s == 3
    assert analyze(w)["distance"]["covered_distance_m"] == 30


@pytest.mark.parametrize(
    "content",
    [
        "timestamp,timestamp\n2025-06-01T00:00Z,2025-06-01T00:00Z\n",
        "timestamp,heart_rate_bpm\n2025-06-01T00:00Z,nan\n",
        "timestamp,heart_rate_bpm\n2025-06-01T00:00Z,140,extra\n",
        "timestamp,active\n2025-06-01T00:00Z,maybe\n",
        "timestamp\n",
        "timestamp\n2025-06-01T00:00\n",
    ],
)
def test_bad_csv(tmp_path, content):
    p = tmp_path / "bad.csv"
    p.write_text(content)
    with pytest.raises(ValueError):
        load_workout(p)


def test_entities_refused(tmp_path):
    p = tmp_path / "bad.gpx"
    p.write_text(
        '<!DOCTYPE gpx [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><gpx>&xxe;</gpx>'
    )
    from defusedxml.common import DefusedXmlException

    with pytest.raises(DefusedXmlException):
        load_workout(p)


def test_gpx_no_time_refused(tmp_path):
    p = tmp_path / "bad.gpx"
    p.write_text('<gpx><trk><trkseg><trkpt lat="0" lon="0"/></trkseg></trk></gpx>')
    with pytest.raises(ValueError, match="time"):
        load_workout(p)


def test_track_segments_excluded(tmp_path):
    p = tmp_path / "two.gpx"
    p.write_text(
        '<gpx><trk><trkseg><trkpt lat="0" lon="0"><time>2025-06-01T00:00:00Z</time></trkpt></trkseg><trkseg><trkpt lat="0" lon="0.001"><time>2025-06-01T00:00:10Z</time></trkpt></trkseg></trk></gpx>'
    )
    assert analyze(load_workout(p))["covered_seconds"] == 0


def test_native_fit_swim_lengths(tmp_path):
    p = tmp_path / "pool.fit"
    p.write_bytes(fit_bytes(swim=True))
    w = load_workout(p)
    assert w.samples[0].sport == "swimming"
    assert len(w.lengths) == 2
    r = analyze(w)["pool_swim"]
    assert r["pool_length_m"] == 25
    assert r["pool_distance_m"] == 50
    assert r["pace_seconds_per_100m"] == 120
    assert r["recorded_strokes"] == 41
