# Platform integration

## One engine, three access paths

| Environment | How to use it | Boundary |
|---|---|---|
| Python-capable AI coding environment | Install repository; provide SKILL.md; execute CLI/Python API | Verify file access and installed dependencies; instructions do not install or execute themselves |
| MCP client supporting local stdio | Install mcp extra; launch server below | Nine read-only tools; local process owner can read all authorized athlete folders |
| Chat-only AI | Upload a reviewed JSON engine report and skill instructions | Can interpret existing results; cannot calculate new windows without engine execution |

No platform certification is claimed. The automated protocol test uses the official Python MCP client against this server, not every commercial AI client. There is no hosted service, Strava OAuth, Garmin API connector, Apple HealthKit integration or Apple bulk Health XML parser.

## MCP setup

First authorize/ingest locally using the coach guide. Then configure your client's MCP server entry, adapting its documented configuration format:

```json
{
  "mcpServers": {
    "open-endurance-coaching": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["-m", "open_endurance_coaching.server", "--workspace", "/absolute/path/to/private-workspace"]
    }
  }
}
```

On Windows use the absolute path to `.venv/Scripts/python.exe`. This JSON is a common configuration pattern, not a promise that every client accepts the same settings. The repository does not change any client settings automatically.

Tools: workout_summary, compare_windows, time_in_zones, efficiency_drift, workout_laps, athlete_history, compare_workouts, find_athlete_workouts, weekly_volume. Each loads data through current consent checks. IDs come from local ingest. Tool inputs are structured; natural-language mapping is performed by the AI skill, not a separate free-text intent classifier.

The MCP process has no write/consent/revoke/network tools. Weather is an explicitly consented CLI operation. The server only starts a local stdio transport; do not wrap it in a remote service without separate authentication, authorization and security work.

## Python API

```python
from open_endurance_coaching.importers import load_workout
from open_endurance_coaching.analysis import analyze, compare

w = load_workout("authorized_workout.fit")
summary = analyze(w)
result = compare(w, (0, 1800), (5400, 7200))  # only if duration >=7200
```

Always inspect coverage, warnings, methods and units. API objects are mutable; callers who modify samples must validate them again before use. Do not bypass the consented workspace when using a shared history or MCP deployment.
