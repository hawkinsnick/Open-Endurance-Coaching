---
name: open-endurance-coaching
description: Evidence-driven endurance workout interrogation for qualified coaches, using deterministic calculations and transparent limitations.
---
# Open Endurance Coaching skill

## Operating contract
1. Obtain athlete authorization before processing identifiable training data.
2. Use the engine for all numeric claims; do not invent data or formulas.
3. Distinguish measured, estimated, and missing inputs; provide units, intervals, and source provenance.
4. Treat correlation as observational, not proof of physiological causation.
5. Report sensor gaps, uncertainty, sampling bias and methodological limitations.
6. Defer clinical concerns to appropriately qualified clinicians; never diagnose.
7. Keep coach in control of recommendations and athlete communications.

## Initial supported workflow
Run `oec workout.csv` or `python -m open_endurance_coaching.cli workout.csv`, inspect JSON, and answer only questions supported by its metrics. The initial engine produces sample-weighted means; do not describe them as time-weighted. FIT/TCX/GPX, weather, history and MCP are future capabilities, not yet available.

## Example prompts
- Which channels are present in this workout, and what are their data gaps?
- What is the elapsed duration and average observed heart rate?
- Which additional data would be required to assess cardiac drift?
