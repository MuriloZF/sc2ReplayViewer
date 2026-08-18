import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.analysis import ReplayAnalysis
from backend.app.analysis.build_order import BuildOrderCategory, BuildOrderEntry
from backend.app.api.dependencies import get_replay_analyzer
from backend.app.api.routes import replays as replay_routes
from backend.app.main import create_app
from backend.app.replay.decoder.models import DecodedReplay, ReplayMetadata
from backend.app.replay.events import PlayerInfo, PlayerResult
from backend.app.replay.state import FrameSnapshot, PlayerSnapshot


class StubAnalyzer:
    temporary_path: Path | None = None
    sample_seconds: float | None = None

    def __call__(self, path: Path, *, sample_seconds: float) -> ReplayAnalysis:
        self.temporary_path = path
        self.sample_seconds = sample_seconds
        assert path.read_bytes() == b"replay contents"
        return _analysis()


def _analysis() -> ReplayAnalysis:
    replay = DecodedReplay(
        metadata=ReplayMetadata(
            base_build=97_563,
            elapsed_game_loops=224,
            map_name="Test Map",
            players=(PlayerInfo(1, "Alpha", "Terran", PlayerResult.WIN),),
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


def test_upload_and_read_replay_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_direct(function: Callable[..., Any], *args: object) -> Any:
        return function(*args)

    monkeypatch.setattr(replay_routes, "run_in_threadpool", run_direct)

    async def scenario() -> None:
        application = create_app()
        analyzer = StubAnalyzer()

        async def get_stub_analyzer() -> StubAnalyzer:
            return analyzer

        application.dependency_overrides[get_replay_analyzer] = get_stub_analyzer
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
            assert summary["duration_seconds"] == 10
            assert summary["players"][0]["win_probability"] is None
            assert summary["counts"]["game_events"] == 1

            listing = await client.get("/api/v1/replays")
            fetched_summary = await client.get(f"/api/v1/replays/{replay_id}/summary")
            timeline = await client.get(f"/api/v1/replays/{replay_id}/timeline")
            build_order = await client.get(f"/api/v1/replays/{replay_id}/build-order")

        assert listing.json()["items"][0]["replay_id"] == replay_id
        assert fetched_summary.json() == summary
        assert timeline.json()["samples"][0]["players"][0]["army_supply"] == 5
        assert build_order.json()["entries"][0]["item_name"] == "Barracks"
        assert build_order.json()["entries"][0]["category"] == "structure"
        assert build_order.json()["entries"][0]["supply"] == 15
        assert analyzer.sample_seconds == 10
        assert analyzer.temporary_path is not None
        assert not analyzer.temporary_path.exists()

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
