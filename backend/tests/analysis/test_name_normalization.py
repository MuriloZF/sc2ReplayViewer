from backend.app.analysis.name_normalization import canonicalize_unit_name


def test_normalizes_identity_and_preserves_mode_across_builds() -> None:
    for build in (32_283, 97_563):
        tank = canonicalize_unit_name("SiegeTankSieged", base_build=build)
        viking = canonicalize_unit_name("VikingFighter", base_build=build)

        assert (tank.name, tank.mode) == ("SiegeTank", "sieged")
        assert (viking.name, viking.mode) == ("Viking", "fighter")


def test_preserves_unknown_future_patch_name() -> None:
    unit = canonicalize_unit_name("FutureExpansionUnit", base_build=999_999)

    assert unit.name == "FutureExpansionUnit"
    assert unit.mode is None
