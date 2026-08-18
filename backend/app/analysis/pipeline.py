from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from backend.app.analysis.build_order import BuildOrderEntry, extract_build_order
from backend.app.analysis.features import FeatureRow, extract_feature_rows
from backend.app.analysis.timeline import extract_timeline
from backend.app.replay.decoder import DecodedReplay, S2ProtocolAdapter
from backend.app.replay.state import FrameSnapshot


@dataclass(frozen=True, slots=True)
class ReplayAnalysis:
    replay: DecodedReplay
    timeline: tuple[FrameSnapshot, ...]
    build_order: tuple[BuildOrderEntry, ...]
    feature_rows: tuple[FeatureRow, ...]


class ReplayDecoder(Protocol):
    def decode(self, replay_path: str | Path) -> DecodedReplay: ...


def analyze_replay(
    replay_path: str | Path,
    *,
    sample_seconds: float = 5.0,
    decoder: ReplayDecoder | None = None,
) -> ReplayAnalysis:
    """Decode a replay and run all currently supported analysis stages."""

    decoded = (decoder or S2ProtocolAdapter()).decode(replay_path)
    timeline = extract_timeline(decoded, sample_seconds=sample_seconds)
    return ReplayAnalysis(
        replay=decoded,
        timeline=timeline,
        build_order=extract_build_order(decoded),
        feature_rows=extract_feature_rows(decoded, timeline),
    )
