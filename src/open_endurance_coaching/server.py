"""Optional MCP stdio adapter; no HTTP listener, arbitrary file reads, or mutation tools."""

import argparse
from .workspace import Workspace
from .analysis import analyze, compare, zones, drift, lap_reports


def build_server(root):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "Install open-endurance-coaching[mcp] for MCP support"
        ) from exc
    ws = Workspace(root)
    server = FastMCP("Open Endurance Coaching engineering alpha")

    @server.tool()
    def workout_summary(
        athlete_id: str,
        workout_id: str,
        start_seconds: float = 0,
        end_seconds: float | None = None,
        max_gap_seconds: float = 30,
    ) -> dict:
        """Summarize a consented local workout window. Times are elapsed seconds from first sample."""
        return analyze(
            ws.load(athlete_id, workout_id), start_seconds, end_seconds, max_gap_seconds
        )

    @server.tool()
    def compare_windows(
        athlete_id: str,
        workout_id: str,
        first_start: float,
        first_end: float,
        second_start: float,
        second_end: float,
    ) -> dict:
        """Compare specified elapsed windows, including coverage and numeric change."""
        return compare(
            ws.load(athlete_id, workout_id),
            (first_start, first_end),
            (second_start, second_end),
        )

    @server.tool()
    def time_in_zones(
        athlete_id: str,
        workout_id: str,
        channel: str,
        boundaries: list[float],
        start_seconds: float = 0,
        end_seconds: float | None = None,
    ) -> dict:
        """Use coach-supplied absolute zone boundaries; never derive thresholds from age."""
        return zones(
            ws.load(athlete_id, workout_id),
            channel,
            boundaries,
            start_seconds,
            end_seconds,
        )

    @server.tool()
    def efficiency_drift(
        athlete_id: str,
        workout_id: str,
        channel: str = "speed_m_s",
        start_seconds: float = 0,
        end_seconds: float | None = None,
    ) -> dict:
        """Descriptive output/HR efficiency change; only use on coach-confirmed steady windows."""
        return drift(
            ws.load(athlete_id, workout_id), channel, start_seconds, end_seconds
        )

    @server.tool()
    def workout_laps(athlete_id: str, workout_id: str) -> list[dict]:
        """Return lap and contiguous sport segment summaries."""
        return lap_reports(ws.load(athlete_id, workout_id))

    @server.tool()
    def athlete_history(athlete_id: str) -> list[dict]:
        """Read one authorized athlete's local workout history."""
        return ws.history(athlete_id)

    @server.tool()
    def compare_workouts(
        athlete_id: str, first_workout_id: str, second_workout_id: str
    ) -> dict:
        """Compare two workouts belonging to the same consented athlete."""
        return ws.compare_history(athlete_id, first_workout_id, second_workout_id)

    @server.tool()
    def find_athlete_workouts(
        athlete_alias: str,
        day: str,
        sport: str = "running",
        athlete_id: str | None = None,
    ) -> dict:
        """Find an authorized local athlete's workout by alias and calendar day, e.g. Bob, Sunday, running. Not a live Strava fetch. Clarify ambiguous matches."""
        from .discovery import find_workouts

        return find_workouts(ws, athlete_alias, day, sport, athlete_id=athlete_id)

    @server.tool()
    def weekly_volume(athlete_id: str) -> dict:
        """Return descriptive weekly volume over locally ingested workouts only."""
        return ws.weekly_totals(athlete_id)

    return server


def main():
    p = argparse.ArgumentParser(description="Local single-user MCP stdio server")
    p.add_argument("--workspace", required=True)
    args = p.parse_args()
    build_server(args.workspace).run(transport="stdio")


if __name__ == "__main__":
    main()
