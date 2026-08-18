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

## Layout

- `backend/app/api/` — FastAPI routes
- `backend/app/replay/` — protocol decoding, normalized events, and state reconstruction
- `backend/app/analysis/` — timeline, build-order, and feature extraction
- `backend/app/storage/` — database and dataset export
- `backend/app/ml/` — integration boundary for future inference
- `frontend/src/` — React application
