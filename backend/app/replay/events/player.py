from dataclasses import dataclass
from enum import StrEnum


class PlayerResult(StrEnum):
    WIN = "win"
    LOSS = "loss"
    TIE = "tie"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PlayerInfo:
    player_id: int
    name: str
    race: str
    result: PlayerResult = PlayerResult.UNKNOWN
