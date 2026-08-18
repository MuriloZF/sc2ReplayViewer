from dataclasses import dataclass

from backend.app.replay.decoder import DecodedReplay
from backend.app.replay.events import UnitEventKind
from backend.app.replay.state.reconstructor import LOOPS_PER_SECOND


@dataclass(frozen=True, slots=True)
class BuildOrderEntry:
    player_id: int
    game_loop: int
    game_time_seconds: float
    item_name: str
    action: str


def extract_build_order(replay: DecodedReplay) -> tuple[BuildOrderEntry, ...]:
    """Extract unit and structure production starts in chronological order."""

    entries = [
        BuildOrderEntry(
            player_id=event.player_id,
            game_loop=event.game_loop,
            game_time_seconds=event.game_loop / LOOPS_PER_SECOND,
            item_name=event.unit_type,
            action="started" if event.kind is UnitEventKind.STARTED else "created",
        )
        for event in replay.unit_events
        if event.player_id is not None
        and event.unit_type
        and event.game_loop > 0
        and event.kind in {UnitEventKind.STARTED, UnitEventKind.BORN}
    ]
    return tuple(sorted(entries, key=lambda entry: (entry.game_loop, entry.player_id)))
