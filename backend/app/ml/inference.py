from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from backend.app.analysis import ReplayAnalysis
from backend.app.replay.state import FrameSnapshot

if TYPE_CHECKING:
    from xgboost import Booster

ECONOMY_FEATURES = ("minerals", "vespene", "supply_used", "supply_cap", "army_supply", "workers")
BASE_FEATURES = (
    "game_time_seconds",
    *(f"{prefix}_{feature}" for prefix in ("p1", "p2") for feature in ECONOMY_FEATURES),
)


class ModelUnavailable(RuntimeError):
    """The inference dependencies or model artifacts could not be loaded."""


class UnsupportedPrediction(ValueError):
    """The replay cannot provide initialized economy data for two players."""


class DifferenceFeature(BaseModel):
    left: str
    right: str
    name: str


class ModelMetadata(BaseModel):
    target: Literal["p1_won"]
    objective: Literal["binary:logistic"]
    positive_class: Literal[1]
    base_features: list[str]
    difference_features: list[DifferenceFeature]
    feature_names: list[str]

    def validate_features(self) -> None:
        if set(self.base_features) != set(BASE_FEATURES):
            raise ValueError("Unsupported model base features")
        names = [*self.base_features, *(feature.name for feature in self.difference_features)]
        if len(set(names)) != len(names) or self.feature_names != names:
            raise ValueError("Model feature order does not match its feature recipe")
        if any(
            feature.left not in BASE_FEATURES or feature.right not in BASE_FEATURES
            for feature in self.difference_features
        ):
            raise ValueError("Difference features must use supported base features")


@dataclass(frozen=True, slots=True)
class PlayerProbability:
    player_id: int
    win_probability: float


@dataclass(frozen=True, slots=True)
class ProbabilitySample:
    game_loop: int
    game_time_seconds: float
    players: tuple[PlayerProbability, ...]


def economy_features(frame: FrameSnapshot, player_ids: tuple[int, int]) -> dict[str, float] | None:
    """Match the training export's player order and 200-supply capacity limit."""

    players = {player.player_id: player for player in frame.players}
    if any(player_id not in players for player_id in player_ids):
        return None
    features = {"game_time_seconds": frame.game_time_seconds}
    for prefix, player_id in zip(("p1", "p2"), player_ids, strict=True):
        player = players[player_id]
        for name in ECONOMY_FEATURES:
            value = getattr(player, name)
            features[f"{prefix}_{name}"] = float(min(value, 200) if name == "supply_cap" else value)
    return features


class WinProbabilityPredictor:
    """Load a trusted local XGBoost model once and predict a replay in one batch."""

    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir
        self._bundle: tuple[Booster, ModelMetadata] | None = None
        self._load_lock = Lock()

    def _load(self) -> tuple[Booster, ModelMetadata]:
        with self._load_lock:
            if self._bundle is None:
                try:
                    from xgboost import Booster
                    from xgboost.core import XGBoostError
                except (ImportError, OSError) as exc:
                    raise ModelUnavailable("Install the backend inference dependencies.") from exc
                try:
                    metadata = ModelMetadata.model_validate_json(
                        (self.model_dir / "model_metadata.json").read_text()
                    )
                    metadata.validate_features()
                    model = Booster(params={"device": "cpu", "nthread": 1})
                    model.load_model(self.model_dir / "sc2_win_probability_model.json")
                    config = json.loads(model.save_config())
                    if config["learner"]["objective"]["name"] != metadata.objective:
                        raise ValueError("Model objective does not match metadata")
                    if model.feature_names != metadata.feature_names:
                        raise ValueError("Model feature names do not match metadata")
                except (OSError, ValueError, XGBoostError) as exc:
                    raise ModelUnavailable(
                        "Unable to load the win probability model and metadata."
                    ) from exc
                self._bundle = model, metadata
            return self._bundle

    def predict(self, analysis: ReplayAnalysis) -> tuple[ProbabilitySample, ...]:
        players = sorted(analysis.replay.metadata.players, key=lambda player: player.player_id)
        if len(players) != 2 or players[0].player_id == players[1].player_id:
            raise UnsupportedPrediction("Win probability is supported for 1v1 replays only.")
        player_ids = (players[0].player_id, players[1].player_id)
        frames: list[FrameSnapshot] = []
        rows: list[dict[str, float]] = []
        initialized = False
        for frame in analysis.timeline:
            features = economy_features(frame, player_ids)
            if features is None:
                continue
            # Only trim the opening; losing all supply providers later is a valid state.
            initialized = initialized or (
                features["p1_supply_cap"] > 0 and features["p2_supply_cap"] > 0
            )
            if not initialized:
                continue
            frames.append(frame)
            rows.append(features)
        if not rows:
            raise UnsupportedPrediction(
                "Replay has no initialized economy samples for both players."
            )

        model, metadata = self._load()
        import numpy as np
        from xgboost import DMatrix
        from xgboost.core import XGBoostError

        for row in rows:
            for feature in metadata.difference_features:
                row[feature.name] = row[feature.left] - row[feature.right]
        values = np.array(
            [[row[name] for name in metadata.feature_names] for row in rows], dtype=np.float32
        )
        try:
            probabilities = model.predict(
                DMatrix(values, feature_names=metadata.feature_names, nthread=1)
            )
        except XGBoostError as exc:
            raise ModelUnavailable("Unable to run the win probability model.") from exc
        if probabilities.shape != (len(frames),) or not np.all(
            np.isfinite(probabilities) & (probabilities >= 0) & (probabilities <= 1)
        ):
            raise ModelUnavailable("Model returned invalid win probabilities.")
        return tuple(
            ProbabilitySample(
                game_loop=frame.game_loop,
                game_time_seconds=frame.game_time_seconds,
                players=(
                    PlayerProbability(player_ids[0], float(probability)),
                    PlayerProbability(player_ids[1], 1.0 - float(probability)),
                ),
            )
            for frame, probability in zip(frames, probabilities, strict=True)
        )
