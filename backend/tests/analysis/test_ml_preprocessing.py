from pathlib import Path

import pandas as pd

from backend.app.analysis.ml_preprocessing import grouped_match_split, load_training_data


def test_expands_nested_features_and_splits_by_match(tmp_path: Path) -> None:
    path = tmp_path / "states.parquet"
    rows = []
    for match_id, won in (("a", True), ("b", False), ("c", True), ("d", False)):
        for game_time in (5.0, 10.0):
            rows.append(_row(match_id, won, game_time))
    pd.DataFrame(rows).to_parquet(path)

    prepared = load_training_data(path)
    split = grouped_match_split(
        prepared.groups,
        validation_fraction=0.25,
        test_fraction=0.25,
        random_seed=7,
    )

    assert "p1_unit_count_Marine" in prepared.features
    assert "p1_mode_SiegeTank:sieged" in prepared.features
    assert "p1_upgrade_Stimpack" in prepared.features
    assert "map_id_map-hash" in prepared.features
    assert prepared.features.select_dtypes(exclude="number").empty
    subsets = [
        set(prepared.groups.loc[list(indices)])
        for indices in (split.train, split.validation, split.test)
    ]
    assert all(
        left.isdisjoint(right)
        for index, left in enumerate(subsets)
        for right in subsets[index + 1 :]
    )


def _row(match_id: str, won: bool, game_time: float) -> dict[str, object]:
    row: dict[str, object] = {
        "match_id": match_id,
        "map_name": "Test Map",
        "map_id": "map-hash",
        "base_build": 97_563,
        "game_loop": int(game_time * 22.4),
        "game_time_seconds": game_time,
        "p1_race": "Terran",
        "p2_race": "Zerg",
        "p1_won": won,
        "sample_weight": 0.5,
    }
    for prefix, unit in (("p1", "Marine"), ("p2", "Zergling")):
        row.update(
            {
                f"{prefix}_minerals": 50,
                f"{prefix}_vespene": 0,
                f"{prefix}_supply_used": 12.0,
                f"{prefix}_supply_cap": 15.0,
                f"{prefix}_army_supply": 1.0,
                f"{prefix}_workers": 11,
                f"{prefix}_unit_counts": {unit: 1},
                f"{prefix}_in_progress_counts": {f"{unit}InProgress": 1},
                f"{prefix}_unit_modes": {"SiegeTank:sieged": 1},
                f"{prefix}_upgrades": ["Stimpack"] if prefix == "p1" else [],
            }
        )
    return row
