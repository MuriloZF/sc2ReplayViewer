from collections.abc import Callable
from pathlib import Path
from typing import cast

from fastapi import Request

from backend.app.analysis import ReplayAnalysis, analyze_replay
from backend.app.api.store import InMemoryReplayStore

type ReplayAnalyzer = Callable[..., ReplayAnalysis]


async def get_replay_store(request: Request) -> InMemoryReplayStore:
    return cast(InMemoryReplayStore, request.app.state.replay_store)


async def get_replay_analyzer() -> ReplayAnalyzer:
    return analyze_replay


def run_analysis(analyzer: ReplayAnalyzer, path: Path, sample_seconds: float) -> ReplayAnalysis:
    return analyzer(path, sample_seconds=sample_seconds)
