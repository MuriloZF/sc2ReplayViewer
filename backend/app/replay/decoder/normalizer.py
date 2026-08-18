from collections.abc import Iterable, Mapping
from typing import Any

from backend.app.replay.decoder.models import RawEvent
from backend.app.replay.events import (
    PlayerEconomyEvent,
    UnitEvent,
    UnitEventKind,
    UnitPosition,
    UpgradeEvent,
)

_UNIT_EVENT_KINDS = {
    "NNet.Replay.Tracker.SUnitBornEvent": UnitEventKind.BORN,
    "NNet.Replay.Tracker.SUnitInitEvent": UnitEventKind.STARTED,
    "NNet.Replay.Tracker.SUnitDoneEvent": UnitEventKind.COMPLETED,
    "NNet.Replay.Tracker.SUnitDiedEvent": UnitEventKind.DIED,
    "NNet.Replay.Tracker.SUnitTypeChangeEvent": UnitEventKind.TYPE_CHANGED,
    "NNet.Replay.Tracker.SUnitOwnerChangeEvent": UnitEventKind.OWNER_CHANGED,
}


def normalize_tracker_events(
    events: Iterable[RawEvent],
) -> tuple[tuple[UnitEvent, ...], tuple[PlayerEconomyEvent, ...], tuple[UpgradeEvent, ...]]:
    units: list[UnitEvent] = []
    economy: list[PlayerEconomyEvent] = []
    upgrades: list[UpgradeEvent] = []

    for event in events:
        event_type = str(event.get("_event", ""))
        if event_type in _UNIT_EVENT_KINDS:
            unit_event = _normalize_unit_event(event, _UNIT_EVENT_KINDS[event_type])
            if not unit_event.unit_type.startswith("Beacon"):
                units.append(unit_event)
        elif event_type == "NNet.Replay.Tracker.SPlayerStatsEvent":
            economy.append(_normalize_economy_event(event))
        elif event_type == "NNet.Replay.Tracker.SUpgradeEvent":
            upgrades.append(
                UpgradeEvent(
                    game_loop=int(event.get("_gameloop", 0)),
                    player_id=int(event.get("m_playerId", 0)),
                    upgrade_type=_text(event.get("m_upgradeTypeName", "Unknown upgrade")),
                )
            )

    return tuple(units), tuple(economy), tuple(upgrades)


def _normalize_unit_event(event: RawEvent, kind: UnitEventKind) -> UnitEvent:
    unit_tag = _unit_tag(event)
    unit_type = _text(event.get("m_unitTypeName", event.get("m_unitType", "")))
    player_id = _optional_int(event.get("m_controlPlayerId", event.get("m_upkeepPlayerId")))
    position = _position(event)
    return UnitEvent(
        game_loop=int(event.get("_gameloop", 0)),
        kind=kind,
        unit_tag=unit_tag,
        unit_type=unit_type,
        player_id=player_id,
        position=position,
    )


def _normalize_economy_event(event: RawEvent) -> PlayerEconomyEvent:
    stats = event.get("m_stats", {})
    if not isinstance(stats, Mapping):
        stats = {}
    supply_used = _stat(stats, "m_scoreValueFoodUsed") / 4096
    workers = _stat(stats, "m_scoreValueWorkersActiveCount")
    return PlayerEconomyEvent(
        game_loop=int(event.get("_gameloop", 0)),
        player_id=int(event.get("m_playerId", 0)),
        minerals=_stat(stats, "m_scoreValueMineralsCurrent"),
        vespene=_stat(stats, "m_scoreValueVespeneCurrent"),
        supply_used=supply_used,
        supply_cap=_stat(stats, "m_scoreValueFoodMade") / 4096,
        army_supply=_army_supply(stats, supply_used, workers),
        workers=workers,
    )


def _stat(stats: Mapping[str, Any], key: str) -> int:
    value = stats.get(key, 0)
    return int(value) if isinstance(value, int | float) else 0


def _army_supply(stats: Mapping[str, Any], supply_used: float, workers: int) -> float:
    explicit_army_supply = stats.get("m_scoreValueFoodUsedArmy")
    if isinstance(explicit_army_supply, int | float):
        return explicit_army_supply / 4096
    return max(supply_used - workers, 0.0)


def _unit_tag(event: RawEvent) -> int:
    index = int(event.get("m_unitTagIndex", 0))
    recycle = int(event.get("m_unitTagRecycle", 0))
    return (index << 18) | recycle


def _position(event: RawEvent) -> UnitPosition | None:
    x = event.get("m_x")
    y = event.get("m_y")
    if not isinstance(x, int | float) or not isinstance(y, int | float):
        return None
    return UnitPosition(x=float(x), y=float(y))


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) and value > 0 else None


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
