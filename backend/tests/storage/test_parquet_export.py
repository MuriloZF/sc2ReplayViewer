import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from backend.app.replay.decoder import DecodedReplay, ReplayMetadata
from backend.app.replay.decoder.normalizer import normalize_tracker_events
from backend.app.replay.events import (
    PlayerInfo,
    PlayerResult,
    UnitEvent,
    UnitEventKind,
)
from backend.app.storage.parquet_export import export_replay_dataset


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

    result = export_replay_dataset(
        replay_dir,
        output_dir,
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
    assert table.schema.metadata == {b"schema_version": b"5"}
    assert "p1_unit_count" not in table.column_names
    assert "tournament" not in table.column_names
    for prefix in ("p1", "p2"):
        assert f"{prefix}_supply_capacity" not in table.column_names
        assert table.column(f"{prefix}_supply_used").to_pylist() == [12] * 3
        assert table.column(f"{prefix}_supply_cap").to_pylist() == [15] * 3
        assert table.column(f"{prefix}_army_supply").to_pylist() == [0] * 3
        for field in ("supply_used", "supply_cap", "army_supply"):
            assert table.schema.field(f"{prefix}_{field}").type == pa.int32()
    assert "p1_unit_modes" in table.column_names
    assert manifest["name_normalization_version"] == "1"
    assert manifest["unit_name_mappings"]["97563"]["SCV"] == {
        "name": "SCV",
        "mode": None,
    }
    assert "tournament" not in manifest
    assert manifest["schema_version"] == "5"
    assert manifest["matches"] == 1
    assert manifest["skipped_replays"][0]["filename"] == "invalid.SC2Replay"


def _replay(results: tuple[PlayerResult, PlayerResult]) -> DecodedReplay:
    players = (
        PlayerInfo(1, "Alpha", "Terran", results[0]),
        PlayerInfo(2, "Beta", "Zerg", results[1]),
    )
    _, economy_events, _ = normalize_tracker_events(
        {
            "_event": "NNet.Replay.Tracker.SPlayerStatsEvent",
            "_gameloop": loop,
            "m_playerId": player_id,
            "m_stats": {
                "m_scoreValueMineralsCurrent": 50,
                "m_scoreValueFoodUsed": 51_200,
                "m_scoreValueFoodMade": 63_488,
                "m_scoreValueFoodUsedArmy": 2048,
                "m_scoreValueWorkersActiveCount": 12,
            },
        }
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
