import json
from pathlib import Path

import pytest

from backend.app.ml.inference import BASE_FEATURES, ECONOMY_FEATURES


@pytest.fixture
def win_model_dir(tmp_path: Path) -> Path:
    """A real, small model keeps tests independent of ignored local model artifacts."""

    xgb = pytest.importorskip("xgboost")
    np = pytest.importorskip("numpy")
    differences = [
        {"left": f"p1_{name}", "right": f"p2_{name}", "name": f"{name}_difference"}
        for name in ECONOMY_FEATURES
    ]
    names = [*BASE_FEATURES, *(feature["name"] for feature in differences)]
    metadata = {
        "target": "p1_won",
        "objective": "binary:logistic",
        "positive_class": 1,
        "base_features": list(BASE_FEATURES),
        "difference_features": differences,
        "feature_names": names,
    }
    values = np.random.default_rng(42).uniform(0, 200, size=(40, len(names)))
    data = xgb.DMatrix(values, label=(values[:, 6] > values[:, 12]), feature_names=names)
    model = xgb.train(
        {"objective": "binary:logistic", "max_depth": 2, "nthread": 1},
        data,
        num_boost_round=3,
    )
    model.save_model(tmp_path / "sc2_win_probability_model.json")
    (tmp_path / "model_metadata.json").write_text(json.dumps(metadata))
    return tmp_path
