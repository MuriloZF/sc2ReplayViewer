# Project Overview:
The goal is to create a tool to Analyze Starcraft 2 replays, this project will be used to gather data for a
ML project.

The final goal is have a website that will display the replay informations (e.g: the minimap with and the data such as
minerals, supply, etc) alognside of a win % of both players, pretty much like it's normal on online chess platforms.


# Purpose:
Your goal is purely the replay analyzis, so you won't need to implement anything related to the ML part.


# Tech Stack:
- Backend: Python 3.12, FastAPI + Uvicorn, Pydantic
- Replay parsing: s2protocol
- Storage: SQLAlchemy + SQLite (swappable to Postgres later)
- ML data handoff: Parquet (PyArrow/Pandas) + JSON dataset export
- Frontend: React 18 + TypeScript + Vite, Recharts, Canvas minimap
- Quality: pytest, ruff + mypy, ESLint, vitest

# Architecture:
backend/
│
├── app/replay/
│   ├── decoder/
│   │   └── s2protocol_adapter.py
│   │
│   ├── events/
│   │   ├── units.py
│   │   ├── economy.py
│   │   └── player.py
│   │
│   └── state/
│       ├── game_state.py
│       └── reconstructor.py
│
├── app/analysis/
│   ├── timeline.py
│   ├── build_order.py
│   └── features.py
│
├── app/ml/
│   └── inference.py
│
├── app/storage/
│
└── app/api/

# Coding Rules:
- Clean code
- Use comments to explain your code, but avoid unnecessary comments
- Documentate the APIs
- Don't do any big commit, break then in small parts, so it will easier to me to maintain

# Current Task:
- [x] Undertand the project
- [x] Decide Tech Stack
- [x] Decide Architecture
- [X] Scaffold backend + frontend
- [X] Implement parser + feature extractor
- [X] Validate parser against a real replay
- [X] Implement FastAPI endpoints
- [X] Implement React frontend (upload, list, minimap, charts)
- [ ] Add tests + API docs
- [ ] Fix build orders
- [ ] Adjust UI
- [ ] Implement SQLite persistence + Parquet export
