# Open Endurance Coaching

An open, cross-platform, coach-directed endurance workout analysis engine and portable AI skill.

## Status
Version 0.1.0 development scaffold. **Not clinically validated and not ready for athlete-facing autonomous advice.**

## Principles
- Coach remains accountable for interpretation and prescriptions.
- Calculations are deterministic, tested, and report data provenance.
- Local-first processing and explicit consent for athlete data.
- Never claim causal effects from observational workout data alone.
- FIT/TCX/GPX/CSV are planned; CSV is the initial implemented import format.

## Quick start
```bash
python -m pip install -e '.[dev]'
python -m pytest
python -m open_endurance_coaching.cli examples/sample_run.csv
```

## CSV input
Required `timestamp` (ISO 8601 with UTC offset). Optional `heart_rate_bpm`, `power_w`, `speed_m_s`, `latitude`, `longitude`, `elevation_m`, `cadence_rpm`. All available samples are validated and ordered. Outputs must not be interpreted as diagnosis.

## Roadmap
- 0.1: CSV import, sample-level quality checks, reproducible summaries, skill instructions.
- 0.2: FIT/TCX/GPX parsers, workout segments, athlete history and comparisons.
- 0.3: historical weather enrichment with spatial/temporal resolution and provenance.
- 0.4: coach workspace, athlete isolation, consent, MCP integration.
- 1.0: benchmark suite, security audit, external coach validation.

## Data and licensing
Do not commit identifiable athlete files. Only ingest data with appropriate authorization; review third-party API terms independently. License to be selected before public distribution of substantial code.
