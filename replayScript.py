from pathlib import Path

from backend.app.dataset_cli import main as export_dataset

REPLAYS_ROOT = Path("Replays")
REPORTS_ROOT = Path("Reports")


def main() -> int:
    tournament = input("Tournament folder: ").strip()

    replay_dir = REPLAYS_ROOT / tournament

    if not replay_dir.is_dir():
        print(f"ERROR: Tournament folder not found: {replay_dir}")
        return 1

    replays = sorted(replay_dir.glob("*.SC2Replay"))

    if not replays:
        print(f"No .SC2Replay files found in {replay_dir}")
        return 1

    output_dir = REPORTS_ROOT / "ML" / tournament
    print(f"\nFound {len(replays)} replays in {tournament}.\n")
    return export_dataset(
        [
            str(replay_dir),
            str(output_dir),
            "--tournament",
            tournament,
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
