import hashlib
from pathlib import Path

import pytest

from backend.app.replay.decoder import MapReference
from backend.app.replay.map_assets import MapAssetError, MapAssetResolver, depot_url


def test_resolves_and_reuses_cached_minimap(tmp_path: Path) -> None:
    archive = b"map archive"
    reference = MapReference("eu", "s2ma", hashlib.sha256(archive).hexdigest())
    downloads: list[str] = []

    def download(url: str) -> bytes:
        downloads.append(url)
        return archive

    def convert(tga: bytes, target: Path) -> None:
        assert tga == b"minimap tga"
        target.write_bytes(b"png image")

    resolver = MapAssetResolver(
        tmp_path,
        downloader=download,
        minimap_extractor=lambda contents: b"minimap tga" if contents == archive else b"",
        png_converter=convert,
    )

    first = resolver.resolve(reference)
    second = resolver.resolve(reference)

    assert first == second == tmp_path / f"{reference.content_hash}.png"
    assert first.read_bytes() == b"png image"
    assert downloads == [depot_url(reference)]


def test_rejects_archive_with_wrong_content_hash(tmp_path: Path) -> None:
    reference = MapReference("us", "s2ma", "ab" * 32)
    resolver = MapAssetResolver(tmp_path, downloader=lambda _url: b"wrong archive")

    with pytest.raises(MapAssetError, match="hash mismatch"):
        resolver.resolve(reference)

    assert list(tmp_path.iterdir()) == []


def test_uses_us_depot_for_legacy_sea_region() -> None:
    reference = MapReference("sea", "s2ma", "ab" * 32)

    assert depot_url(reference) == (
        "https://us-s2-depot.classic.blizzard.com/" + "ab" * 32 + ".s2ma"
    )
