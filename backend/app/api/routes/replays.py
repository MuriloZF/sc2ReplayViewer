import os
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from starlette.concurrency import run_in_threadpool

from backend.app.analysis import ReplayAnalysis
from backend.app.api.dependencies import (
    ReplayAnalyzer,
    get_map_asset_resolver,
    get_replay_analyzer,
    get_replay_store,
    run_analysis,
)
from backend.app.api.schemas import (
    ApiErrorResponse,
    BuildOrderEntryResponse,
    BuildOrderResponse,
    FrameSnapshotResponse,
    MapBoundsResponse,
    MapReferenceResponse,
    PlayerResponse,
    ReplayCountsResponse,
    ReplayListResponse,
    ReplayMapMetadataResponse,
    ReplaySummaryResponse,
    TimelineResponse,
)
from backend.app.api.store import InMemoryReplayStore, ReplayRecord
from backend.app.replay.decoder import MapReference, ReplayDecodeError
from backend.app.replay.map_assets import MapAssetError, MapAssetResolver
from backend.app.replay.state.reconstructor import LOOPS_PER_SECOND

router = APIRouter(prefix="/replays")
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024

StoreDependency = Annotated[InMemoryReplayStore, Depends(get_replay_store)]
AnalyzerDependency = Annotated[ReplayAnalyzer, Depends(get_replay_analyzer)]
MapResolverDependency = Annotated[MapAssetResolver, Depends(get_map_asset_resolver)]


@router.post(
    "",
    response_model=ReplaySummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and analyze a replay",
    description=(
        "Accepts one `.SC2Replay` file, analyzes it, and retains the result in process memory. "
        "The uploaded file is deleted immediately after analysis."
    ),
    responses={400: {"model": ApiErrorResponse}, 413: {"model": ApiErrorResponse}},
)
async def upload_replay(
    store: StoreDependency,
    analyzer: AnalyzerDependency,
    replay: Annotated[UploadFile, File(description="StarCraft II `.SC2Replay` file")],
    sample_seconds: Annotated[float, Query(gt=0, le=60)] = 5.0,
) -> ReplaySummaryResponse:
    filename = replay.filename or "replay.SC2Replay"
    if Path(filename).suffix.lower() != ".sc2replay":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File must have a .SC2Replay extension")

    temporary_path: Path | None = None
    try:
        temporary_path = await _write_temporary_replay(replay)
        analysis = await run_in_threadpool(run_analysis, analyzer, temporary_path, sample_seconds)
    except ReplayDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    finally:
        await replay.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return _summary(store.add(Path(filename).name, analysis))


@router.get(
    "",
    response_model=ReplayListResponse,
    summary="List analyzed replays",
    description="Lists replay analyses retained by the current API process.",
)
async def list_replays(store: StoreDependency) -> ReplayListResponse:
    return ReplayListResponse(items=[_summary(record) for record in store.list()])


@router.get(
    "/{replay_id}/summary",
    response_model=ReplaySummaryResponse,
    summary="Get replay summary",
    responses={404: {"model": ApiErrorResponse}},
)
async def replay_summary(replay_id: str, store: StoreDependency) -> ReplaySummaryResponse:
    return _summary(_record_or_404(store, replay_id))


@router.get(
    "/{replay_id}/timeline",
    response_model=TimelineResponse,
    summary="Get sampled replay timeline",
    responses={404: {"model": ApiErrorResponse}},
)
async def replay_timeline(replay_id: str, store: StoreDependency) -> TimelineResponse:
    record = _record_or_404(store, replay_id)
    return TimelineResponse(
        replay_id=replay_id,
        samples=[FrameSnapshotResponse.model_validate(frame) for frame in record.analysis.timeline],
    )


@router.get(
    "/{replay_id}/build-order",
    response_model=BuildOrderResponse,
    summary="Get replay build order",
    responses={404: {"model": ApiErrorResponse}},
)
async def replay_build_order(replay_id: str, store: StoreDependency) -> BuildOrderResponse:
    record = _record_or_404(store, replay_id)
    return BuildOrderResponse(
        replay_id=replay_id,
        entries=[
            BuildOrderEntryResponse.model_validate(entry) for entry in record.analysis.build_order
        ],
    )


@router.get(
    "/{replay_id}/minimap",
    response_class=Response,
    summary="Get the replay map minimap",
    description=(
        "Resolves the exact map archive referenced by the replay and returns its minimap as PNG. "
        "The converted image is cached by the map's content hash."
    ),
    responses={
        404: {"model": ApiErrorResponse},
        502: {"model": ApiErrorResponse},
    },
)
async def replay_minimap(
    replay_id: str, store: StoreDependency, resolver: MapResolverDependency
) -> Response:
    record = _record_or_404(store, replay_id)
    reference = record.analysis.replay.metadata.map_reference
    if reference is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Replay does not contain a downloadable map reference"
        )
    try:
        contents = await run_in_threadpool(_resolve_minimap_contents, resolver, reference)
    except MapAssetError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Unable to resolve replay map: {exc}"
        ) from exc
    return Response(
        contents,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get(
    "/{replay_id}/map-metadata",
    response_model=ReplayMapMetadataResponse,
    summary="Get replay map dimensions and playable bounds",
    responses={404: {"model": ApiErrorResponse}, 502: {"model": ApiErrorResponse}},
)
async def replay_map_metadata(
    replay_id: str, store: StoreDependency, resolver: MapResolverDependency
) -> ReplayMapMetadataResponse:
    record = _record_or_404(store, replay_id)
    reference = record.analysis.replay.metadata.map_reference
    if reference is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Replay does not contain a downloadable map reference"
        )
    try:
        bounds = await run_in_threadpool(resolver.resolve_bounds, reference)
    except MapAssetError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"Unable to resolve replay map: {exc}"
        ) from exc
    return ReplayMapMetadataResponse(
        replay_id=replay_id, bounds=MapBoundsResponse.model_validate(bounds)
    )


def _resolve_minimap_contents(resolver: MapAssetResolver, reference: MapReference) -> bytes:
    path = resolver.resolve(reference)
    return path.read_bytes()


async def _write_temporary_replay(upload: UploadFile) -> Path:
    descriptor, raw_path = tempfile.mkstemp(suffix=".SC2Replay")
    path = Path(raw_path)
    size = 0
    try:
        with os.fdopen(descriptor, "wb") as target:
            while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        "Replay file exceeds the 100 MB upload limit",
                    )
                target.write(chunk)
        if size == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Replay file is empty")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _record_or_404(store: InMemoryReplayStore, replay_id: str) -> ReplayRecord:
    record = store.get(replay_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Replay analysis was not found")
    return record


def _summary(record: ReplayRecord) -> ReplaySummaryResponse:
    analysis: ReplayAnalysis = record.analysis
    metadata = analysis.replay.metadata
    return ReplaySummaryResponse(
        replay_id=record.replay_id,
        filename=record.filename,
        created_at=record.created_at,
        map_name=metadata.map_name,
        map_reference=(
            MapReferenceResponse.model_validate(metadata.map_reference)
            if metadata.map_reference is not None
            else None
        ),
        base_build=metadata.base_build,
        elapsed_game_loops=metadata.elapsed_game_loops,
        duration_seconds=metadata.elapsed_game_loops / LOOPS_PER_SECOND,
        players=[PlayerResponse.model_validate(player) for player in metadata.players],
        counts=ReplayCountsResponse(
            unit_events=len(analysis.replay.unit_events),
            economy_events=len(analysis.replay.economy_events),
            game_events=len(analysis.replay.game_events),
            timeline_samples=len(analysis.timeline),
            build_order_entries=len(analysis.build_order),
            feature_rows=len(analysis.feature_rows),
        ),
    )
