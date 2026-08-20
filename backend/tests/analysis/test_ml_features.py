import pytest

from backend.app.analysis.ml_features import (
    UnsupportedTrainingReplay,
    extract_ml_state_rows,
)
from backend.app.replay.decoder import DecodedReplay, ReplayMetadata
from backend.app.replay.events import PlayerInfo, PlayerResult, UpgradeEvent
from backend.app.replay.state import FrameSnapshot, PlayerSnapshot, UnitState


def test_extracts_both_players_into_labeled_sparse_rows() -> None:
    replay = _replay()
    marine = UnitState(1, "Marine", 1, None, True)
    barracks = UnitState(2, "Barracks", 1, None, False)
    zergling = UnitState(3, "Zergling", 2, None, True)
    timeline = (
        FrameSnapshot(
            0,
            0,
            (
                PlayerSnapshot(1, 50, 0, 12, 15, 0, 12, ()),
                PlayerSnapshot(2, 50, 0, 12, 14, 0, 12, ()),
            ),
        ),
        FrameSnapshot(
            112,
            5,
            (
                PlayerSnapshot(1, 100, 25, 20, 31, 5, 15, (marine, barracks)),
                PlayerSnapshot(2, 80, 10, 18, 22, 4, 14, (zergling,)),
            ),
        ),
    )

    rows = extract_ml_state_rows(
        replay, timeline, match_id="match", tournament="IEM9 Taipei"
    )

    assert len(rows) == 2
    assert rows[1]["p1_won"] is True
    assert rows[1]["p1_unit_counts"] == {"Marine": 1}
    assert rows[1]["p1_in_progress_counts"] == {"Barracks": 1}
    assert rows[1]["p2_unit_counts"] == {"Zergling": 1}
    assert rows[1]["p1_upgrades"] == ["Stimpack"]
    assert "p1_unit_count" not in rows[1]
    assert sum(float(row["sample_weight"]) for row in rows) == pytest.approx(1)


def test_removes_uninitialized_opening_and_normalizes_races() -> None:
    replay = _replay(
        players=(
            PlayerInfo(1, "Alpha", "저그", PlayerResult.WIN),
            PlayerInfo(2, "Beta", "프로토스", PlayerResult.LOSS),
        )
    )
    drone = UnitState(1, "Drone", 1, None, True)
    probe = UnitState(2, "Probe", 2, None, True)
    timeline = (
        FrameSnapshot(
            0,
            0,
            (
                PlayerSnapshot(1, 0, 0, 0, 0, 0, 0, (drone,)),
                PlayerSnapshot(2, 0, 0, 0, 0, 0, 0, (probe,)),
            ),
        ),
        FrameSnapshot(
            112,
            5,
            (
                PlayerSnapshot(1, 50, 0, 6, 10, 0, 6, (drone,)),
                PlayerSnapshot(2, 50, 0, 6, 15, 0, 6, (probe,)),
            ),
        ),
    )

    rows = extract_ml_state_rows(replay, timeline, match_id="match", tournament="test")

    assert len(rows) == 1
    assert rows[0]["game_time_seconds"] == 5
    assert rows[0]["p1_race"] == "Zerg"
    assert rows[0]["p2_race"] == "Protoss"


def test_rejects_replay_without_clear_1v1_result() -> None:
    replay = _replay(
        players=(
            PlayerInfo(1, "Alpha", "Terran", PlayerResult.UNKNOWN),
            PlayerInfo(2, "Beta", "Zerg", PlayerResult.UNKNOWN),
        )
    )

    with pytest.raises(UnsupportedTrainingReplay, match="one winner"):
        extract_ml_state_rows(replay, (), match_id="match", tournament="test")


def _replay(*, players: tuple[PlayerInfo, ...] | None = None) -> DecodedReplay:
    return DecodedReplay(
        metadata=ReplayMetadata(
            base_build=97_563,
            elapsed_game_loops=112,
            map_name="Test Map",
            players=players
            or (
                PlayerInfo(1, "Alpha", "Terran", PlayerResult.WIN),
                PlayerInfo(2, "Beta", "Zerg", PlayerResult.LOSS),
            ),
        ),
        unit_events=(),
        economy_events=(),
        game_events=(),
        upgrade_events=(
            UpgradeEvent(0, 1, "RewardDanceMule"),
            UpgradeEvent(0, 1, "MarineSkin"),
            UpgradeEvent(100, 1, "Stimpack"),
        ),
    )
