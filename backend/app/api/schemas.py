from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlayerResponse(ApiModel):
    player_id: int
    name: str
    race: str
    result: Literal["win", "loss", "tie", "unknown"]
    win_probability: float | None = None


class ReplayCountsResponse(ApiModel):
    unit_events: int
    economy_events: int
    game_events: int
    timeline_samples: int
    build_order_entries: int
    feature_rows: int


class MapReferenceResponse(ApiModel):
    region: str
    archive_type: str
    content_hash: str


class ReplaySummaryResponse(ApiModel):
    replay_id: str
    filename: str
    created_at: datetime
    map_name: str
    map_reference: MapReferenceResponse | None
    base_build: int
    elapsed_game_loops: int
    duration_seconds: float
    players: list[PlayerResponse]
    counts: ReplayCountsResponse


class ReplayListResponse(ApiModel):
    items: list[ReplaySummaryResponse]


class UnitPositionResponse(ApiModel):
    x: float
    y: float


class UnitStateResponse(ApiModel):
    unit_tag: int
    unit_type: str
    player_id: int | None
    position: UnitPositionResponse | None
    completed: bool


class PlayerSnapshotResponse(ApiModel):
    player_id: int
    minerals: int
    vespene: int
    supply_used: float
    supply_cap: float
    army_supply: float
    workers: int
    units: list[UnitStateResponse]


class FrameSnapshotResponse(ApiModel):
    game_loop: int
    game_time_seconds: float
    players: list[PlayerSnapshotResponse]


class TimelineResponse(ApiModel):
    replay_id: str
    samples: list[FrameSnapshotResponse]


class BuildOrderEntryResponse(ApiModel):
    player_id: int
    game_loop: int
    game_time_seconds: float
    supply: float | None
    item_name: str
    category: Literal["worker", "structure", "unit", "upgrade"]
    action: str


class BuildOrderResponse(ApiModel):
    replay_id: str
    entries: list[BuildOrderEntryResponse]


class MapBoundsResponse(ApiModel):
    width: int
    height: int
    playable_left: int
    playable_bottom: int
    playable_right: int
    playable_top: int


class ReplayMapMetadataResponse(ApiModel):
    replay_id: str
    bounds: MapBoundsResponse


class ApiErrorResponse(BaseModel):
    detail: str = Field(description="Human-readable explanation of the request failure.")
