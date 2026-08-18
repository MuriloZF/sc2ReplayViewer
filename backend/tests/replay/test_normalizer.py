from backend.app.replay.decoder.normalizer import normalize_tracker_events
from backend.app.replay.events import UnitEventKind


def test_normalizes_unit_and_economy_events() -> None:
    tracker_events = [
        {
            "_event": "NNet.Replay.Tracker.SUnitBornEvent",
            "_gameloop": 12,
            "m_unitTagIndex": 4,
            "m_unitTagRecycle": 2,
            "m_unitTypeName": b"SCV",
            "m_controlPlayerId": 1,
            "m_x": 32,
            "m_y": 48,
        },
        {
            "_event": "NNet.Replay.Tracker.SPlayerStatsEvent",
            "_gameloop": 16,
            "m_playerId": 1,
            "m_stats": {
                "m_scoreValueMineralsCurrent": 50,
                "m_scoreValueVespeneCurrent": 25,
                "m_scoreValueFoodUsed": 61_440,
                "m_scoreValueFoodMade": 92_160,
                "m_scoreValueWorkersActiveCount": 12,
            },
        },
        {
            "_event": "NNet.Replay.Tracker.SUnitBornEvent",
            "_gameloop": 0,
            "m_unitTagIndex": 5,
            "m_unitTypeName": b"BeaconArmy",
            "m_controlPlayerId": 1,
        },
        {
            "_event": "NNet.Replay.Tracker.SUpgradeEvent",
            "_gameloop": 200,
            "m_playerId": 1,
            "m_upgradeTypeName": b"TerranInfantryWeaponsLevel1",
        },
    ]

    units, economy, upgrades = normalize_tracker_events(tracker_events)

    assert units[0].kind is UnitEventKind.BORN
    assert units[0].unit_tag == (4 << 18) | 2
    assert units[0].unit_type == "SCV"
    assert units[0].position is not None
    assert units[0].position.x == 32
    assert economy[0].supply_used == 15
    assert economy[0].supply_cap == 22.5
    assert economy[0].army_supply == 3
    assert economy[0].workers == 12
    assert len(units) == 1
    assert upgrades[0].upgrade_type == "TerranInfantryWeaponsLevel1"
    assert upgrades[0].player_id == 1
