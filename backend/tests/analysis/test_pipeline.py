from pathlib import Path

from backend.app.analysis import analyze_replay
from backend.app.cli import analysis_report
from backend.app.replay.decoder.models import DecodedReplay, ReplayMetadata
from backend.app.replay.events import PlayerInfo


class StubDecoder:
    def __init__(self, replay: DecodedReplay) -> None:
        self.replay = replay

    def decode(self, _replay_path: str | Path) -> DecodedReplay:
        return self.replay


def test_analyzes_replay_and_builds_summary_report() -> None:
    replay = DecodedReplay(
        metadata=ReplayMetadata(
            base_build=97_563,
            elapsed_game_loops=224,
            map_name="Test Map",
            players=(PlayerInfo(1, "Alpha", "Terran"),),
        ),
        unit_events=(),
        economy_events=(),
        game_events=(),
    )

    analysis = analyze_replay("unused.SC2Replay", decoder=StubDecoder(replay))
    report = analysis_report(analysis)

    assert report["map_name"] == "Test Map"
    assert report["players"] == [
        {"player_id": 1, "name": "Alpha", "race": "Terran", "result": "unknown"}
    ]
    assert report["counts"] == {
        "unit_events": 0,
        "economy_events": 0,
        "game_events": 0,
        "timeline_samples": 3,
        "build_order_entries": 0,
        "feature_rows": 0,
    }
