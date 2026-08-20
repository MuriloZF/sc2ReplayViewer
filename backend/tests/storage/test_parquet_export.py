import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from backend.app.replay.decoder import DecodedReplay, ReplayMetadata
from backend.app.replay.events import (
    PlayerEconomyEvent,
    PlayerInfo,
    PlayerResult,
    UnitEvent,
    UnitEventKind,
)
from backend.app.storage.parquet_export import export_tournament_dataset


class StubDecoder:
    def decode(self, replay_path: str | Path) -> DecodedReplay:
        path = Path(replay_path)
        results = (
            (PlayerResult.UNKNOWN, PlayerResult.UNKNOWN)
            if path.stem == "invalid"
            else (PlayerResult.WIN, PlayerResult.LOSS)
        )
        return _replay(results)


def test_exports_compressed_parquet_and_skip_manifest(tmp_path: Path) -> None:
    replay_dir = tmp_path / "replays"
    replay_dir.mkdir()
    valid = replay_dir / "valid.SC2Replay"
    valid.write_bytes(b"valid replay")
    (replay_dir / "invalid.SC2Replay").write_bytes(b"invalid replay")
    output_dir = tmp_path / "dataset"

    result = export_tournament_dataset(
        replay_dir,
        output_dir,
        tournament="Test Cup",
        decoder=StubDecoder(),
    )

    table = pq.read_table(result.dataset_path)
    manifest = json.loads(result.manifest_path.read_text())
    assert result.matches == 1
    assert result.skipped == 1
    assert table.num_rows == 3
    assert table.column("match_id")[0].as_py() == hashlib.sha256(b"valid replay").hexdigest()
    assert table.column("p1_won")[0].as_py() is True
    assert table.column("p1_unit_counts")[1].as_py() == [("SCV", 1)]
    assert table.schema.metadata == {b"schema_version": b"2"}
    assert "p1_unit_count" not in table.column_names
    assert manifest["tournament"] == "Test Cup"
    assert manifest["matches"] == 1
    assert manifest["skipped_replays"][0]["filename"] == "invalid.SC2Replay"


def _replay(results: tuple[PlayerResult, PlayerResult]) -> DecodedReplay:
    players = (
        PlayerInfo(1, "Alpha", "Terran", results[0]),
        PlayerInfo(2, "Beta", "Zerg", results[1]),
    )
    economy_events = tuple(
        PlayerEconomyEvent(loop, player_id, 50, 0, 12, 15, 0, 12)
        for loop in (0, 112, 224)
        for player_id in (1, 2)
    )
    unit_events = (
        UnitEvent(0, UnitEventKind.BORN, 1, "SCV", 1),
        UnitEvent(0, UnitEventKind.BORN, 2, "Drone", 2),
    )
    return DecodedReplay(
        ReplayMetadata(97_563, 224, "Test Map", players),
        unit_events,
        economy_events,
        (),
    )
