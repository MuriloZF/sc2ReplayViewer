import hashlib
import json
import os
import struct
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import Image

from backend.app.replay.decoder import MapReference

MAX_MAP_ARCHIVE_BYTES = 100 * 1024 * 1024

type Downloader = Callable[[str], bytes]
type MinimapExtractor = Callable[[bytes], bytes]
type MapInfoExtractor = Callable[[bytes], bytes]
type PngConverter = Callable[[bytes, Path], None]


class MapAssetError(RuntimeError):
    """Raised when an exact minimap asset cannot be resolved or decoded."""


@dataclass(frozen=True, slots=True)
class MapBounds:
    width: int
    height: int
    playable_left: int
    playable_bottom: int
    playable_right: int
    playable_top: int


class MapAssetResolver:
    """Resolve content-addressed SC2 map archives into cached minimap PNGs."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        downloader: Downloader | None = None,
        minimap_extractor: MinimapExtractor | None = None,
        map_info_extractor: MapInfoExtractor | None = None,
        png_converter: PngConverter | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        self._downloader = downloader or _download
        self._minimap_extractor = minimap_extractor or _extract_minimap
        self._map_info_extractor = map_info_extractor or _extract_map_info
        self._png_converter = png_converter or _convert_to_png

    def resolve(self, reference: MapReference) -> Path:
        """Return a cached PNG path, downloading and converting it when absent."""

        target, _bounds = self._resolve_assets(reference)
        return target

    def resolve_bounds(self, reference: MapReference) -> MapBounds:
        """Return cached authoritative dimensions and playable map bounds."""

        _target, bounds = self._resolve_assets(reference)
        return bounds

    def _resolve_assets(self, reference: MapReference) -> tuple[Path, MapBounds]:
        target = self._cache_dir / f"{reference.content_hash}.png"
        metadata_target = self._cache_dir / f"{reference.content_hash}.json"
        if target.is_file() and metadata_target.is_file():
            try:
                bounds = MapBounds(**json.loads(metadata_target.read_text(encoding="utf-8")))
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                metadata_target.unlink(missing_ok=True)
            else:
                return target, bounds

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        archive = self._downloader(depot_url(reference))
        actual_hash = hashlib.sha256(archive).hexdigest()
        if actual_hash != reference.content_hash:
            raise MapAssetError(
                f"Map archive hash mismatch: expected {reference.content_hash}, got {actual_hash}"
            )

        try:
            bounds = parse_map_info(self._map_info_extractor(archive))
            if not target.is_file():
                minimap = self._minimap_extractor(archive)
                _write_png_atomically(
                    minimap, target, self._cache_dir, reference.content_hash, self._png_converter
                )
            _write_json_atomically(bounds, metadata_target, self._cache_dir, reference.content_hash)
        except MapAssetError:
            raise
        except Exception as exc:
            raise MapAssetError(f"Unable to decode minimap asset: {exc}") from exc
        return target, bounds


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
    return _extract_archive_file(archive_contents, "Minimap.tga")


def _extract_map_info(archive_contents: bytes) -> bytes:
    return _extract_archive_file(archive_contents, "MapInfo")


def _extract_archive_file(archive_contents: bytes, filename: str) -> bytes:
    from mpyq import MPQArchive  # type: ignore[import-untyped]

    with tempfile.TemporaryDirectory() as directory:
        archive_path = Path(directory) / "map.s2ma"
        archive_path.write_bytes(archive_contents)
        archive: Any = MPQArchive(str(archive_path))
        contents = archive.read_file(filename)
    if not isinstance(contents, bytes):
        raise MapAssetError(f"Map archive does not contain {filename}")
    return contents


def _convert_to_png(tga_contents: bytes, target: Path) -> None:
    with Image.open(BytesIO(tga_contents)) as image:
        image.convert("RGB").save(target, format="PNG")


def _write_png_atomically(
    minimap: bytes,
    target: Path,
    cache_dir: Path,
    content_hash: str,
    converter: PngConverter,
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{content_hash}-", suffix=".png", dir=cache_dir
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        converter(minimap, temporary_path)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_json_atomically(
    bounds: MapBounds, target: Path, cache_dir: Path, content_hash: str
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{content_hash}-", suffix=".json", dir=cache_dir, text=True
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(asdict(bounds), output)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def parse_map_info(contents: bytes) -> MapBounds:
    """Parse the version-gated MapInfo prefix containing playable bounds."""

    reader = _MapInfoReader(contents)
    if reader.u32() != 0x4D617049:
        raise MapAssetError("MapInfo has an invalid magic value")
    version = reader.u32()
    if not 4 <= version <= 39:
        raise MapAssetError(f"Unsupported MapInfo version: {version}")
    if version >= 0x18:
        reader.skip(8)
    width, height = reader.u32(), reader.u32()
    locale_mode = reader.u32()
    if locale_mode == 2:
        reader.cstring()
    if version >= 0x16 and reader.u32() == 2:
        reader.cstring()
    if version >= 0x1C:
        reader.cstring()
    if version >= 0x25:
        reader.cstring()
    if version >= 0x1D:
        reader.u32()
    if version >= 0x0B:
        reader.u32()
    if version >= 3:
        reader.cstring()
    else:
        reader.u32()
    reader.cstring()
    if 2 <= version < 5:
        reader.cstring()
    if version < 8:
        raise MapAssetError(f"MapInfo version {version} does not contain playable bounds")
    bounds = MapBounds(width, height, reader.i32(), reader.i32(), reader.i32(), reader.i32())
    if not (
        0 <= bounds.playable_left < bounds.playable_right <= width <= 256
        and 0 <= bounds.playable_bottom < bounds.playable_top <= height <= 256
    ):
        raise MapAssetError("MapInfo contains invalid playable bounds")
    return bounds


class _MapInfoReader:
    def __init__(self, contents: bytes) -> None:
        self._contents = contents
        self._offset = 0

    def skip(self, size: int) -> None:
        self._read(size)

    def u32(self) -> int:
        return cast(int, struct.unpack("<I", self._read(4))[0])

    def i32(self) -> int:
        return cast(int, struct.unpack("<i", self._read(4))[0])

    def cstring(self) -> None:
        try:
            self._offset = self._contents.index(b"\x00", self._offset) + 1
        except ValueError as exc:
            raise MapAssetError("MapInfo contains an unterminated string") from exc

    def _read(self, size: int) -> bytes:
        end = self._offset + size
        if end > len(self._contents):
            raise MapAssetError("MapInfo ended unexpectedly")
        value = self._contents[self._offset : end]
        self._offset = end
        return value
