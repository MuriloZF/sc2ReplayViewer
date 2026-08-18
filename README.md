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

The replay API exposes:

- `POST /api/v1/replays` — upload and analyze a replay
- `GET /api/v1/replays` — list analyses in the current process
- `GET /api/v1/replays/{replay_id}/summary` — metadata, players, and event counts
- `GET /api/v1/replays/{replay_id}/timeline` — sampled economy and unit state
- `GET /api/v1/replays/{replay_id}/build-order` — chronological production events

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

The frontend supports replay upload, process-local replay history, animated timeline playback, reconstructed unit positions on a canvas minimap, player resource cards, army/worker charts, and time-aware build-order columns. Start the backend before Vite so `/api` requests can be proxied correctly.

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

## Layout

- `backend/app/api/` — FastAPI routes
- `backend/app/replay/` — protocol decoding, normalized events, and state reconstruction
- `backend/app/analysis/` — timeline, build-order, and feature extraction
- `backend/app/storage/` — database and dataset export
- `backend/app/ml/` — integration boundary for future inference
- `frontend/src/` — React application
