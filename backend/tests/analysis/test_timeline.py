from backend.app.analysis import (
    BuildOrderCategory,
    extract_build_order,
    extract_feature_rows,
    extract_timeline,
)
from backend.app.replay.decoder.models import DecodedReplay, ReplayMetadata
from backend.app.replay.events import (
    PlayerEconomyEvent,
    PlayerInfo,
    UnitEvent,
    UnitEventKind,
    UnitPosition,
    UpgradeEvent,
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
            UnitEvent(20, UnitEventKind.BORN, 3, "Larva", 1, UnitPosition(11, 21)),
            UnitEvent(100, UnitEventKind.STARTED, 2, "Barracks", 1, UnitPosition(12, 22)),
            UnitEvent(120, UnitEventKind.BORN, 4, "Marine", 1, UnitPosition(13, 23)),
            UnitEvent(130, UnitEventKind.STARTED, 5, "Stalker", 1, UnitPosition(14, 24)),
            UnitEvent(140, UnitEventKind.BORN, 5, "Stalker", 1, UnitPosition(14, 24)),
            UnitEvent(200, UnitEventKind.DIED, 1, "SCV", 1),
        ),
        economy_events=(
            PlayerEconomyEvent(0, 1, 50, 0, 12, 15, 0, 12),
            PlayerEconomyEvent(112, 1, 125, 25, 15, 23, 3, 13),
        ),
        game_events=(),
        upgrade_events=(UpgradeEvent(150, 1, "TerranInfantryWeaponsLevel1"),),
    )


def test_extracts_sampled_timeline_and_features() -> None:
    replay = _replay()

    timeline = extract_timeline(replay)
    rows = extract_feature_rows(replay, timeline)

    assert [frame.game_loop for frame in timeline] == [0, 112, 224]
    assert timeline[1].players[0].minerals == 125
    assert len(timeline[1].players[0].units) == 3
    assert len(timeline[2].players[0].units) == 4
    assert rows[1]["map_name"] == "Test Map"
    assert rows[1]["unit_count"] == 3


def test_extracts_chronological_build_order() -> None:
    entries = extract_build_order(_replay())

    assert [entry.item_name for entry in entries] == [
        "Barracks",
        "Marine",
        "Stalker",
        "Terran Infantry Weapons Level 1",
    ]
    assert entries[0].action == "started"
    assert entries[0].category is BuildOrderCategory.STRUCTURE
    assert entries[0].supply == 12
    assert entries[1].category is BuildOrderCategory.UNIT
    assert entries[1].supply == 15
    assert entries[2].category is BuildOrderCategory.UNIT
    assert entries[3].category is BuildOrderCategory.UPGRADE
