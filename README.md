# Open Endurance Coaching

**Engineering alpha 0.8.0a1** — a local workout analysis engine and portable AI skill for qualified endurance and triathlon coaches.

Upload an authorized workout in an environment that can run the engine, ask a question, and obtain reproducible calculations tied to explicit workout windows. Coaches remain responsible for interpretation and prescriptions.

## What works

- CSV, timestamped GPX tracks, TCX activities/extensions, and FIT record/lap/session/timer/length messages through fitdecode.
- Time-weighted summaries, data coverage, pause and gap handling, lap/sport segments, coach-defined zones, window comparisons, output/HR efficiency change, power variability and recorded-power integrals.
- Descriptive pool-length summaries when native FIT lengths and an unambiguous pool length are present. Running, cycling, swimming and transition samples; no inferred swim sets or drill correction.
- Same-athlete history comparisons, UTC weekly volume totals and coach-supplied context/RPE/threshold-profile annotations.
- Opt-in historical weather matching with source, model, time offset, grid distance, cache and uncertainty.
- A repository skill, JSON CLI, and nine read-only local MCP tools using the same engine.

**Evidence boundary:** synthetic and protocol-tested engineering alpha. No real athlete, production device export, external coach, clinical or independent security validation is claimed. Instructions alone do not give a chat-only AI the ability to execute code or access files. No direct Garmin/Strava/Apple account connections are implemented.

## Try it

Python 3.10+ and a local checkout are required. Use a virtual environment, then:

```bash
python -m pip install -e '.[dev,mcp]'
python -m pytest -q
python -m open_endurance_coaching.cli synthetic /tmp/oec-demo
python -m open_endurance_coaching.cli analyze /tmp/oec-demo/synthetic_run.csv
python -m open_endurance_coaching.cli compare /tmp/oec-demo/synthetic_run.csv --first 0 1800 --second 5400 7200
```

These are **synthetic** two-hour sessions, not athlete records. The run's known answers are 7,200 seconds, 21.6 km from speed, and HR 140 versus 154 bpm in the first/last 30 minutes. Generate cycling, swimming, brick and gap scenarios with the same command. Windows use elapsed seconds, not moving time.

For authorized real files, replace the synthetic path with the local FIT/TCX/GPX/CSV path. Use platform exports only with authorization; format support does not establish compatibility with every exporter. The 30-second default gap limit must be reviewed for sparse files.

## Find an athlete’s workout

Ask “Show me Bob’s Sunday run.” With a consented roster and imported workouts, the skill resolves the athlete, timezone, calendar date and activity; duplicate matches require clarification. See [workout discovery and the live Strava gate](docs/STRAVA.md). This alpha performs local lookup; Strava live coaching/AI access is gated by current platform restrictions.

## For coaches and AI platforms

Read the [coach walkthrough](docs/COACH_GUIDE.md), including installation, consented storage, example questions and data deletion. Give the AI [the skill](skills/open-endurance-coaching/SKILL.md) in a supported skill environment, use an MCP client, or supply an engine JSON report to a chat-only system. These paths have different capabilities; see [platform integration](docs/INTEGRATION.md).

## Technical evidence and project status

- [Methods, formulas and schema](docs/METHODS.md)
- [Validation evidence and remaining gates](docs/VALIDATION.md)
- [Privacy and security boundaries](docs/PRIVACY.md)
- [Roadmap and capability matrix](docs/ROADMAP.md)
- [Primary technical references and data provenance](docs/SOURCES.md)
- [Changelog](CHANGELOG.md)
- [Licensing status](LICENSE-STATUS.md)

Code, skill and documentation changes must be reviewed together. CI tests calculations, file parsing, consent isolation, privacy controls, command-line behavior and the MCP protocol. Never commit identifiable athlete files. Public visibility is not a software license grant; project licensing remains pending.
