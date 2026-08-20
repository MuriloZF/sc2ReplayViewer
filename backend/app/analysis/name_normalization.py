from dataclasses import dataclass

NAME_NORMALIZATION_VERSION = "1"


@dataclass(frozen=True, slots=True)
class CanonicalUnitName:
    name: str
    mode: str | None = None


# These aliases describe presentation modes of the same underlying unit. They
# are not patch balance data, so they are safe across builds. Patch-specific
# aliases must be added to a build-gated table rather than this mapping.
_UNIT_MODE_ALIASES = {
    "BanelingBurrowed": CanonicalUnitName("Baneling", "burrowed"),
    "BarracksFlying": CanonicalUnitName("Barracks", "flying"),
    "ChangelingMarine": CanonicalUnitName("Changeling", "marine"),
    "ChangelingMarineShield": CanonicalUnitName("Changeling", "marine_shield"),
    "ChangelingZealot": CanonicalUnitName("Changeling", "zealot"),
    "ChangelingZergling": CanonicalUnitName("Changeling", "zergling"),
    "ChangelingZerglingWings": CanonicalUnitName("Changeling", "zergling_wings"),
    "CommandCenterFlying": CanonicalUnitName("CommandCenter", "flying"),
    "CreepTumorBurrowed": CanonicalUnitName("CreepTumor", "burrowed"),
    "CreepTumorQueen": CanonicalUnitName("CreepTumor", "queen"),
    "FactoryFlying": CanonicalUnitName("Factory", "flying"),
    "InfestorBurrowed": CanonicalUnitName("Infestor", "burrowed"),
    "OrbitalCommandFlying": CanonicalUnitName("OrbitalCommand", "flying"),
    "RoachBurrowed": CanonicalUnitName("Roach", "burrowed"),
    "SiegeTankSieged": CanonicalUnitName("SiegeTank", "sieged"),
    "SpineCrawlerUprooted": CanonicalUnitName("SpineCrawler", "uprooted"),
    "SporeCrawlerUprooted": CanonicalUnitName("SporeCrawler", "uprooted"),
    "StarportFlying": CanonicalUnitName("Starport", "flying"),
    "SupplyDepotLowered": CanonicalUnitName("SupplyDepot", "lowered"),
    "SwarmHostBurrowedMP": CanonicalUnitName("SwarmHost", "burrowed"),
    "SwarmHostMP": CanonicalUnitName("SwarmHost"),
    "VikingAssault": CanonicalUnitName("Viking", "assault"),
    "VikingFighter": CanonicalUnitName("Viking", "fighter"),
    "WarpPrismPhasing": CanonicalUnitName("WarpPrism", "phasing"),
    "WidowMineBurrowed": CanonicalUnitName("WidowMine", "burrowed"),
    "ZerglingBurrowed": CanonicalUnitName("Zergling", "burrowed"),
}

_STABLE_UNIT_ALIASES = {
    "BroodlingEscort": "Broodling",
    "LocustMP": "Locust",
}


def canonicalize_unit_name(raw_name: str, *, base_build: int) -> CanonicalUnitName:
    """Return a stable identity while retaining strategically meaningful modes."""

    del base_build  # Reserved for build-gated aliases when cross-patch evidence requires them.
    mode_alias = _UNIT_MODE_ALIASES.get(raw_name)
    if mode_alias is not None:
        return mode_alias
    return CanonicalUnitName(_STABLE_UNIT_ALIASES.get(raw_name, raw_name))


def unit_name_mapping(raw_name: str, *, base_build: int) -> dict[str, str | None]:
    canonical = canonicalize_unit_name(raw_name, base_build=base_build)
    return {"name": canonical.name, "mode": canonical.mode}
