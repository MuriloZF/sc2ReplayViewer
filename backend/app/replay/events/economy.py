from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerEconomyEvent:
    game_loop: int
    player_id: int
    minerals: int
    vespene: int
    supply_used: float
    supply_cap: float
    army_supply: float
    workers: int
