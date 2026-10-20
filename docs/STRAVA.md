# “Show me Bob's Sunday run”

## Implemented alpha workflow

The AI maps that request to `find_athlete_workouts(athlete_alias="Bob", day="Sunday", sport="running")`. A consented local roster resolves the alias and athlete timezone. Calendar matching handles UTC conversion and daylight saving. Duplicate Bobs or multiple runs return candidates for clarification; no arbitrary choice is made. One match returns its workout ID for follow-up analysis. Multisport files require selecting the running segment.

This searches **already imported authorized local files**. It does not fetch from Strava. No Strava API credentials are collected or used.

```bash
python -m open_endurance_coaching.cli bind-alias --workspace private --athlete athlete01 --alias Bob --timezone America/Chicago
python -m open_endurance_coaching.cli find --workspace private --athlete Bob --day Sunday --sport running
```

First authorize and ingest as described in the coach guide. Bare weekdays mean the most recent occurrence including today in the athlete timezone; “last Sunday” means strictly before today. Results disclose the chosen date and rule. Use an explicit date whenever the intended week differs. Aliases are sensitive local roster data and are removed on workspace revocation.

## Live Strava gate — reviewed 2026-10-20 UTC

The current [API Policy](https://www.strava.com/legal/api_policy), sections 5.3 and 5.16, restricts AI use of ordinary API data (including derived/context-window data) and third-party MCP/agent interfaces. Section 3.5 limits Strava's own MCP to personal use of one's own data, excluding commercial/third-party access. Display and retention provisions also affect a coaching deployment; sections 2.3, 6.1 and the [API Agreement](https://www.strava.com/legal/api) require careful reconciliation.

Therefore ordinary OAuth consent is not treated as sufficient permission for this product. Live coaching retrieval remains disabled pending an applicable written arrangement/clarification from Strava. The technical [activity/stream endpoints](https://developers.strava.com/docs/reference/) and [OAuth documentation](https://developers.strava.com/docs/authentication/) do not themselves grant those usage rights. No scraping, token sharing, API-data laundering or proxy workaround is implemented. Athlete-original device files supplied with authorization are a separate intake path; do not assume changing an API payload into CSV removes restrictions.
