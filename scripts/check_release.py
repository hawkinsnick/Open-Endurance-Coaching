"""Version/skill/doc-link and analytic release smoke checks; no network or athlete data."""

import json
import re
import tempfile
from pathlib import Path
from open_endurance_coaching import __version__
from open_endurance_coaching.analysis import analyze, compare
from open_endurance_coaching.importers import load_workout
from open_endurance_coaching.synthetic import export_examples

ROOT = Path(__file__).resolve().parents[1]
assert f'version = "{__version__}"' in (ROOT / "pyproject.toml").read_text()
assert __version__ in (ROOT / "README.md").read_text()
assert __version__ in (ROOT / "skills/open-endurance-coaching/SKILL.md").read_text()
for path in ROOT.rglob("*.md"):
    if ".git" in path.parts:
        continue
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
        if "://" in target or target.startswith("#"):
            continue
        assert (path.parent / target.split("#")[0]).exists(), (path, target)
with tempfile.TemporaryDirectory() as folder:
    export_examples(folder)
    w = load_workout(Path(folder) / "synthetic_run.csv")
    r = analyze(w)
    assert r["elapsed_seconds"] == 7200
    assert r["metrics"]["heart_rate_bpm"]["time_weighted_mean"] == 147
    assert r["distance"]["covered_distance_m"] == 21600
    c = compare(w, (0, 1800), (5400, 7200))
    assert c["change_second_minus_first"]["heart_rate_bpm"]["absolute_change"] == 14
    print(
        json.dumps(
            {
                "version": __version__,
                "status": "passed",
                "synthetic_source_sha256": w.source["sha256"],
                "checks": [
                    "version_sync",
                    "skill_sync",
                    "local_doc_links",
                    "two_hour_known_answers",
                ],
            }
        )
    )
