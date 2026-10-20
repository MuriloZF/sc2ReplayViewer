# SC2 Replay Viewer

SC2 Replay Viewer is a web application for extracting and exploring data from StarCraft II replay files. The project focuses on replay analysis; win-probability inference remains an external ML concern.

## Requirements

- Python 3.12+
- Node.js 20+

## Backend

Create a virtual environment and install the API with its development tools:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,export]'
uvicorn backend.app.main:app --reload
```

The API is available at `http://localhost:8000`, with interactive documentation at `/docs` and the health check at `/api/v1/health`.

Replay analyses are currently retained in process memory and are cleared whenever the API restarts. Upload a replay with:

```bash
curl -F replay=@path/to/game.SC2Replay http://localhost:8000/api/v1/replays
```

Map minimaps are resolved from Blizzard's content-addressed depot and cached as PNG files in
`.cache/maps`. Set `SC2_MAP_CACHE_DIR` to use a different cache directory.

The replay API exposes:

- `POST /api/v1/replays` — upload and analyze a replay
- `GET /api/v1/replays` — list analyses in the current process
- `GET /api/v1/replays/{replay_id}/summary` — metadata, players, and event counts
- `GET /api/v1/replays/{replay_id}/timeline` — sampled economy and unit state
- `GET /api/v1/replays/{replay_id}/build-order` — chronological production events
- `GET /api/v1/replays/{replay_id}/minimap` — exact replay map minimap as a cached PNG
- `GET /api/v1/replays/{replay_id}/map-metadata` — map dimensions and playable bounds

The upload endpoint accepts a `sample_seconds` query parameter greater than 0 and at most 60, and limits replay files to 100 MB. Endpoint schemas and error responses are documented in the interactive OpenAPI UI.

Run backend checks from the repository root:

```bash
pytest
ruff check .
mypy
```

## Frontend

Install dependencies and start Vite:

```bash
cd frontend
npm install
npm run dev
```

The development server is available at `http://localhost:5173` and proxies `/api` requests to the backend. Run `npm test`, `npm run lint`, and `npm run build` to verify frontend changes.

The frontend supports replay upload, process-local replay history, animated timeline playback, the exact replay map as a canvas minimap background, reconstructed unit positions, player resource cards, army/worker charts, and replay-derived build-order columns. Build orders include game time, nearest known supply, workers, meaningful units and structures, and researched upgrades while filtering temporary or internal entities. Start the backend before Vite so `/api` requests can be proxied correctly.

## Replay analysis

`S2ProtocolAdapter` decodes replay metadata, tracker events, and game events into normalized models. The analysis layer reconstructs sampled player state and exposes timeline, build-order, and flat feature-row extractors. The adapter uses Python's modern module loader for protocol definitions because current `s2protocol` releases still rely on the `imp` module removed in Python 3.12.

```python
from backend.app.analysis import extract_build_order, extract_feature_rows, extract_timeline
from backend.app.replay.decoder import S2ProtocolAdapter

replay = S2ProtocolAdapter().decode("example.SC2Replay")
timeline = extract_timeline(replay, sample_seconds=5)
build_order = extract_build_order(replay)
feature_rows = extract_feature_rows(replay, timeline)
```

Inspect a replay from the command line after installing the project:

```bash
sc2-replay-inspect path/to/game.SC2Replay
```

Add `--include-data` to emit the full timeline, build order, and feature rows. Use `--output report.json` to write the result to a file instead of standard output. The command exits with a concise error for missing, corrupt, or unsupported replay files.

## ML dataset export

Training data is exported separately from the detailed JSON used to inspect individual replays. The exporter samples each completed 1v1 match every five seconds and writes both players into one compact, labeled row. It excludes raw game events, unit positions, minimap data, and build-order display data.

Install the export dependencies and export a replay directory:

```bash
pip install -e '.[export]'
sc2-replay-export Replays/batch Reports/ML/batch
```

The output directory contains:

- `states.parquet` — Zstandard-compressed match states, canonical sparse unit counts, unit modes, upgrades, and the `p1_won` training target
- `manifest.json` — schema versions, raw-to-canonical unit mappings by game build, row counts, replay hashes, and reasons for skipped replays

Existing output is protected by default. Pass `--overwrite` to regenerate a dataset. Replays that are corrupt, unsupported, incomplete, tied, or not 1v1 are recorded in the manifest and do not stop the rest of the batch. `replayScript.py` provides the same export flow with an interactive replay-folder prompt.

Load numeric model features and create leakage-safe splits with:

```python
from backend.app.analysis.ml_preprocessing import grouped_match_split, load_training_data

data = load_training_data("Reports/ML/batch/states.parquet")
split = grouped_match_split(data.groups)

X_train = data.features.loc[list(split.train)]
y_train = data.target.loc[list(split.train)]
weights = data.sample_weight.loc[list(split.train)]
```

The loader expands sparse unit-count maps and upgrade lists, encodes map/race categories, and separates labels, weights, and match groups from model inputs. Always split by `match_id`; randomly splitting timestamp rows would leak states from the same replay across training and evaluation sets.

Dataset schema version 5 stores `supply_used`, `supply_cap`, and `army_supply` as Int32. The parser discards fractional supply points using integer division of the raw tracker values by 4096 (for example, 61.5 becomes 61). No batch label is stored in the dataset or manifest. The `p1_supply_capacity` and `p2_supply_capacity` columns remain omitted. During dataset export, `supply_cap` is capped at 200, while `supply_used` is not clamped because legitimate over-cap states can occur. The parser and timeline API retain the tracker's supply capacity, which can exceed 200; this export limit does not apply there. Existing schema version 4 files retain Double supply fields; regenerate exports with `--overwrite` to use the new schema.

Unit transformations are represented without double-counting identity. For example, a sieged tank contributes to `SiegeTank` in `unit_counts` and `SiegeTank:sieged` in `unit_modes`. For successfully decoded replays, unit names without a known alias are kept exactly as written and recorded in `manifest.json` under `unit_name_mappings`, grouped by game build. The parser does not guess whether an unfamiliar name refers to an existing unit. A developer can inspect those mappings and explicitly add an alias when appropriate. This fallback does not make unsupported replay builds decodable.

## Layout

- `backend/app/api/` — FastAPI routes
- `backend/app/replay/` — protocol decoding, normalized events, and state reconstruction
- `backend/app/analysis/` — timeline, build-order, and feature extraction
- `backend/app/storage/` — database and dataset export
- `backend/app/ml/` — integration boundary for future inference
- `frontend/src/` — React application
