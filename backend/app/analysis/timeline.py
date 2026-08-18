from backend.app.replay.decoder import DecodedReplay
from backend.app.replay.state import FrameSnapshot, reconstruct_timeline


def extract_timeline(
    replay: DecodedReplay, *, sample_seconds: float = 5.0
) -> tuple[FrameSnapshot, ...]:
    """Create regularly sampled player and unit state from decoded replay events."""

    return reconstruct_timeline(
        replay.unit_events,
        replay.economy_events,
        elapsed_game_loops=replay.metadata.elapsed_game_loops,
        sample_seconds=sample_seconds,
    )
