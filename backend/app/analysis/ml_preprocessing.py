import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class PreparedTrainingData:
    features: Any
    target: Any
    sample_weight: Any
    groups: Any


@dataclass(frozen=True, slots=True)
class GroupedSplit:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]


def load_training_data(path: str | Path) -> PreparedTrainingData:
    """Load Parquet states and expand sparse maps/lists into numeric model features."""

    import pandas as pd  # type: ignore[import-untyped]

    frame = pd.read_parquet(path)
    target = frame["p1_won"].astype("int8")
    sample_weight = frame["sample_weight"]
    groups = frame["match_id"]
    base = frame.drop(
        columns=[
            "match_id",
            "map_name",
            "p1_won",
            "sample_weight",
            "game_loop",
        ]
    )

    nested_columns = [
        "p1_unit_counts",
        "p1_in_progress_counts",
        "p1_unit_modes",
        "p1_upgrades",
        "p2_unit_counts",
        "p2_in_progress_counts",
        "p2_unit_modes",
        "p2_upgrades",
    ]
    expanded = [_expand_nested_column(frame[column], column, pd) for column in nested_columns]
    base = base.drop(columns=nested_columns)
    base = pd.get_dummies(
        base,
        columns=["map_id", "p1_race", "p2_race"],
        dtype="int8",
    )
    features = pd.concat([base, *expanded], axis=1).fillna(0)
    return PreparedTrainingData(features, target, sample_weight, groups)


def grouped_match_split(
    groups: Any,
    *,
    validation_fraction: float = 0.2,
    test_fraction: float = 0.1,
    random_seed: int = 42,
) -> GroupedSplit:
    """Return row indices split by match so one replay never crosses data subsets."""

    if not 0 <= validation_fraction < 1 or not 0 <= test_fraction < 1:
        raise ValueError("split fractions must be between zero and one")
    if validation_fraction + test_fraction >= 1:
        raise ValueError("validation and test fractions must sum to less than one")

    matches = list(dict.fromkeys(str(value) for value in groups))
    if not matches:
        raise ValueError("cannot split an empty dataset")
    random.Random(random_seed).shuffle(matches)
    validation_count = _split_count(len(matches), validation_fraction)
    test_count = _split_count(len(matches), test_fraction)
    validation_matches = set(matches[:validation_count])
    test_matches = set(matches[validation_count : validation_count + test_count])

    train: list[int] = []
    validation: list[int] = []
    test: list[int] = []
    for index, match_id in zip(groups.index, groups, strict=True):
        destination = (
            validation
            if str(match_id) in validation_matches
            else test
            if str(match_id) in test_matches
            else train
        )
        destination.append(int(index))
    return GroupedSplit(tuple(train), tuple(validation), tuple(test))


def _expand_nested_column(series: Any, column: str, pd: Any) -> Any:
    if column.endswith("upgrades"):
        records = [{str(value): 1 for value in values} for values in series]
        prefix = f"{column[:-1]}_"
    else:
        records = [dict(values) for values in series]
        prefix = (
            f"{column.removesuffix('unit_modes')}mode_"
            if column.endswith("unit_modes")
            else f"{column[:-1]}_"
        )
    return pd.DataFrame.from_records(records, index=series.index).fillna(0).add_prefix(prefix)


def _split_count(total: int, fraction: float) -> int:
    return max(1, round(total * fraction)) if fraction > 0 else 0
