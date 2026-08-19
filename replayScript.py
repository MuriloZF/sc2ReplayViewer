from pathlib import Path
import subprocess


REPLAYS_ROOT = Path("Replays")
REPORTS_ROOT = Path("Reports")


def main():
    tournament = input("Tournament folder: ").strip()

    replay_dir = REPLAYS_ROOT / tournament

    if not replay_dir.is_dir():
        print(f"ERROR: Tournament folder not found: {replay_dir}")
        return

    replays = sorted(replay_dir.glob("*.SC2Replay"))

    if not replays:
        print(f"No .SC2Replay files found in {replay_dir}")
        return

    # Creates Reports/ if it doesn't exist.
    # Does nothing if it already exists.
    REPORTS_ROOT.mkdir(exist_ok=True)

    # Creates Reports/<tournament>/ if it doesn't exist.
    # Does nothing if it already exists.
    output_dir = REPORTS_ROOT / tournament
    output_dir.mkdir(exist_ok=True)

    print(f"\nFound {len(replays)} replays in {tournament}.\n")

    successful = 0
    failed = 0

    for index, replay in enumerate(replays, start=1):
        output_file = output_dir / f"{replay.stem}.json"

        print(f"[{index}/{len(replays)}] Processing {replay.name}")

        command = [
            "sc2-replay-inspect",
            str(replay),
            "--include-data",
            "--output",
            str(output_file),
        ]

        try:
            subprocess.run(command, check=True)
            successful += 1
            print(f"    -> {output_file}")

        except subprocess.CalledProcessError as exc:
            failed += 1
            print(f"    FAILED: {exc}")

        except FileNotFoundError:
            print("ERROR: sc2-replay-inspect was not found in PATH.")
            return

    print("\nFinished.")
    print(f"Successful: {successful}")
    print(f"Failed:     {failed}")
    print(f"Reports:    {output_dir}")


if __name__ == "__main__":
    main()
