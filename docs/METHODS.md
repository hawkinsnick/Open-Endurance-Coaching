# Methods and schema — 0.8.0a1

## Canonical inputs

CSV requires `timestamp`, ISO 8601 with explicit UTC offset. Optional numeric channels: `heart_rate_bpm`, `power_w`, `speed_m_s`, `latitude`, `longitude`, `elevation_m`, `cadence_rpm`, `distance_m`. Optional `sport` (running/cycling/swimming/transition/unknown), `lap`, `segment`, `active` (true/false/1/0). Empty cells are missing. Zero power/speed are real zeros; zero HR becomes missing. All numbers must be finite. Negative non-geographic channels and out-of-range coordinates are rejected. HR above 250 is retained with a review warning, not a clinical judgment.

Normalize timestamps to UTC, sort explicitly with a warning, reject duplicates. Pair latitude/longitude. Units are SI except HR and cadence. The legacy name cadence_rpm preserves supplied cycles per minute: FIT, TCX Cadence, TCX RunCadence (strides/min) and CSV may have different conventions. Never silently double cadence or compare it across devices without knowing the convention. GPX Garmin TrackPointExtension HR/cadence is recognized. Unrecognized extensions/developer fields are not interpreted.

Limits: 50 MiB per input, 500,000 samples. XML uses defusedxml; external entities are forbidden. XML is parsed in memory and is not an untrusted multiuser service. FIT CRC and decoder errors fail closed. Length-only FIT files without records are rejected with an explicit explanation. TCX Activities and GPX timed trackpoints are supported, not TCX course-only or untimed routes. Unknown sports map to unknown.

## Integration

For adjacent samples at times t_i and t_(i+1), hold the left value on [t_i,t_(i+1)). Clip to the requested elapsed window. Exclude intervals longer than max_gap (default 30 seconds), across track/session/sport segment boundaries, or where the left sample is inactive. Subtract explicit FIT timer pauses even if they begin inside an interval. No extrapolation beyond the last sample. A single sample has zero duration and no integrated metrics.

For a channel x, time-weighted mean = sum(x_i * eligible_seconds_i) / channel_covered_seconds. Missing channels do not become zeros. Coverage = channel_covered_seconds / expected_active_seconds. Expected active time is elapsed window less explicit timer pauses and inactive sample intervals; unknown gaps remain in its denominator. Values are left-held, not linearly interpolated; sparse sampling is a material modeling assumption. Terminal samples define the final boundary but have zero weight themselves.

Power variability is time-weighted coefficient of variation = standard deviation / mean over covered intervals. It is **not** normalized power or a training stress metric. `mechanical_work_kj` is the integral of recorded watts /1000. Device power may itself be estimated; this is not metabolic energy or calorie expenditure, particularly for running power models.

Moving estimate counts intervals with recorded speed >0.5 m/s; it is neither device moving time nor inferred motion when speed is missing. This is an explicit engineering rule, not a validated physiological threshold.

## Distance and elevation

Prefer device cumulative distance differences, prorated for clipped/paused intervals (uniform movement within that interval is assumed). Reject negative reset intervals; do not invent a reset offset. Otherwise integrate recorded speed; otherwise use haversine GPS distance at Earth mean radius 6,371,008.8 m. GPS segments above 100 m/s are excluded as an engineering quality rule. Report contributing methods and covered seconds; never represent a partial sum as total workout distance. Routes and device distances can include other artifacts not detected automatically.

Ascent sums positive elevation deltas, prorated for eligible intervals. It is unsmoothed and noise-sensitive; absence returns null, not zero. Elevation does not establish terrain-adjusted effort. No grade-adjusted pace is implemented. Route coordinates are omitted from summary JSON unless explicitly requested.

## Zones, segments and drift

Zone boundaries are coach-supplied absolute channel values, increasing, lower inclusive / upper exclusive. Report seconds and missing coverage; no age formula or automatic threshold estimation. Threshold IDs and effective dates are annotations, not a validated physiological profile engine.

Lap reports split contiguous lap, sport and segment runs. Window endpoints correspond to sample timestamps; a final terminal-only lap may have zero duration. Track/session crossings are excluded conservatively rather than bridged. Session and lap assignment uses half-open boundaries, with final terminal samples assigned to the final session/lap.

Efficiency decline uses matched output+HR intervals only: R = mean(output)/mean(HR), separately for two equal elapsed halves. Decline percent = 100*(1 - R_second/R_first). Positive values mean lower output/HR in the second half. The sign/denominator convention is explicit and need not match other products' decoupling definitions. Require a >=20 minute single running/cycling window and >=90% paired **elapsed** coverage in each half (pauses count against it). These are engineering eligibility guards, not validated diagnostic thresholds. Steady intensity must be confirmed by the coach; the engine cannot establish dehydration, fatigue or aerobic fitness from this metric.

## Swimming and history

Native FIT length messages are retained. Pool summaries count fully contained active/idle lengths; distance = active lengths * pool length only when all swimming sessions have one unambiguous available pool length. Active timer sums and strokes are returned only when complete. Pace per 100 m uses active length timers, not elapsed rest time. No swim set inference, SWOLF comparison, stroke correctness or drill correction is claimed. Length summary and sample-integrated distance are distinct estimates and may disagree.

History comparisons operate within one consented athlete ID. They show descriptive changes; they do not automatically match conditions or establish improvement. Optional context stores coach_note, workout_goal, RPE 0-10, threshold_profile, threshold_effective_date. Weekly totals group by ISO UTC week of workout start (a midnight/week crossing is not split). Covered volume can be partial and covers only ingested files, with no completeness claim. No chronic/acute workload ratio, readiness or training stress model is implemented.

## Weather and reproducibility

Opt-in Open-Meteo archive request pins ERA5, UTC, degrees C, humidity %, wind m/s and direction degrees. Select route anchors every 30 minutes or 10 km, maximum 24, rounding request coordinates to two decimals. Match nearest hourly value within 3,600 seconds and 50 km of the returned grid point. ERA5 nominal resolution is 0.25 degrees; actual grid distance is reported. No continuous exposure integration, headwind, WBGT or physiological adjustment is implemented. Recorded route anchors can still lie inside pauses; no full pause-aware exposure model is claimed.

Cache by request hash with retrieval date, provider, original response hash and canonical body integrity hash. Cache is reusable offline, with no automatic expiry; reanalysis can be revised, so archive the response if exact replay is needed. Provider absence, unit mismatch or invalid values fail closed; null values are partial. A failed/partial weather request must never substitute invented weather.

JSON includes engine version, schema version, input SHA-256, parameters, windows, methods and warnings. The compatibility load_csv/summarize Python API retains labeled sample-weighted v0.1 means; production CLI/MCP use analyze and time weighting. Dependencies are range-constrained; exact versions used for alpha validation are recorded separately. Floating-point results should be rounded for display only.
