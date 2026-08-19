import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from backend.app.analysis import ReplayAnalysis, analyze_replay
from backend.app.replay.decoder import ReplayDecodeError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sc2-replay-inspect",
        description="Decode a StarCraft II replay and print an analysis report as JSON.",
    )
    parser.add_argument("replay", type=Path, help="Path to a .SC2Replay file")
    parser.add_argument(
        "--sample-seconds",
        type=_positive_float,
        default=5.0,
        help="Timeline interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--include-data",
        action="store_true",
        help="Include timeline, build-order, and feature rows in the JSON output",
    )
    parser.add_argument("--output", type=Path, help="Write JSON to this file instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        analysis = analyze_replay(args.replay, sample_seconds=args.sample_seconds)
        report = analysis_report(analysis, include_data=args.include_data)
    except (ReplayDecodeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(f"{output}\n", encoding="utf-8")
    else:
        print(output)
    return 0


def analysis_report(analysis: ReplayAnalysis, *, include_data: bool = False) -> dict[str, Any]:
    metadata = analysis.replay.metadata
    report: dict[str, Any] = {
        "map_name": metadata.map_name,
        "map_reference": (
            asdict(metadata.map_reference) if metadata.map_reference is not None else None
        ),
        "base_build": metadata.base_build,
        "elapsed_game_loops": metadata.elapsed_game_loops,
        "players": [asdict(player) for player in metadata.players],
        "counts": {
            "unit_events": len(analysis.replay.unit_events),
            "economy_events": len(analysis.replay.economy_events),
            "game_events": len(analysis.replay.game_events),
            "timeline_samples": len(analysis.timeline),
            "build_order_entries": len(analysis.build_order),
            "feature_rows": len(analysis.feature_rows),
        },
    }
    if include_data:
        report["timeline"] = [asdict(frame) for frame in analysis.timeline]
        report["build_order"] = [asdict(entry) for entry in analysis.build_order]
        report["feature_rows"] = analysis.feature_rows
    return report


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
