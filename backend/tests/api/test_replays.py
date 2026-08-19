import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.analysis import ReplayAnalysis
from backend.app.analysis.build_order import BuildOrderCategory, BuildOrderEntry
from backend.app.api.dependencies import get_map_asset_resolver, get_replay_analyzer
from backend.app.api.routes import replays as replay_routes
from backend.app.main import create_app
from backend.app.replay.decoder.models import DecodedReplay, MapReference, ReplayMetadata
from backend.app.replay.events import PlayerInfo, PlayerResult
from backend.app.replay.map_assets import MapAssetError, MapBounds
from backend.app.replay.state import FrameSnapshot, PlayerSnapshot

DEFAULT_MAP_REFERENCE = MapReference("us", "s2ma", "ab" * 32)


class StubAnalyzer:
    temporary_path: Path | None = None
    sample_seconds: float | None = None

    def __call__(self, path: Path, *, sample_seconds: float) -> ReplayAnalysis:
        self.temporary_path = path
        self.sample_seconds = sample_seconds
        assert path.read_bytes() == b"replay contents"
        return _analysis()


class StubMapAssetResolver:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.references: list[MapReference] = []

    def resolve(self, reference: MapReference) -> Path:
        self.references.append(reference)
        return self.path

    def resolve_bounds(self, reference: MapReference) -> MapBounds:
        self.references.append(reference)
        return MapBounds(168, 168, 12, 17, 156, 147)


def _analysis(
    map_reference: MapReference | None = DEFAULT_MAP_REFERENCE,
) -> ReplayAnalysis:
    replay = DecodedReplay(
        metadata=ReplayMetadata(
            base_build=97_563,
            elapsed_game_loops=224,
            map_name="Test Map",
            players=(PlayerInfo(1, "Alpha", "Terran", PlayerResult.WIN),),
            map_reference=map_reference,
        ),
        unit_events=(),
        economy_events=(),
        game_events=({},),
    )
    player = PlayerSnapshot(1, 100, 25, 20, 31, 5, 15, ())
    return ReplayAnalysis(
        replay=replay,
        timeline=(FrameSnapshot(224, 10.0, (player,)),),
        build_order=(
            BuildOrderEntry(
                1,
                112,
                5.0,
                15,
                "Barracks",
                BuildOrderCategory.STRUCTURE,
                "started",
            ),
        ),
        feature_rows=({"player_id": 1},),
    )


def test_upload_and_read_replay_analysis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def run_direct(function: Callable[..., Any], *args: object) -> Any:
        return function(*args)

    monkeypatch.setattr(replay_routes, "run_in_threadpool", run_direct)

    async def scenario() -> None:
        application = create_app()
        analyzer = StubAnalyzer()
        minimap_path = tmp_path / "minimap.png"
        minimap_path.write_bytes(b"png image")
        map_resolver = StubMapAssetResolver(minimap_path)

        async def get_stub_analyzer() -> StubAnalyzer:
            return analyzer

        async def get_stub_map_resolver() -> StubMapAssetResolver:
            return map_resolver

        application.dependency_overrides[get_replay_analyzer] = get_stub_analyzer
        application.dependency_overrides[get_map_asset_resolver] = get_stub_map_resolver
        transport = ASGITransport(app=application)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            upload = await client.post(
                "/api/v1/replays?sample_seconds=10",
                files={"replay": ("ladder.SC2Replay", b"replay contents")},
            )
            assert upload.status_code == 201
            summary = upload.json()
            replay_id = summary["replay_id"]
            assert summary["map_name"] == "Test Map"
            assert summary["map_reference"] == {
                "region": "us",
                "archive_type": "s2ma",
                "content_hash": "ab" * 32,
            }
            assert summary["duration_seconds"] == 10
            assert summary["players"][0]["win_probability"] is None
            assert summary["counts"]["game_events"] == 1

            listing = await client.get("/api/v1/replays")
            fetched_summary = await client.get(f"/api/v1/replays/{replay_id}/summary")
            timeline = await client.get(f"/api/v1/replays/{replay_id}/timeline")
            build_order = await client.get(f"/api/v1/replays/{replay_id}/build-order")
            minimap = await client.get(f"/api/v1/replays/{replay_id}/minimap")
            map_metadata = await client.get(f"/api/v1/replays/{replay_id}/map-metadata")

        assert listing.json()["items"][0]["replay_id"] == replay_id
        assert fetched_summary.json() == summary
        assert timeline.json()["samples"][0]["players"][0]["army_supply"] == 5
        assert build_order.json()["entries"][0]["item_name"] == "Barracks"
        assert build_order.json()["entries"][0]["category"] == "structure"
        assert build_order.json()["entries"][0]["supply"] == 15
        assert minimap.content == b"png image"
        assert minimap.headers["content-type"] == "image/png"
        assert "immutable" in minimap.headers["cache-control"]
        assert map_metadata.json()["bounds"]["playable_left"] == 12
        assert map_resolver.references == [DEFAULT_MAP_REFERENCE, DEFAULT_MAP_REFERENCE]
        assert analyzer.sample_seconds == 10
        assert analyzer.temporary_path is not None
        assert not analyzer.temporary_path.exists()

    asyncio.run(scenario())


def test_minimap_reports_missing_reference_and_resolution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_direct(function: Callable[..., Any], *args: object) -> Any:
        return function(*args)

    monkeypatch.setattr(replay_routes, "run_in_threadpool", run_direct)

    class FailingResolver:
        def resolve(self, _reference: MapReference) -> Path:
            raise MapAssetError("depot unavailable")

    async def scenario() -> None:
        application = create_app()
        missing_reference = application.state.replay_store.add(
            "missing.SC2Replay", _analysis(map_reference=None)
        )
        failing_reference = application.state.replay_store.add("failure.SC2Replay", _analysis())

        async def get_failing_resolver() -> FailingResolver:
            return FailingResolver()

        application.dependency_overrides[get_map_asset_resolver] = get_failing_resolver
        transport = ASGITransport(app=application)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            missing = await client.get(
                f"/api/v1/replays/{missing_reference.replay_id}/minimap"
            )
            failed = await client.get(
                f"/api/v1/replays/{failing_reference.replay_id}/minimap"
            )

        assert missing.status_code == 404
        assert missing.json()["detail"] == "Replay does not contain a downloadable map reference"
        assert failed.status_code == 502
        assert "depot unavailable" in failed.json()["detail"]

    asyncio.run(scenario())


def test_replay_api_validation_and_not_found() -> None:
    async def scenario() -> None:
        application = create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            wrong_extension = await client.post(
                "/api/v1/replays",
                files={"replay": ("notes.txt", b"not a replay")},
            )
            empty_replay = await client.post(
                "/api/v1/replays",
                files={"replay": ("empty.SC2Replay", b"")},
            )
            missing = await client.get("/api/v1/replays/unknown/summary")

        assert wrong_extension.status_code == 400
        assert wrong_extension.json()["detail"] == "File must have a .SC2Replay extension"
        assert empty_replay.status_code == 400
        assert empty_replay.json()["detail"] == "Replay file is empty"
        assert missing.status_code == 404

    asyncio.run(scenario())
