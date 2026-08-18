from backend.app.analysis import extract_build_order, extract_feature_rows, extract_timeline
from backend.app.replay.decoder.models import DecodedReplay, ReplayMetadata
from backend.app.replay.events import (
    PlayerEconomyEvent,
    PlayerInfo,
    UnitEvent,
    UnitEventKind,
    UnitPosition,
)


def _replay() -> DecodedReplay:
    return DecodedReplay(
        metadata=ReplayMetadata(
            base_build=99_999,
            elapsed_game_loops=224,
            map_name="Test Map",
            players=(PlayerInfo(player_id=1, name="Alpha", race="Terran"),),
        ),
        unit_events=(
            UnitEvent(0, UnitEventKind.BORN, 1, "SCV", 1, UnitPosition(10, 20)),
            UnitEvent(100, UnitEventKind.STARTED, 2, "Barracks", 1, UnitPosition(12, 22)),
            UnitEvent(200, UnitEventKind.DIED, 1, "SCV", 1),
        ),
        economy_events=(
            PlayerEconomyEvent(0, 1, 50, 0, 12, 15, 0, 12),
            PlayerEconomyEvent(112, 1, 125, 25, 15, 23, 3, 13),
        ),
        game_events=(),
    )


def test_extracts_sampled_timeline_and_features() -> None:
    replay = _replay()

    timeline = extract_timeline(replay)
    rows = extract_feature_rows(replay, timeline)

    assert [frame.game_loop for frame in timeline] == [0, 112, 224]
    assert timeline[1].players[0].minerals == 125
    assert len(timeline[1].players[0].units) == 2
    assert len(timeline[2].players[0].units) == 1
    assert rows[1]["map_name"] == "Test Map"
    assert rows[1]["unit_count"] == 2


def test_extracts_chronological_build_order() -> None:
    entries = extract_build_order(_replay())

    assert [entry.item_name for entry in entries] == ["Barracks"]
    assert entries[0].action == "started"
