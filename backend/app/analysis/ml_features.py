from collections import Counter
from typing import Any

from backend.app.analysis.name_normalization import canonicalize_unit_name
from backend.app.replay.decoder import DecodedReplay
from backend.app.replay.events import PlayerInfo, PlayerResult
from backend.app.replay.state import FrameSnapshot, PlayerSnapshot

type MlStateRow = dict[str, Any]


class UnsupportedTrainingReplay(ValueError):
    """Raised when a replay cannot provide an unambiguous 1v1 winner label."""


def extract_ml_state_rows(
    replay: DecodedReplay,
    timeline: tuple[FrameSnapshot, ...],
    *,
    match_id: str,
    tournament: str,
) -> tuple[MlStateRow, ...]:
    """Build compact, labeled match-state rows for offline model training."""

    player_one, player_two = _training_players(replay.metadata.players)
    snapshots: list[tuple[FrameSnapshot, dict[int, PlayerSnapshot]]] = []
    for frame in timeline:
        players = _players_by_id(frame)
        if {player_one.player_id, player_two.player_id} <= set(players):
            snapshots.append((frame, players))
    if not snapshots:
        raise UnsupportedTrainingReplay("timeline does not contain both players")
    snapshots = _trim_uninitialized_opening(snapshots, player_one.player_id, player_two.player_id)

    player_one_race = _canonical_race(player_one, snapshots)
    player_two_race = _canonical_race(player_two, snapshots)

    upgrades = {player_one.player_id: set[str](), player_two.player_id: set[str]()}
    ordered_upgrades = iter(sorted(replay.upgrade_events, key=lambda event: event.game_loop))
    next_upgrade = next(ordered_upgrades, None)
    sample_weight = 1.0 / len(snapshots)
    rows: list[MlStateRow] = []

    for frame, players in snapshots:
        while next_upgrade is not None and next_upgrade.game_loop <= frame.game_loop:
            if next_upgrade.player_id in upgrades and _is_gameplay_upgrade(
                next_upgrade.upgrade_type
            ):
                upgrades[next_upgrade.player_id].add(next_upgrade.upgrade_type)
            next_upgrade = next(ordered_upgrades, None)

        row: MlStateRow = {
            "match_id": match_id,
            "tournament": tournament,
            "map_name": replay.metadata.map_name,
            "map_id": _map_id(replay),
            "base_build": replay.metadata.base_build,
            "game_loop": frame.game_loop,
            "game_time_seconds": frame.game_time_seconds,
            "p1_race": player_one_race,
            "p2_race": player_two_race,
            "p1_won": player_one.result is PlayerResult.WIN,
            "sample_weight": sample_weight,
        }
        row.update(
            _player_features(
                "p1",
                players[player_one.player_id],
                upgrades[player_one.player_id],
                replay.metadata.base_build,
            )
        )
        row.update(
            _player_features(
                "p2",
                players[player_two.player_id],
                upgrades[player_two.player_id],
                replay.metadata.base_build,
            )
        )
        rows.append(row)
    return tuple(rows)


def _training_players(players: tuple[PlayerInfo, ...]) -> tuple[PlayerInfo, PlayerInfo]:
    if len(players) != 2:
        raise UnsupportedTrainingReplay(f"expected 2 players, found {len(players)}")
    ordered = tuple(sorted(players, key=lambda player: player.player_id))
    results = {player.result for player in ordered}
    if results != {PlayerResult.WIN, PlayerResult.LOSS}:
        raise UnsupportedTrainingReplay("match does not contain exactly one winner and one loser")
    return ordered[0], ordered[1]


def _players_by_id(frame: FrameSnapshot) -> dict[int, PlayerSnapshot]:
    return {player.player_id: player for player in frame.players}


def _player_features(
    prefix: str, player: PlayerSnapshot, upgrades: set[str], base_build: int
) -> dict[str, object]:
    completed: Counter[str] = Counter()
    in_progress: Counter[str] = Counter()
    modes: Counter[str] = Counter()
    for unit in player.units:
        canonical = canonicalize_unit_name(unit.unit_type, base_build=base_build)
        destination = completed if unit.completed else in_progress
        destination[canonical.name] += 1
        if canonical.mode is not None:
            modes[f"{canonical.name}:{canonical.mode}"] += 1
    return {
        f"{prefix}_minerals": player.minerals,
        f"{prefix}_vespene": player.vespene,
        f"{prefix}_supply_used": player.supply_used,
        f"{prefix}_supply_cap": min(player.supply_cap, 200.0),
        f"{prefix}_supply_capacity": player.supply_cap,
        f"{prefix}_army_supply": player.army_supply,
        f"{prefix}_workers": player.workers,
        f"{prefix}_unit_counts": dict(sorted(completed.items())),
        f"{prefix}_in_progress_counts": dict(sorted(in_progress.items())),
        f"{prefix}_unit_modes": dict(sorted(modes.items())),
        f"{prefix}_upgrades": sorted(upgrades),
    }


def _trim_uninitialized_opening(
    snapshots: list[tuple[FrameSnapshot, dict[int, PlayerSnapshot]]],
    player_one_id: int,
    player_two_id: int,
) -> list[tuple[FrameSnapshot, dict[int, PlayerSnapshot]]]:
    for index, (_frame, players) in enumerate(snapshots):
        if players[player_one_id].supply_cap > 0 and players[player_two_id].supply_cap > 0:
            return snapshots[index:]
    raise UnsupportedTrainingReplay("timeline does not contain initialized economy data")


def _canonical_race(
    player: PlayerInfo,
    snapshots: list[tuple[FrameSnapshot, dict[int, PlayerSnapshot]]],
) -> str:
    normalized = player.race.casefold()
    translations = {
        "protoss": "Protoss",
        "terran": "Terran",
        "zerg": "Zerg",
        "프로토스": "Protoss",
        "테란": "Terran",
        "저그": "Zerg",
    }
    if normalized in translations:
        return translations[normalized]

    unit_types = {
        unit.unit_type
        for _frame, players in snapshots
        for unit in players[player.player_id].units
    }
    for race, identifiers in (
        ("Terran", {"SCV", "CommandCenter"}),
        ("Zerg", {"Drone", "Hatchery"}),
        ("Protoss", {"Probe", "Nexus"}),
    ):
        if unit_types & identifiers:
            return race
    raise UnsupportedTrainingReplay(f"unable to identify race for player {player.player_id}")


def _is_gameplay_upgrade(upgrade_type: str) -> bool:
    return not (
        upgrade_type.startswith(("RewardDance", "Spray")) or upgrade_type.endswith("Skin")
    )


def _map_id(replay: DecodedReplay) -> str:
    reference = replay.metadata.map_reference
    return reference.content_hash if reference is not None else replay.metadata.map_name.casefold()
