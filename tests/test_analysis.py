from pathlib import Path
import pytest
from open_endurance_coaching.analysis import load_csv, summarize


def test_example():
    rows = load_csv(Path(__file__).parents[1] / "examples/sample_run.csv")
    out = summarize(rows)
    assert out["elapsed_seconds"] == 120
    assert out["metrics"]["heart_rate_bpm"]["sample_mean"] == 145


def test_reject_naive_timestamp(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("timestamp,heart_rate_bpm\n2026-01-01T12:00:00,140\n")
    with pytest.raises(ValueError, match="UTC offset"):
        load_csv(p)
