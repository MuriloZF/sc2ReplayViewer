from collections.abc import Iterable
from dataclasses import dataclass

from backend.app.replay.events import PlayerEconomyEvent, UnitEvent
from backend.app.replay.state.game_state import GameState, UnitState

LOOPS_PER_SECOND = 22.4


@dataclass(frozen=True, slots=True)
class PlayerSnapshot:
    player_id: int
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    army_supply: int
    workers: int
    units: tuple[UnitState, ...]


@dataclass(frozen=True, slots=True)
class FrameSnapshot:
    game_loop: int
    game_time_seconds: float
    players: tuple[PlayerSnapshot, ...]


def reconstruct_timeline(
    unit_events: Iterable[UnitEvent],
    economy_events: Iterable[PlayerEconomyEvent],
    *,
    elapsed_game_loops: int,
    sample_seconds: float = 5.0,
) -> tuple[FrameSnapshot, ...]:
    if sample_seconds <= 0:
        raise ValueError("sample_seconds must be greater than zero")

    # The secondary key keeps unit changes ahead of economy samples at the same loop.
    ordered: list[tuple[int, int, UnitEvent | PlayerEconomyEvent]] = [
        (event.game_loop, 0, event) for event in unit_events
    ]
    ordered.extend((event.game_loop, 1, event) for event in economy_events)
    ordered.sort(key=lambda item: (item[0], item[1]))

    state = GameState()
    snapshots: list[FrameSnapshot] = []
    event_index = 0
    sample_loops = max(1, round(sample_seconds * LOOPS_PER_SECOND))

    for game_loop in range(0, elapsed_game_loops + 1, sample_loops):
        while event_index < len(ordered) and ordered[event_index][0] <= game_loop:
            event = ordered[event_index][2]
            if isinstance(event, UnitEvent):
                state.apply_unit_event(event)
            else:
                state.apply_economy_event(event)
            event_index += 1
        snapshots.append(_snapshot(state, game_loop))

    if not snapshots or snapshots[-1].game_loop != elapsed_game_loops:
        while event_index < len(ordered) and ordered[event_index][0] <= elapsed_game_loops:
            event = ordered[event_index][2]
            if isinstance(event, UnitEvent):
                state.apply_unit_event(event)
            else:
                state.apply_economy_event(event)
            event_index += 1
        snapshots.append(_snapshot(state, elapsed_game_loops))

    return tuple(snapshots)


def _snapshot(state: GameState, game_loop: int) -> FrameSnapshot:
    player_ids = set(state.economy)
    player_ids.update(unit.player_id for unit in state.units.values() if unit.player_id is not None)
    players: list[PlayerSnapshot] = []
    for player_id in sorted(player_ids):
        economy = state.economy.get(player_id)
        units = tuple(unit for unit in state.units.values() if unit.player_id == player_id)
        players.append(
            PlayerSnapshot(
                player_id=player_id,
                minerals=economy.minerals if economy else 0,
                vespene=economy.vespene if economy else 0,
                supply_used=economy.supply_used if economy else 0,
                supply_cap=economy.supply_cap if economy else 0,
                army_supply=economy.army_supply if economy else 0,
                workers=economy.workers if economy else 0,
                units=units,
            )
        )
    return FrameSnapshot(
        game_loop=game_loop,
        game_time_seconds=game_loop / LOOPS_PER_SECOND,
        players=tuple(players),
    )
