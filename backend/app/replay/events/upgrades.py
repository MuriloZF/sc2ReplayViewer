from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpgradeEvent:
    game_loop: int
    player_id: int
    upgrade_type: str
