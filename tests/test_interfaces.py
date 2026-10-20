import json
import subprocess
import sys
from pathlib import Path
import pytest
from open_endurance_coaching.synthetic import write_csv, workout
from open_endurance_coaching.workspace import Workspace


def test_cli_success_and_failure(tmp_path):
    file = tmp_path / "w.csv"
    write_csv(workout(), file)
    r = subprocess.run(
        [sys.executable, "-m", "open_endurance_coaching.cli", str(file)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert json.loads(r.stdout)["elapsed_seconds"] == 7200
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "open_endurance_coaching.cli",
            "analyze",
            str(file),
            "--start",
            "-1",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert json.loads(r.stderr)["status"] == "error"


def test_mcp_stdio_protocol(tmp_path):
    pytest.importorskip("mcp")
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    file = tmp_path / "w.csv"
    write_csv(workout(), file)
    ws = Workspace(tmp_path / "private")
    ws.authorize("a", "synthetic-test")
    wid = ws.ingest("a", file)["workout_id"]
    from open_endurance_coaching.discovery import bind_alias

    bind_alias(ws, "a", "Bob", "America/Chicago")

    async def check():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "open_endurance_coaching.server", "--workspace", str(ws.root)],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                assert len(listed.tools) == 9
                result = await session.call_tool(
                    "workout_summary", {"athlete_id": "a", "workout_id": wid}
                )
                assert not result.isError
                # MCP v1 returns typed structured output as well as text content.
                payload = result.structuredContent or json.loads(result.content[0].text)
                assert payload["elapsed_seconds"] == 7200
                assert payload["metrics"]["heart_rate_bpm"]["time_weighted_mean"] == 147
                operations = [
                    (
                        "compare_windows",
                        {
                            "athlete_id": "a",
                            "workout_id": wid,
                            "first_start": 0,
                            "first_end": 1800,
                            "second_start": 5400,
                            "second_end": 7200,
                        },
                    ),
                    (
                        "time_in_zones",
                        {
                            "athlete_id": "a",
                            "workout_id": wid,
                            "channel": "heart_rate_bpm",
                            "boundaries": [130, 150],
                        },
                    ),
                    ("efficiency_drift", {"athlete_id": "a", "workout_id": wid}),
                    ("workout_laps", {"athlete_id": "a", "workout_id": wid}),
                    ("athlete_history", {"athlete_id": "a"}),
                    (
                        "compare_workouts",
                        {
                            "athlete_id": "a",
                            "first_workout_id": wid,
                            "second_workout_id": wid,
                        },
                    ),
                    ("weekly_volume", {"athlete_id": "a"}),
                    (
                        "find_athlete_workouts",
                        {
                            "athlete_alias": "Bob",
                            "day": "2025-06-01",
                            "sport": "running",
                        },
                    ),
                ]
                for operation, arguments in operations:
                    outcome = await session.call_tool(operation, arguments)
                    assert not outcome.isError, (operation, outcome)
                matched = outcome.structuredContent or json.loads(
                    outcome.content[0].text
                )
                assert matched["status"] == "matched"
                assert matched["live_platform_fetch"] is False
                bad = await session.call_tool(
                    "workout_summary", {"athlete_id": "../a", "workout_id": wid}
                )
                assert bad.isError
                other = await session.call_tool(
                    "workout_summary", {"athlete_id": "b", "workout_id": wid}
                )
                assert other.isError

    anyio.run(check)


def test_skill_frontmatter_and_commands():
    import yaml

    skill = Path(__file__).parents[1] / "skills/open-endurance-coaching/SKILL.md"
    content = skill.read_text()
    front = yaml.safe_load(content.split("---")[1])
    assert front["name"] == "open-endurance-coaching"
    assert len(front["description"]) > 20
    assert "0.8.0a1" in content
