from dataclasses import dataclass
from enum import StrEnum


class UnitEventKind(StrEnum):
    BORN = "born"
    STARTED = "started"
    COMPLETED = "completed"
    DIED = "died"
    TYPE_CHANGED = "type_changed"
    OWNER_CHANGED = "owner_changed"


@dataclass(frozen=True, slots=True)
class UnitPosition:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class UnitEvent:
    game_loop: int
    kind: UnitEventKind
    unit_tag: int
    unit_type: str
    player_id: int | None
    position: UnitPosition | None = None
