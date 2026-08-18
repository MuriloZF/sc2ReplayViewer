import importlib.util
import sys
from collections.abc import Callable, Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol, cast

from backend.app.replay.decoder.models import DecodedReplay, RawEvent, ReplayMetadata
from backend.app.replay.decoder.normalizer import normalize_tracker_events
from backend.app.replay.events import PlayerInfo, PlayerResult


class ReplayDecodeError(RuntimeError):
    """Raised when a replay archive cannot be decoded safely."""


class Archive(Protocol):
    header: Mapping[str, Any]

    def read_file(self, filename: str) -> bytes | None: ...


ArchiveFactory = Callable[[str], Archive]
ProtocolResolver = Callable[[int], ModuleType]


class S2ProtocolAdapter:
    """Decode MPQ replay sections and normalize tracker events."""

    def __init__(
        self,
        archive_factory: ArchiveFactory | None = None,
        latest_protocol: Callable[[], ModuleType] | None = None,
        protocol_resolver: ProtocolResolver | None = None,
    ) -> None:
        if archive_factory is None or latest_protocol is None or protocol_resolver is None:
            archive_factory, latest_protocol, protocol_resolver = _load_s2protocol()
        self._archive_factory = archive_factory
        self._latest_protocol = latest_protocol
        self._protocol_resolver = protocol_resolver

    def decode(self, replay_path: str | Path) -> DecodedReplay:
        path = Path(replay_path)
        if not path.is_file():
            raise ReplayDecodeError(f"Replay file does not exist: {path}")

        try:
            archive = self._archive_factory(str(path))
            header_content = archive.header["user_data_header"]["content"]
            header = self._latest_protocol().decode_replay_header(header_content)
            base_build = int(header["m_version"]["m_baseBuild"])
            protocol = self._protocol_resolver(base_build)
            details = protocol.decode_replay_details(_required_file(archive, "replay.details"))
            tracker_events = tuple(
                cast(
                    Iterable[RawEvent],
                    protocol.decode_replay_tracker_events(
                        _required_file(archive, "replay.tracker.events")
                    ),
                )
            )
            game_events = tuple(
                cast(
                    Iterable[RawEvent],
                    protocol.decode_replay_game_events(
                        _required_file(archive, "replay.game.events")
                    ),
                )
            )
        except ReplayDecodeError:
            raise
        except Exception as exc:
            raise ReplayDecodeError(f"Unable to decode replay {path.name}: {exc}") from exc

        unit_events, economy_events = normalize_tracker_events(tracker_events)
        metadata = ReplayMetadata(
            base_build=base_build,
            elapsed_game_loops=int(header.get("m_elapsedGameLoops", 0)),
            map_name=_text(details.get("m_title", "Unknown map")),
            players=_players(details),
        )
        return DecodedReplay(metadata, unit_events, economy_events, game_events)


def _load_s2protocol() -> tuple[ArchiveFactory, Callable[[], ModuleType], ProtocolResolver]:
    try:
        from mpyq import MPQArchive  # type: ignore[import-untyped]
    except (ImportError, ModuleNotFoundError) as exc:
        raise ReplayDecodeError("s2protocol and mpyq must be installed to decode replays") from exc
    return (
        cast(ArchiveFactory, MPQArchive),
        lambda: _load_protocol_module(),
        lambda build: _load_protocol_module(build),
    )


@lru_cache
def _load_protocol_module(build: int | None = None) -> ModuleType:
    """Load generated protocol modules without s2protocol's removed ``imp`` dependency."""

    package = importlib.util.find_spec("s2protocol")
    if package is None or package.submodule_search_locations is None:
        raise ReplayDecodeError("The s2protocol package is not installed")

    versions_path = Path(next(iter(package.submodule_search_locations))) / "versions"
    if build is None:
        candidates = list(versions_path.glob("protocol[0-9]*.py"))
        if not candidates:
            raise ReplayDecodeError("s2protocol does not contain any protocol definitions")
        protocol_path = max(candidates, key=lambda path: int(path.stem.removeprefix("protocol")))
    else:
        protocol_path = versions_path / f"protocol{build:05d}.py"
        if not protocol_path.is_file():
            raise ReplayDecodeError(f"Unsupported StarCraft II base build: {build}")

    module_name = f"_sc2_replay_protocol_{protocol_path.stem}"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(module_name, protocol_path)
    if spec is None or spec.loader is None:
        raise ReplayDecodeError(f"Unable to load protocol definition {protocol_path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _required_file(archive: Archive, filename: str) -> bytes:
    contents = archive.read_file(filename)
    if contents is None:
        raise ReplayDecodeError(f"Replay archive is missing {filename}")
    return contents


def _players(details: Mapping[str, Any]) -> tuple[PlayerInfo, ...]:
    raw_players = details.get("m_playerList", ())
    if not isinstance(raw_players, Iterable):
        return ()
    players: list[PlayerInfo] = []
    for index, raw_player in enumerate(raw_players, start=1):
        if not isinstance(raw_player, Mapping):
            continue
        players.append(
            PlayerInfo(
                player_id=int(raw_player.get("m_workingSetSlotId", index - 1)) + 1,
                name=_text(raw_player.get("m_name", f"Player {index}")),
                race=_text(raw_player.get("m_race", "Unknown")),
                result=_result(raw_player.get("m_result")),
            )
        )
    return tuple(players)


def _result(value: object) -> PlayerResult:
    if not isinstance(value, int):
        return PlayerResult.UNKNOWN
    return {1: PlayerResult.WIN, 2: PlayerResult.LOSS, 3: PlayerResult.TIE}.get(
        value, PlayerResult.UNKNOWN
    )


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
