from dataclasses import dataclass
from typing import Any

from backend.app.replay.events import PlayerEconomyEvent, PlayerInfo, UnitEvent, UpgradeEvent

RawEvent = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReplayMetadata:
    base_build: int
    elapsed_game_loops: int
    map_name: str
    players: tuple[PlayerInfo, ...]


@dataclass(frozen=True, slots=True)
class DecodedReplay:
    metadata: ReplayMetadata
    unit_events: tuple[UnitEvent, ...]
    economy_events: tuple[PlayerEconomyEvent, ...]
    game_events: tuple[RawEvent, ...]
    upgrade_events: tuple[UpgradeEvent, ...] = ()
