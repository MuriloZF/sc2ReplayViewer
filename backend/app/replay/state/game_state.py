from dataclasses import dataclass, field

from backend.app.replay.events import PlayerEconomyEvent, UnitEvent, UnitEventKind, UnitPosition


@dataclass(frozen=True, slots=True)
class UnitState:
    unit_tag: int
    unit_type: str
    player_id: int | None
    position: UnitPosition | None
    completed: bool


@dataclass(slots=True)
class GameState:
    game_loop: int = 0
    units: dict[int, UnitState] = field(default_factory=dict)
    economy: dict[int, PlayerEconomyEvent] = field(default_factory=dict)

    def apply_unit_event(self, event: UnitEvent) -> None:
        self.game_loop = max(self.game_loop, event.game_loop)
        if event.kind is UnitEventKind.DIED:
            self.units.pop(event.unit_tag, None)
            return

        previous = self.units.get(event.unit_tag)
        self.units[event.unit_tag] = UnitState(
            unit_tag=event.unit_tag,
            unit_type=event.unit_type or (previous.unit_type if previous else "Unknown"),
            player_id=event.player_id if event.player_id is not None else _owner(previous),
            position=event.position or (previous.position if previous else None),
            completed=event.kind in {UnitEventKind.BORN, UnitEventKind.COMPLETED}
            or bool(previous and previous.completed),
        )

    def apply_economy_event(self, event: PlayerEconomyEvent) -> None:
        self.game_loop = max(self.game_loop, event.game_loop)
        self.economy[event.player_id] = event


def _owner(unit: UnitState | None) -> int | None:
    return unit.player_id if unit else None
