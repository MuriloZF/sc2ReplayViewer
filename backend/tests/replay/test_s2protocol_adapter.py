from collections.abc import Mapping
from pathlib import Path
from typing import Any

from backend.app.replay.decoder import S2ProtocolAdapter


class FakeArchive:
    header: Mapping[str, Any] = {"user_data_header": {"content": b"header"}}

    def __init__(self, _path: str) -> None:
        pass

    def read_file(self, filename: str) -> bytes | None:
        return {
            "replay.details": b"details",
            "replay.tracker.events": b"tracker",
            "replay.game.events": b"game",
        }.get(filename)


class HeaderProtocol:
    @staticmethod
    def decode_replay_header(_contents: bytes) -> dict[str, object]:
        return {"m_version": {"m_baseBuild": 99_999}, "m_elapsedGameLoops": 224}


class ReplayProtocol:
    @staticmethod
    def decode_replay_details(_contents: bytes) -> dict[str, object]:
        return {
            "m_title": b"Test Map",
            "m_playerList": [
                {
                    "m_workingSetSlotId": 0,
                    "m_name": b"Alpha",
                    "m_race": b"Terran",
                    "m_result": 1,
                }
            ],
        }

    @staticmethod
    def decode_replay_tracker_events(_contents: bytes) -> list[dict[str, object]]:
        return [
            {
                "_event": "NNet.Replay.Tracker.SUnitBornEvent",
                "_gameloop": 0,
                "m_unitTagIndex": 1,
                "m_unitTagRecycle": 0,
                "m_unitTypeName": b"SCV",
                "m_controlPlayerId": 1,
            }
        ]

    @staticmethod
    def decode_replay_game_events(_contents: bytes) -> list[dict[str, object]]:
        return []


def test_decodes_replay_sections(tmp_path: Path) -> None:
    replay_path = tmp_path / "test.SC2Replay"
    replay_path.write_bytes(b"fake archive")
    adapter = S2ProtocolAdapter(
        archive_factory=FakeArchive,
        latest_protocol=lambda: HeaderProtocol,  # type: ignore[return-value]
        protocol_resolver=lambda _build: ReplayProtocol,  # type: ignore[return-value]
    )

    replay = adapter.decode(replay_path)

    assert replay.metadata.base_build == 99_999
    assert replay.metadata.map_name == "Test Map"
    assert replay.metadata.players[0].name == "Alpha"
    assert replay.unit_events[0].unit_type == "SCV"
