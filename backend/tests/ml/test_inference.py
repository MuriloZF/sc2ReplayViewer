import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from backend.app.analysis import ReplayAnalysis
from backend.app.ml.inference import (
    ModelUnavailable,
    UnsupportedPrediction,
    WinProbabilityPredictor,
    economy_features,
)
from backend.app.replay.decoder.models import DecodedReplay, ReplayMetadata
from backend.app.replay.events import PlayerInfo, PlayerResult
from backend.app.replay.state import FrameSnapshot, PlayerSnapshot


def analysis() -> ReplayAnalysis:
    # Deliberately unsorted metadata and frame players; IDs define model p1/p2.
    players = (
        PlayerInfo(7, "Beta", "Zerg", PlayerResult.UNKNOWN),
        PlayerInfo(3, "Alpha", "Terran", PlayerResult.UNKNOWN),
    )
    replay = DecodedReplay(ReplayMetadata(97_563, 224, "Test Map", players), (), (), ())
    p1 = PlayerSnapshot(3, 100, 25, 205, 240, 150, 55, ())
    p2 = PlayerSnapshot(7, 50, 0, 190, 216, 130, 60, ())
    return ReplayAnalysis(
        replay,
        (
            FrameSnapshot(0, 0, (replace(p1, supply_cap=0), replace(p2, supply_cap=0))),
            FrameSnapshot(112, 5, (p2, p1)),
            FrameSnapshot(224, 10, (p1, p2)),
            FrameSnapshot(336, 15, (p1,)),
        ),
        (),
        (),
    )


def test_predictions_match_expected_training_features_and_ignore_results(
    win_model_dir: Path,
) -> None:
    import numpy as np
    from xgboost import Booster, DMatrix

    predictor = WinProbabilityPredictor(win_model_dir)
    replay = analysis()
    predictions = predictor.predict(replay)
    assert [sample.game_loop for sample in predictions] == [112, 224]
    assert [item.player_id for item in predictions[0].players] == [3, 7]
    model = Booster(model_file=win_model_dir / "sc2_win_probability_model.json")
    expected = model.predict(
        DMatrix(
            np.array(
                [[5, 100, 25, 205, 200, 150, 55, 50, 0, 190, 200, 130, 60, 50, 25, 15, 0, 20, -5]],
                dtype=np.float32,
            ),
            feature_names=model.feature_names,
        )
    )[0]
    assert predictions[0].players[0].win_probability == pytest.approx(float(expected))
    assert sum(player.win_probability for player in predictions[0].players) == 1.0

    labeled_replay = replace(
        replay,
        replay=replace(
            replay.replay,
            metadata=replace(
                replay.replay.metadata,
                players=tuple(
                    replace(player, result=PlayerResult.WIN if index else PlayerResult.LOSS)
                    for index, player in enumerate(replay.replay.metadata.players)
                ),
            ),
        ),
    )
    assert predictor.predict(labeled_replay) == predictions
    # Once loaded, the model stays in memory instead of reading its files per request.
    (win_model_dir / "sc2_win_probability_model.json").unlink()
    assert predictor.predict(replay) == predictions


def test_supply_preprocessing_matches_export() -> None:
    from backend.app.analysis.ml_features import extract_ml_state_rows

    replay = analysis()
    metadata = replace(
        replay.replay.metadata,
        players=(
            PlayerInfo(3, "Alpha", "Terran", PlayerResult.WIN),
            PlayerInfo(7, "Beta", "Zerg", PlayerResult.LOSS),
        ),
    )
    frame = replay.timeline[1]
    row = extract_ml_state_rows(replace(replay.replay, metadata=metadata), (frame,), match_id="m")[
        0
    ]
    features = economy_features(frame, (3, 7))
    assert features is not None
    assert all(row[name] == value for name, value in features.items())


def test_keeps_late_zero_supply_states_after_initialization(win_model_dir: Path) -> None:
    replay = analysis()
    frame = replay.timeline[2]
    destroyed = replace(frame, players=tuple(replace(p, supply_cap=0) for p in frame.players))
    predictions = WinProbabilityPredictor(win_model_dir).predict(
        replace(replay, timeline=(*replay.timeline[:2], destroyed))
    )
    assert [sample.game_loop for sample in predictions] == [112, 224]


def test_rejects_unsupported_replays_without_loading_model(tmp_path: Path) -> None:
    predictor = WinProbabilityPredictor(tmp_path)
    replay = analysis()
    with pytest.raises(UnsupportedPrediction, match="initialized"):
        predictor.predict(replace(replay, timeline=replay.timeline[:1]))
    with pytest.raises(UnsupportedPrediction, match="1v1"):
        predictor.predict(
            replace(
                replay,
                replay=replace(
                    replay.replay,
                    metadata=replace(replay.replay.metadata, players=()),
                ),
            )
        )


def test_reports_missing_model(tmp_path: Path) -> None:
    with pytest.raises(ModelUnavailable):
        WinProbabilityPredictor(tmp_path).predict(analysis())


def test_reports_missing_dependency(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "xgboost", None)
    with pytest.raises(ModelUnavailable, match="dependencies"):
        WinProbabilityPredictor(tmp_path).predict(analysis())


@pytest.mark.parametrize("mismatch", ["order", "objective", "unknown_feature", "corrupt_model"])
def test_rejects_incompatible_artifacts(win_model_dir: Path, mismatch: str) -> None:
    path = win_model_dir / "model_metadata.json"
    metadata = json.loads(path.read_text())
    if mismatch == "order":
        metadata["base_features"] = list(reversed(metadata["base_features"]))
        metadata["feature_names"][:13] = metadata["base_features"]
    elif mismatch == "objective":
        metadata["objective"] = "reg:squarederror"
    elif mismatch == "unknown_feature":
        metadata["difference_features"][0]["left"] = "p1_won"
    else:
        (win_model_dir / "sc2_win_probability_model.json").write_text("broken")
    path.write_text(json.dumps(metadata))
    with pytest.raises(ModelUnavailable):
        WinProbabilityPredictor(win_model_dir).predict(analysis())
