import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from backend.app.analysis.ml_features import (
    UnsupportedTrainingReplay,
    extract_ml_state_rows,
)
from backend.app.analysis.name_normalization import (
    NAME_NORMALIZATION_VERSION,
    unit_name_mapping,
)
from backend.app.analysis.timeline import extract_timeline
from backend.app.replay.decoder import DecodedReplay, ReplayDecodeError, S2ProtocolAdapter

DATASET_SCHEMA_VERSION = "3"
DEFAULT_SAMPLE_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class DatasetExportResult:
    dataset_path: Path
    manifest_path: Path
    matches: int
    rows: int
    skipped: int


class ReplayDecoder(Protocol):
    def decode(self, replay_path: str | Path) -> DecodedReplay: ...


def export_tournament_dataset(
    replay_dir: Path,
    output_dir: Path,
    *,
    tournament: str | None = None,
    sample_seconds: float = DEFAULT_SAMPLE_SECONDS,
    overwrite: bool = False,
    progress: Callable[[int, int, Path], None] | None = None,
    decoder: ReplayDecoder | None = None,
) -> DatasetExportResult:
    """Export completed 1v1 replays as a compressed, training-ready Parquet table."""

    if sample_seconds <= 0:
        raise ValueError("sample_seconds must be greater than zero")
    if not replay_dir.is_dir():
        raise ValueError(f"replay directory does not exist: {replay_dir}")
    replay_paths = sorted(replay_dir.glob("*.SC2Replay"))
    if not replay_paths:
        raise ValueError(f"no .SC2Replay files found in {replay_dir}")

    dataset_path = output_dir / "states.parquet"
    manifest_path = output_dir / "manifest.json"
    if not overwrite and (dataset_path.exists() or manifest_path.exists()):
        raise FileExistsError(f"dataset already exists in {output_dir}; use --overwrite")

    import pyarrow as pa  # type: ignore[import-untyped]
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    output_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".states-", suffix=".parquet", dir=output_dir
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    schema = _dataset_schema(pa)
    writer = pq.ParquetWriter(
        temporary_path,
        schema,
        compression="zstd",
        use_dictionary=True,
    )
    replay_decoder = decoder or S2ProtocolAdapter()
    exported: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    row_count = 0
    unit_names_by_build: dict[int, set[str]] = {}
    tournament_name = tournament or replay_dir.name

    try:
        for index, replay_path in enumerate(replay_paths, start=1):
            if progress is not None:
                progress(index, len(replay_paths), replay_path)
            try:
                match_id = _sha256(replay_path)
                replay = replay_decoder.decode(replay_path)
                unit_names_by_build.setdefault(replay.metadata.base_build, set()).update(
                    event.unit_type for event in replay.unit_events if event.unit_type
                )
                timeline = extract_timeline(replay, sample_seconds=sample_seconds)
                rows = extract_ml_state_rows(
                    replay,
                    timeline,
                    match_id=match_id,
                    tournament=tournament_name,
                )
            except (OSError, ReplayDecodeError, UnsupportedTrainingReplay, ValueError) as exc:
                skipped.append({"filename": replay_path.name, "reason": str(exc)})
                continue

            writer.write_table(pa.Table.from_pylist(list(rows), schema=schema))
            row_count += len(rows)
            exported.append(
                {
                    "filename": replay_path.name,
                    "match_id": match_id,
                    "rows": len(rows),
                }
            )
    except Exception:
        writer.close()
        temporary_path.unlink(missing_ok=True)
        raise
    else:
        writer.close()
        os.replace(temporary_path, dataset_path)

    manifest = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "tournament": tournament_name,
        "sample_seconds": sample_seconds,
        "name_normalization_version": NAME_NORMALIZATION_VERSION,
        "dataset": dataset_path.name,
        "matches": len(exported),
        "rows": row_count,
        "skipped": len(skipped),
        "exported_replays": exported,
        "skipped_replays": skipped,
        "unit_name_mappings": {
            str(build): {
                raw_name: unit_name_mapping(raw_name, base_build=build)
                for raw_name in sorted(raw_names)
            }
            for build, raw_names in sorted(unit_names_by_build.items())
        },
    }
    _write_manifest(manifest_path, manifest)
    return DatasetExportResult(dataset_path, manifest_path, len(exported), row_count, len(skipped))


def _dataset_schema(pa: Any) -> Any:
    unit_counts = pa.map_(pa.string(), pa.int32())
    fields = [
        pa.field("match_id", pa.string(), nullable=False),
        pa.field("tournament", pa.string(), nullable=False),
        pa.field("map_name", pa.string(), nullable=False),
        pa.field("map_id", pa.string(), nullable=False),
        pa.field("base_build", pa.int32(), nullable=False),
        pa.field("game_loop", pa.int64(), nullable=False),
        pa.field("game_time_seconds", pa.float64(), nullable=False),
        pa.field("p1_race", pa.string(), nullable=False),
        pa.field("p2_race", pa.string(), nullable=False),
        pa.field("p1_won", pa.bool_(), nullable=False),
        pa.field("sample_weight", pa.float64(), nullable=False),
    ]
    for prefix in ("p1", "p2"):
        fields.extend(
            [
                pa.field(f"{prefix}_minerals", pa.int32(), nullable=False),
                pa.field(f"{prefix}_vespene", pa.int32(), nullable=False),
                pa.field(f"{prefix}_supply_used", pa.float64(), nullable=False),
                pa.field(f"{prefix}_supply_cap", pa.float64(), nullable=False),
                pa.field(f"{prefix}_supply_capacity", pa.float64(), nullable=False),
                pa.field(f"{prefix}_army_supply", pa.float64(), nullable=False),
                pa.field(f"{prefix}_workers", pa.int32(), nullable=False),
                pa.field(f"{prefix}_unit_counts", unit_counts, nullable=False),
                pa.field(f"{prefix}_in_progress_counts", unit_counts, nullable=False),
                pa.field(f"{prefix}_unit_modes", unit_counts, nullable=False),
                pa.field(f"{prefix}_upgrades", pa.list_(pa.string()), nullable=False),
            ]
        )
    metadata = {b"schema_version": DATASET_SCHEMA_VERSION.encode()}
    return pa.schema(fields, metadata=metadata)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as replay:
        while chunk := replay.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(path: Path, contents: dict[str, object]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".manifest-", suffix=".json", dir=path.parent, text=True
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(contents, output, indent=2, ensure_ascii=False)
            output.write("\n")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
