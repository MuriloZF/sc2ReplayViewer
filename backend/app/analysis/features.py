from dataclasses import asdict

from backend.app.replay.decoder import DecodedReplay
from backend.app.replay.state import FrameSnapshot

type FeatureValue = int | float | str
type FeatureRow = dict[str, FeatureValue]


def extract_feature_rows(
    replay: DecodedReplay, timeline: tuple[FrameSnapshot, ...]
) -> tuple[FeatureRow, ...]:
    """Flatten timeline samples into rows suitable for persistence or ML export."""

    rows: list[FeatureRow] = []
    for frame in timeline:
        for player in frame.players:
            row: FeatureRow = {
                "base_build": replay.metadata.base_build,
                "map_name": replay.metadata.map_name,
                "game_loop": frame.game_loop,
                "game_time_seconds": frame.game_time_seconds,
                "player_id": player.player_id,
                "minerals": player.minerals,
                "vespene": player.vespene,
                "supply_used": player.supply_used,
                "supply_cap": player.supply_cap,
                "army_supply": player.army_supply,
                "workers": player.workers,
                "unit_count": len(player.units),
            }
            rows.append(row)
    return tuple(rows)


def snapshot_dict(frame: FrameSnapshot) -> dict[str, object]:
    """Return a JSON-serializable representation for API and dataset consumers."""

    return asdict(frame)
