# Coach walkthrough

This alpha requires a Python-capable environment or help from someone who can install the local engine. There is no hosted upload portal. A chat-only AI can explain a supplied report, but cannot run the engine merely from the skill text.

## 1. Rehearse without athlete data

Clone/download this repository to your computer. Install Python 3.10+. In a terminal opened in the repository:

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest -q
python -m open_endurance_coaching.cli synthetic demo-output
python -m open_endurance_coaching.cli analyze demo-output/synthetic_run.csv
python -m open_endurance_coaching.cli compare demo-output/synthetic_run.csv --first 0 1800 --second 5400 7200
```

The comparison means first 0–30 minutes versus final 90–120 minutes. This synthetic example yields HR 140 versus 154 bpm, unchanged speed 3 m/s and complete channel coverage. It does not establish any real athlete response. The generated expected.json records known answers. Files are original synthetic data; do not replace examples with athlete files in GitHub.

## 2. Ask useful questions

In an AI environment with engine access, supply the skill and local file. Ask:

- “Which channels are available, and how much of this workout is usable?”
- “Compare the first and final 30 minutes, including coverage.”
- “Compare laps 3 and 5; here is my prescribed workout.”
- “Using my HR boundaries 130, 150 and 170 bpm, how long was spent in each zone?”
- “For this steady running segment, describe output/HR efficiency change and its limits.”

The AI should call the engine and report exact windows. If you ask why a change happened, it should distinguish observations from possible explanations. No automatic prescriptions or athlete messages are sent.

For chat-only environments, save a JSON report first:
`python -m open_endurance_coaching.cli analyze your_workout.fit > report.json`.
Review it for privacy, then supply that report to the AI. Recompute other windows with the compare command if needed.

## 3. Use an authorized real export

Obtain permission from the athlete and export the original activity from their platform using its supported tools. Supported file formats do not guarantee all export variants. Apple Health bulk XML, direct Apple HealthKit access, Garmin account access and Strava OAuth are not implemented. Missing HR/power in an export cannot be recovered by AI.

Direct local analysis processes the supplied file without copying it into the workspace. You are responsible for authorization and file security. For history/MCP, create a pseudonymous consented workspace:

```bash
python -m open_endurance_coaching.cli authorize --workspace private --athlete athlete01 --reference consent-record-01
python -m open_endurance_coaching.cli ingest --workspace private --athlete athlete01 your_workout.fit
python -m open_endurance_coaching.cli history --workspace private --athlete athlete01
python -m open_endurance_coaching.cli weekly --workspace private --athlete athlete01
```

Ingest returns a workout ID. Save context in a local JSON file, for example `{"rpe":4,"workout_goal":"steady run","threshold_profile":"coach-v1","threshold_effective_date":"2025-06-01"}`, then:
`python -m open_endurance_coaching.cli annotate --workspace private --athlete athlete01 WORKOUT_ID context.json`.
Compare two IDs with `history-compare --workspace private --athlete athlete01 FIRST_ID SECOND_ID`.
Do not put athlete names or sensitive notes into project files.

## 4. Add weather only with separate permission

Explain that rounded route coordinates and workout dates leave the machine. If authorized:
`python -m open_endurance_coaching.cli weather your_workout.fit --cache weather-cache --allow-location-network`.

Subsequent calls without the network flag read cached entries and fail if any needed entry is absent. Results are hourly reanalysis grid estimates, not a measurement at the runner. Review grid distance and temporal offsets before discussing conditions. Check provider terms for your coaching use.

## 5. Remove stored data

`python -m open_endurance_coaching.cli revoke --workspace private --athlete athlete01` blocks access and removes that athlete's stored normalized files and notes. It does not delete source exports, copied reports, weather caches or backups. Delete those separately under your retention policy. Filesystem deletion is not guaranteed forensic erasure.

## Troubleshooting

- Missing UTC offset: obtain original timezone information; do not guess it.
- Duplicate timestamps: inspect the source and resolve ambiguity; the engine does not silently merge them.
- Little coverage: inspect sampling and pauses; disclose changes to --max-gap rather than extending it blindly.
- Drift unavailable: check duration, sport, paired channels and steady intensity. Do not force a numeric conclusion.
- Length-only swim FIT: not supported yet; retain the source for the real-export pilot.
- MCP unavailable: install the mcp extra in the same Python environment; use CLI reports in other environments.

## Find workouts conversationally

After local authorization and ingestion, register a private roster alias once:
`python -m open_endurance_coaching.cli bind-alias --workspace private --athlete athlete01 --alias Bob --timezone America/Chicago`.

Then ask the connected AI, “Show me Bob's Sunday run.” It calls the discovery tool and uses the resulting ID for analysis. A CLI equivalent is:
`python -m open_endurance_coaching.cli find --workspace private --athlete Bob --day Sunday --sport running`.

The response identifies the calendar date and timezone; duplicate names or activities require clarification. This is local discovery, not a live Strava fetch. See [Strava integration gate](STRAVA.md) before planning live coaching access.
