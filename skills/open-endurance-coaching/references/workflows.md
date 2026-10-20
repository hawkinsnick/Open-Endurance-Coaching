# Tool selection and worked questions

Use only executable capabilities below. Consult repository docs/METHODS.md for formulas and docs/VALIDATION.md for evidence limits.

| Coach question | Operation | Required context |
|---|---|---|
| How did the last 30 minutes compare with the first? | Read summary duration T, compare [0,1800) with [T-1800,T) | Require T>=3600 for non-overlapping windows; state if coach requests overlapping windows |
| Did heart rate rise at similar output? | Compare explicit steady windows; inspect paired coverage; optionally drift | Running speed or cycling power plus HR; terrain/intensity context |
| How much time was in each zone? | zones / time_in_zones | Coach-supplied absolute boundaries and their effective date; no inferred age formula |
| Which intervals differed? | laps / workout_laps, then compare selected windows | Lap labels and prescribed workout if judging compliance |
| Was slowing caused by heat? | Summary/comparison, optional consented weather | Report association only; causal question remains unanswered |
| Is this athlete getting fitter? | history / compare_workouts | Same athlete; coach must match effort, devices, thresholds and conditions; no causal fitness claim |
| Did the swim improve? | Read speed/distance/laps if present | Pool length and stroke context; length-only FIT and detailed swim set inference are not supported |
| Why was cadence different? | Inspect source conventions first | FIT device cycles/min, TCX Cadence or RunCadence, and CSV convention may differ |

## Local consented workspace
Choose pseudonymous IDs. The consent reference is an audit pointer, not a signed consent system. Do not place personal information in it.

```bash
python -m open_endurance_coaching.cli authorize --workspace /private/oec --athlete athlete01 --reference consent-record-01
python -m open_endurance_coaching.cli ingest --workspace /private/oec --athlete athlete01 workout.fit
python -m open_endurance_coaching.cli history --workspace /private/oec --athlete athlete01
python -m open_endurance_coaching.cli history-compare --workspace /private/oec --athlete athlete01 FIRST_WORKOUT_ID SECOND_WORKOUT_ID
python -m open_endurance_coaching.cli revoke --workspace /private/oec --athlete athlete01
```

MCP runs locally through stdio:
`python -m open_endurance_coaching.server --workspace /private/oec`.
Tools: workout_summary, compare_windows, time_in_zones, efficiency_drift, workout_laps, athlete_history, compare_workouts, find_athlete_workouts, weekly_volume.
Use returned IDs from ingestion; never invent identifiers. The server deliberately exposes no ingestion, authorization, deletion, arbitrary-path or network tools. Local OS access, rather than athlete IDs, is the access boundary. Do not expose this server to untrusted users.

## Historical weather
Only after separate permission for location transfer:
`python -m open_endurance_coaching.cli weather workout.fit --cache /private/oec-weather --allow-location-network`.
Omit the network flag to use already cached responses. Missing cache entries fail closed. No live provider or commercial-use entitlement is implied; verify service terms before deployment.

## Synthetic rehearsal
`python -m open_endurance_coaching.cli synthetic /tmp/oec-demo` creates original fixtures for five two-hour scenarios and four import formats. Mark all demonstrations synthetic. The generated expected.json contains independently stated analytic targets. Never use these scenarios as evidence of physiological validity.
