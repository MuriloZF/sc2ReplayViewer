import re
from bisect import bisect_right
from dataclasses import dataclass
from enum import StrEnum

from backend.app.replay.decoder import DecodedReplay
from backend.app.replay.events import PlayerEconomyEvent, UnitEvent, UnitEventKind
from backend.app.replay.state.reconstructor import LOOPS_PER_SECOND


class BuildOrderCategory(StrEnum):
    WORKER = "worker"
    STRUCTURE = "structure"
    UNIT = "unit"
    UPGRADE = "upgrade"


@dataclass(frozen=True, slots=True)
class BuildOrderEntry:
    player_id: int
    game_loop: int
    game_time_seconds: float
    supply: int | None
    item_name: str
    category: BuildOrderCategory
    action: str


_WORKER_TYPES = {"Drone", "Probe", "SCV"}
_STRUCTURE_TYPES = {
    "Armory",
    "Assimilator",
    "BanelingNest",
    "Barracks",
    "BarracksReactor",
    "BarracksTechLab",
    "Bunker",
    "CommandCenter",
    "CyberneticsCore",
    "DarkShrine",
    "EngineeringBay",
    "EvolutionChamber",
    "Extractor",
    "Factory",
    "FactoryReactor",
    "FactoryTechLab",
    "FleetBeacon",
    "Forge",
    "FusionCore",
    "Gateway",
    "GhostAcademy",
    "Hatchery",
    "HydraliskDen",
    "InfestationPit",
    "LurkerDenMP",
    "MissileTurret",
    "Nexus",
    "NydusCanal",
    "NydusNetwork",
    "PhotonCannon",
    "Pylon",
    "Refinery",
    "RoachWarren",
    "RoboticsBay",
    "RoboticsFacility",
    "SensorTower",
    "ShieldBattery",
    "SpawningPool",
    "SpineCrawler",
    "Spire",
    "SporeCrawler",
    "Stargate",
    "Starport",
    "StarportReactor",
    "StarportTechLab",
    "SupplyDepot",
    "TemplarArchive",
    "TwilightCouncil",
    "UltraliskCavern",
}
_MEANINGFUL_MORPHS = {
    "Baneling",
    "BroodLord",
    "GreaterSpire",
    "Hive",
    "Lair",
    "LurkerMP",
    "OrbitalCommand",
    "Overseer",
    "PlanetaryFortress",
    "Ravager",
    "WarpPrismPhasing",
}
_EXCLUDED_TYPES = {
    "AdeptPhaseShift",
    "AutoTurret",
    "Broodling",
    "DisruptorPhased",
    "Egg",
    "ForceField",
    "Interceptor",
    "KD8Charge",
    "Larva",
    "LocustMP",
    "LocustMPFlying",
    "MULE",
    "OverlordTransportCocoon",
    "ParasiticBombDummy",
    "RavagerCocoon",
}
_EXCLUDED_PREFIXES = ("Beacon", "Changeling", "CreepTumor")


def extract_build_order(replay: DecodedReplay) -> tuple[BuildOrderEntry, ...]:
    """Extract meaningful production and research events in chronological order."""

    economy_by_player = _economy_by_player(replay.economy_events)
    entries: list[BuildOrderEntry] = []
    started_tags: set[int] = set()
    for event in sorted(replay.unit_events, key=lambda item: item.game_loop):
        if not _include_unit_event(event):
            continue
        if event.kind is UnitEventKind.BORN and event.unit_tag in started_tags:
            continue
        if event.kind is UnitEventKind.STARTED:
            started_tags.add(event.unit_tag)
        entries.append(_unit_entry(event, economy_by_player))
    entries.extend(
        BuildOrderEntry(
            player_id=event.player_id,
            game_loop=event.game_loop,
            game_time_seconds=event.game_loop / LOOPS_PER_SECOND,
            supply=_supply_at(economy_by_player.get(event.player_id, ()), event.game_loop),
            item_name=_humanize(event.upgrade_type),
            category=BuildOrderCategory.UPGRADE,
            action="researched",
        )
        for event in replay.upgrade_events
        if event.player_id > 0
        and event.game_loop > 0
        and not event.upgrade_type.startswith("Spray")
    )
    return tuple(sorted(entries, key=lambda entry: (entry.game_loop, entry.player_id)))


def _include_unit_event(event: UnitEvent) -> bool:
    if event.player_id is None or event.game_loop <= 0 or not event.unit_type:
        return False
    if event.unit_type in _EXCLUDED_TYPES or event.unit_type.startswith(_EXCLUDED_PREFIXES):
        return False
    return event.kind in {UnitEventKind.STARTED, UnitEventKind.BORN} or (
        event.kind is UnitEventKind.TYPE_CHANGED and event.unit_type in _MEANINGFUL_MORPHS
    )


def _unit_entry(
    event: UnitEvent, economy_by_player: dict[int, tuple[PlayerEconomyEvent, ...]]
) -> BuildOrderEntry:
    if event.kind is UnitEventKind.STARTED:
        category = (
            BuildOrderCategory.STRUCTURE
            if event.unit_type in _STRUCTURE_TYPES
            else BuildOrderCategory.UNIT
        )
        action = "started"
    elif event.kind is UnitEventKind.TYPE_CHANGED:
        category = (
            BuildOrderCategory.STRUCTURE
            if _is_structure_morph(event.unit_type)
            else BuildOrderCategory.UNIT
        )
        action = "morphed"
    else:
        category = (
            BuildOrderCategory.WORKER
            if event.unit_type in _WORKER_TYPES
            else BuildOrderCategory.UNIT
        )
        action = "created"
    return BuildOrderEntry(
        player_id=event.player_id or 0,
        game_loop=event.game_loop,
        game_time_seconds=event.game_loop / LOOPS_PER_SECOND,
        supply=_supply_at(economy_by_player.get(event.player_id or 0, ()), event.game_loop),
        item_name=_humanize(event.unit_type),
        category=category,
        action=action,
    )


def _economy_by_player(
    events: tuple[PlayerEconomyEvent, ...],
) -> dict[int, tuple[PlayerEconomyEvent, ...]]:
    grouped: dict[int, list[PlayerEconomyEvent]] = {}
    for event in events:
        grouped.setdefault(event.player_id, []).append(event)
    return {
        player_id: tuple(sorted(player_events, key=lambda item: item.game_loop))
        for player_id, player_events in grouped.items()
    }


def _supply_at(events: tuple[PlayerEconomyEvent, ...], game_loop: int) -> int | None:
    index = bisect_right([event.game_loop for event in events], game_loop) - 1
    return events[index].supply_used if index >= 0 else None


def _is_structure_morph(unit_type: str) -> bool:
    return unit_type in {"GreaterSpire", "Hive", "Lair", "OrbitalCommand", "PlanetaryFortress"}


def _humanize(value: str) -> str:
    with_word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"(?<=\D)(\d+)$", r" \1", with_word_boundaries).replace("MP", "").strip()
