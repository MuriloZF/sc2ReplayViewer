from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from backend.app.analysis import ReplayAnalysis


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    replay_id: str
    filename: str
    created_at: datetime
    analysis: ReplayAnalysis


class InMemoryReplayStore:
    """Process-local replay storage used until durable persistence is selected."""

    def __init__(self) -> None:
        self._records: dict[str, ReplayRecord] = {}

    def add(self, filename: str, analysis: ReplayAnalysis) -> ReplayRecord:
        record = ReplayRecord(
            replay_id=str(uuid4()),
            filename=filename,
            created_at=datetime.now(UTC),
            analysis=analysis,
        )
        self._records[record.replay_id] = record
        return record

    def get(self, replay_id: str) -> ReplayRecord | None:
        return self._records.get(replay_id)

    def list(self) -> tuple[ReplayRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.created_at, reverse=True))
