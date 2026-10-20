# Engineering alpha evidence — 0.8.0a1

This is an engineering release candidate for a real-workout pilot, not validated coaching software. Test success is scoped to the cases below.

## Executed evidence

- Automated suite: **78 tests passed**, Linux / CPython 3.12, including actual binary FIT decoding (running and pool length messages), original CSV/TCX/GPX parsing and an actual MCP stdio client/server handshake calling all nine tools.
- Mathematical targets: two-hour run, 7,200 covered seconds, 21,600 m from speed, full-workout HR 147 bpm, first/final 30-minute HR 140/154 bpm; cycling power integral 1,440 kJ; defined efficiency-decline result; native 25 m pool length example gives 50 m and 120 s/100 m.
- Edge cases: irregular sampling, clipped windows, integration partitioning, long gaps, partial channels, zero versus missing, timer/sample pause overlap, distance resets, GPS jumps, invalid zones/windows/numbers, duplicates, no UTC offset, one-sample workouts and track boundaries.
- Privacy/interface cases: consent required and rechecked, wrong-athlete lookup failure, revocation/purge, private POSIX modes, path/symlink refusal, stored-workout integrity, weather opt-in/cache/integrity, malformed imports and structured CLI errors.
- Discovery: Bob's Sunday run over local imports, duplicate Bob/run clarification, athlete timezone rather than UTC date, 23/25-hour DST days, alias removal on revocation. It does not test a Strava account connection.
- Weather: offline known-answer provider fixtures plus a successful live Open-Meteo ERA5 smoke test for a synthetic route on 2025-06-01. Five route anchors matched; the first returned grid was approximately 16.63 km from the anchor. No athlete coordinates were used. Unit tests are offline and do not depend on that provider response remaining unchanged.
- Skill forward trial: an independent fresh agent used the actual skill and synthetic file to answer first-versus-last-30-minute HR/speed questions, cited coverage/method/source hash and declined to attribute differences to heat without evidence. It executed the engine rather than inventing results. This is one narrow qualitative trial, not a general model-accuracy benchmark.
- Ruff static checks/formatting, skill frontmatter validator, local documentation links and synchronized versions are checked before publication.

Exact principal dependency versions for the executed environment are recorded in [alpha-environment.json](alpha-environment.json). This is an environment record, not a complete transitive lockfile. CI config covers Python 3.10/3.12/3.13 on Ubuntu; its remote results must be inspected separately and are not preclaimed. Windows, macOS and individual AI clients were not executed here.

## Reproduce

```bash
python -m pip install -e '.[dev,mcp]'
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python scripts/check_release.py
```

The generator and tests are original synthetic fixtures. Their formulas/targets are explicitly stated, but they cannot demonstrate real-device accuracy or physiological usefulness. There is no real-athlete ground truth or independent clinical benchmark. No percentage of real-world accuracy is claimed.

## Remaining gates

Real device/export compatibility, authorized athlete pilot, independent coach review, security review appropriate to deployment, licensing selection, and any live provider permission/integration are open. Strava coaching/AI retrieval is specifically gated by current platform policy. See [roadmap](ROADMAP.md), [privacy](PRIVACY.md) and [Strava](STRAVA.md). No open gate is silently converted to a pass by the alpha version number.
