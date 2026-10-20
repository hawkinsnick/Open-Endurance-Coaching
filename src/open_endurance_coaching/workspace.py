"""Single-user local workspace. OS ownership is the security boundary, not athlete IDs."""

import csv
import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict
from .model import CHANNELS
from .importers import load_workout
from .analysis import analyze


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise ValueError("Use 1-64 letters, digits, hyphens or underscores for IDs")
    return value


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    def _path(self, *parts):
        p = self.root.joinpath(*(identifier(x) for x in parts))
        current = self.root
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Workspace symlinks are forbidden")
        if not p.resolve().is_relative_to(self.root):
            raise ValueError("Path escapes workspace")
        return p

    def _file(self, folder, name):
        p = folder / name
        if p.is_symlink():
            raise ValueError("Workspace file symlinks are forbidden")
        return p

    def _write(self, path, content):
        if path.is_symlink():
            raise ValueError("Workspace symlinks are forbidden")
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        os.chmod(path, 0o600)

    def authorize(self, athlete_id, reference):
        if not reference or not reference.strip():
            raise ValueError(
                "Consent reference is required; use a non-identifying record reference"
            )
        folder = self._path(athlete_id)
        folder.mkdir(mode=0o700, exist_ok=True)
        self._write(
            self._file(folder, "consent.json"),
            json.dumps(
                {
                    "authorized": True,
                    "reference": reference,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
        )
        return {"athlete_id": athlete_id, "authorized": True}

    def _authorized(self, athlete_id):
        folder = self._path(athlete_id)
        consent = self._file(folder, "consent.json")
        if not consent.exists() or not json.loads(consent.read_text()).get(
            "authorized"
        ):
            raise PermissionError("Active athlete authorization is required")
        return folder

    def ingest(self, athlete_id, source):
        self._authorized(athlete_id)
        w = load_workout(source)
        workout_id = w.source["sha256"][:24]
        target = self._path(athlete_id, workout_id)
        target.mkdir(mode=0o700, exist_ok=True)
        import io

        stream = io.StringIO()
        columns = ["timestamp", *CHANNELS, "lap", "sport", "active", "segment"]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for sample in w.samples:
            row = asdict(sample)
            row["timestamp"] = sample.timestamp.isoformat()
            writer.writerow(row)
        self._write(self._file(target, "samples.csv"), stream.getvalue())
        meta = {
            "normalized_sha256": __import__("hashlib")
            .sha256(stream.getvalue().encode())
            .hexdigest(),
            "source": w.source,
            "warnings": w.warnings,
            "metadata": w.metadata,
            "lengths": w.lengths,
            "pauses": [[a.isoformat(), b.isoformat()] for a, b in w.pauses],
        }
        self._write(
            self._file(target, "metadata.json"), json.dumps(meta, allow_nan=False)
        )
        return {"athlete_id": athlete_id, "workout_id": workout_id, "source": w.source}

    def load(self, athlete_id, workout_id):
        self._authorized(athlete_id)
        folder = self._path(athlete_id, workout_id)
        w = load_workout(self._file(folder, "samples.csv"))
        meta = json.loads(self._file(folder, "metadata.json").read_text())
        from .model import timestamp

        if meta.get("normalized_sha256") != w.source["sha256"]:
            raise ValueError("Stored normalized workout integrity mismatch")
        w.source, w.metadata, w.lengths = (
            meta["source"],
            meta["metadata"],
            meta["lengths"],
        )
        w.warnings = meta["warnings"]
        context = self._file(folder, "context.json")
        if context.exists():
            w.metadata["coach_context"] = json.loads(context.read_text())
        w.pauses = [(timestamp(a), timestamp(b)) for a, b in meta["pauses"]]
        w.__post_init__()
        return w

    def annotate(self, athlete_id, workout_id, context):
        self._authorized(athlete_id)
        self.load(athlete_id, workout_id)
        allowed = {
            "coach_note",
            "workout_goal",
            "rpe",
            "threshold_profile",
            "threshold_effective_date",
        }
        if not isinstance(context, dict) or set(context) - allowed:
            raise ValueError("Unsupported annotation fields")
        if "rpe" in context and (
            not isinstance(context["rpe"], (int, float))
            or isinstance(context["rpe"], bool)
            or not 0 <= context["rpe"] <= 10
        ):
            raise ValueError("RPE must be finite and within 0-10")
        for field in allowed - {"rpe"}:
            if field in context and (
                not isinstance(context[field], str) or len(context[field]) > 2000
            ):
                raise ValueError(
                    "Annotation text fields must be strings <=2000 characters"
                )
        folder = self._path(athlete_id, workout_id)
        self._write(
            self._file(folder, "context.json"), json.dumps(context, allow_nan=False)
        )
        return {"athlete_id": athlete_id, "workout_id": workout_id, "context": context}

    def history(self, athlete_id):
        folder = self._authorized(athlete_id)
        result = []
        for item in sorted(folder.iterdir()):
            if item.is_symlink():
                raise ValueError("Workspace symlinks are forbidden")
            if item.is_dir():
                w = self.load(athlete_id, item.name)
                result.append(
                    {
                        "workout_id": item.name,
                        "start_utc": w.samples[0].timestamp.isoformat(),
                        "report": analyze(w),
                    }
                )
        return result

    def compare_history(self, athlete_id, first_id, second_id):
        a, b = [analyze(self.load(athlete_id, x)) for x in (first_id, second_id)]
        changes = {}
        if a["sports"] != b["sports"]:
            raise ValueError("Select matching sports before history comparison")
        for k in a["metrics"].keys() & b["metrics"].keys():
            x, y = [r["metrics"][k]["time_weighted_mean"] for r in (a, b)]
            changes[k] = {
                "absolute_change": y - x,
                "percent_change": (y / x - 1) * 100 if x else None,
            }
        return {
            "first": a,
            "second": b,
            "changes": changes,
            "threshold_profiles_match": (
                a["metadata"].get("coach_context", {}).get("threshold_profile")
                == b["metadata"].get("coach_context", {}).get("threshold_profile")
            )
            if a["metadata"].get("coach_context", {}).get("threshold_profile")
            and b["metadata"].get("coach_context", {}).get("threshold_profile")
            else None,
            "limitations": "Coach must match effort, duration, thresholds, device conventions and conditions. No fitness or causal inference.",
        }

    def weekly_totals(self, athlete_id):
        weeks = {}
        for entry in self.history(athlete_id):
            from .model import timestamp

            iso = timestamp(entry["start_utc"]).isocalendar()
            key = f"{iso.year}-W{iso.week:02d}"
            r = entry["report"]
            bucket = weeks.setdefault(
                key,
                {
                    "workouts": 0,
                    "elapsed_seconds": 0,
                    "covered_seconds": 0,
                    "covered_distance_m": 0,
                    "power_integral_kj": 0,
                    "workouts_with_distance": 0,
                    "workouts_with_power": 0,
                },
            )
            bucket["workouts"] += 1
            bucket["elapsed_seconds"] += r["elapsed_seconds"]
            bucket["covered_seconds"] += r["covered_seconds"]
            if r["distance"]["covered_distance_m"] is not None:
                bucket["covered_distance_m"] += r["distance"]["covered_distance_m"]
                bucket["workouts_with_distance"] += 1
            if r["mechanical_work_kj"] is not None:
                bucket["power_integral_kj"] += r["mechanical_work_kj"]
                bucket["workouts_with_power"] += 1
        return {
            "weeks": weeks,
            "basis": "UTC ISO week of workout start; only workouts present in this workspace",
            "limitations": "Descriptive volume totals, not training stress, recovery, readiness or fitness. Covered distance and power can be partial; a zero with zero contributing workouts means unavailable.",
        }

    def revoke(self, athlete_id):
        folder = self._path(athlete_id)
        if folder.exists():
            for item in folder.iterdir():
                if item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                elif item.name != "consent.json":
                    item.unlink()
            self._write(
                self._file(folder, "consent.json"), json.dumps({"authorized": False})
            )
        roster_path = self._file(self.root, "roster.json")
        if roster_path.exists():
            roster = json.loads(roster_path.read_text())
            self._write(
                roster_path,
                json.dumps(
                    [entry for entry in roster if entry["athlete_id"] != athlete_id]
                ),
            )
        return {
            "athlete_id": athlete_id,
            "authorized": False,
            "workspace_data_removed": True,
            "limitation": "Source files, exports, external weather caches and backups are outside this purge",
        }
