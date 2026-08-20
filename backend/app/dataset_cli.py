import argparse
import sys
from pathlib import Path

from backend.app.storage.parquet_export import export_tournament_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sc2-replay-export",
        description="Export a tournament directory as a compact Parquet training dataset.",
    )
    parser.add_argument("replay_dir", type=Path, help="Directory containing .SC2Replay files")
    parser.add_argument(
        "output_dir", type=Path, help="Directory for states.parquet and manifest.json"
    )
    parser.add_argument("--tournament", help="Tournament label (defaults to replay directory name)")
    parser.add_argument(
        "--sample-seconds",
        type=_positive_float,
        default=5.0,
        help="Training-state interval in seconds (default: 5)",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace existing output files")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = export_tournament_dataset(
            args.replay_dir,
            args.output_dir,
            tournament=args.tournament,
            sample_seconds=args.sample_seconds,
            overwrite=args.overwrite,
            progress=lambda index, total, path: print(f"[{index}/{total}] {path.name}"),
        )
    except (FileExistsError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Exported {result.matches} matches and {result.rows} states")
    print(f"Skipped {result.skipped} replays")
    print(f"Dataset: {result.dataset_path}")
    print(f"Manifest: {result.manifest_path}")
    return 0


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
