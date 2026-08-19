import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import Image

from backend.app.replay.decoder import MapReference

MAX_MAP_ARCHIVE_BYTES = 100 * 1024 * 1024

type Downloader = Callable[[str], bytes]
type MinimapExtractor = Callable[[bytes], bytes]
type PngConverter = Callable[[bytes, Path], None]


class MapAssetError(RuntimeError):
    """Raised when an exact minimap asset cannot be resolved or decoded."""


class MapAssetResolver:
    """Resolve content-addressed SC2 map archives into cached minimap PNGs."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        downloader: Downloader | None = None,
        minimap_extractor: MinimapExtractor | None = None,
        png_converter: PngConverter | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        self._downloader = downloader or _download
        self._minimap_extractor = minimap_extractor or _extract_minimap
        self._png_converter = png_converter or _convert_to_png

    def resolve(self, reference: MapReference) -> Path:
        """Return a cached PNG path, downloading and converting it when absent."""

        target = self._cache_dir / f"{reference.content_hash}.png"
        if target.is_file():
            return target

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        archive = self._downloader(depot_url(reference))
        actual_hash = hashlib.sha256(archive).hexdigest()
        if actual_hash != reference.content_hash:
            raise MapAssetError(
                f"Map archive hash mismatch: expected {reference.content_hash}, got {actual_hash}"
            )

        try:
            minimap = self._minimap_extractor(archive)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{reference.content_hash}-", suffix=".png", dir=self._cache_dir
            )
            os.close(descriptor)
            temporary_path = Path(temporary_name)
            try:
                self._png_converter(minimap, temporary_path)
                os.replace(temporary_path, target)
            finally:
                temporary_path.unlink(missing_ok=True)
        except MapAssetError:
            raise
        except Exception as exc:
            raise MapAssetError(f"Unable to decode minimap asset: {exc}") from exc
        return target


def depot_url(reference: MapReference) -> str:
    """Build the Blizzard depot URL for a parsed map reference."""

    region = "us" if reference.region in {"sea", "sg"} else reference.region
    return (
        f"https://{region}-s2-depot.classic.blizzard.com/"
        f"{reference.content_hash}.{reference.archive_type}"
    )


def _download(url: str) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310
            contents = cast(bytes, response.read(MAX_MAP_ARCHIVE_BYTES + 1))
    except (OSError, urllib.error.URLError) as exc:
        raise MapAssetError(f"Unable to download map archive: {exc}") from exc
    if len(contents) > MAX_MAP_ARCHIVE_BYTES:
        raise MapAssetError("Map archive exceeds the 100 MB download limit")
    return contents


def _extract_minimap(archive_contents: bytes) -> bytes:
    from mpyq import MPQArchive  # type: ignore[import-untyped]

    with tempfile.TemporaryDirectory() as directory:
        archive_path = Path(directory) / "map.s2ma"
        archive_path.write_bytes(archive_contents)
        archive: Any = MPQArchive(str(archive_path))
        minimap = archive.read_file("Minimap.tga")
    if not isinstance(minimap, bytes):
        raise MapAssetError("Map archive does not contain Minimap.tga")
    return minimap


def _convert_to_png(tga_contents: bytes, target: Path) -> None:
    with Image.open(BytesIO(tga_contents)) as image:
        image.convert("RGB").save(target, format="PNG")
