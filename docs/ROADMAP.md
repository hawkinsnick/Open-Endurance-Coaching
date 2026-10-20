# Roadmap

## Engineering alpha 0.8.0a1 delivered

| Roadmap area | Implemented alpha capability | Explicit limit |
|---|---|---|
| 0.2 foundation | Canonical units/time, time weighting, coverage, pause/gap rules, provenance | Left-held interpolation assumptions; no validated artifact classifier |
| 0.3 imports | CSV, FIT, TCX, GPX; native laps/timer/session/length information | Synthetic fixtures verified; production exporter/device matrix remains open |
| 0.4 interrogation | Structured summary, zones, laps, comparisons, descriptive efficiency change | AI maps language to tools; no autonomous prescriptions |
| 0.5 conditions | Live/offline ERA5 enrichment, spatial/time offsets, cache, provenance | Hourly route anchors; no causal heat adjustment, WBGT or headwind model |
| 0.6 triathlon | Sport/transition boundaries, native pool lengths, sample-level run/bike/swim summaries | No length-only FIT, inferred swim sets, drill correction or transition-quality scoring |
| 0.7 history | Per-athlete comparisons, weekly volume, coach notes/RPE/threshold IDs | No automatic condition matching, training stress or readiness model |
| 0.8 portability | CLI, Python API, skill, nine MCP stdio tools, shared calculations | Protocol-tested; individual commercial AI hosts not certified |

Engineering alpha means the implemented subset is testable and reproducible, with the exclusions above. It does not mean every desired feature or every device variant has been implemented.

## Live retrieval workstream

The core interaction is “Show me Bob’s Sunday run,” followed by questions. Alpha implements authorized local alias/date/sport discovery and clarification. Live Strava coaching/AI retrieval requires an applicable arrangement under current platform restrictions; see STRAVA.md. A future permitted provider adapter must add OAuth/account binding, secure token storage/rotation, scopes, rate-limit handling, deauthorization/deletion and production authorization tests. Synthetic mocks cannot validate a real account connection.

## 0.9 real-workout pilot

1. Obtain consented original exports from Garmin, Strava and Apple Watch export workflows, covering run, bike, pool/open-water swim and a brick/multisport file. Record device/exporter versions and permitted use.
2. Have coaches independently mark pauses, intervals, suspect sensor segments and known workout intentions. Reconcile elapsed/timer/moving-time and calculation definitions before comparing product numbers.
3. Compare parser outputs and metrics against source records and independent reference calculations; track every discrepancy with cause, severity and regression test. Test sparse/duplicate records, laps at boundaries, length-only swims and device cadence conventions.
4. Evaluate realistic questions with multiple certified coaches. Score factual/numeric accuracy, unsupported claims, missing-data handling, usefulness, time saved and reproducibility. Define acceptance criteria before the held-out evaluation.
5. Verify privacy/deletion behavior in the intended deployment and review third-party terms. Resolve project licensing before an externally distributed reusable release.

## 1.0 release gate

Publish a device/export compatibility matrix and benchmark methodology; resolve critical defects; complete external coach validation and independent security review appropriate to the deployment. Document limitations and negative findings. Version the engine, skill, docs and benchmark together. A release number never substitutes for validation.

No real-athlete or external-coach gate is marked passed based on synthetic evidence. No data-dependent date or success rate is promised.
