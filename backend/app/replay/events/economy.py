from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerEconomyEvent:
    game_loop: int
    player_id: int
    minerals: int
    vespene: int
    supply_used: int
    supply_cap: int
    army_supply: int
    workers: int
