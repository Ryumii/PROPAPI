"""Geospatial file reading, CRS transformation, and geometry helpers."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import shapefile as shp
from pyproj import Transformer
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.ops import transform

logger = logging.getLogger(__name__)

# ── CRS transformers (cached) ────────────────────────────────
_JGD2011_TO_WGS84 = Transformer.from_crs("EPSG:6668", "EPSG:4326", always_xy=True)


def transform_to_wgs84(geom: Any, *, source_epsg: int = 6668) -> Any:
    """Reproject geometry to WGS84 (EPSG:4326).

    JGD2011 (EPSG:6668) → WGS84 is sub-metre difference;
    included for correctness.
    """
    if source_epsg == 4326:
        return geom
    if source_epsg == 6668:
        return transform(_JGD2011_TO_WGS84.transform, geom)
    t = Transformer.from_crs(f"EPSG:{source_epsg}", "EPSG:4326", always_xy=True)
    return transform(t.transform, geom)


def ensure_multi(geom: Any) -> Any:
    """Coerce Polygon → MultiPolygon. Pass-through Point/MultiPoint as-is."""
    if geom.geom_type == "MultiPolygon":
        return geom
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type in ("Point", "MultiPoint"):
        return geom
    msg = f"Unexpected geometry type: {geom.geom_type}"
    raise ValueError(msg)


def geom_to_geojson(geom: Any) -> str:
    """Serialise a Shapely geometry to GeoJSON string."""
    return json.dumps(mapping(geom))


# ── File readers ─────────────────────────────────────────────

def read_geojson(path: Path) -> Iterator[tuple[Any, dict[str, Any]]]:
    """Yield (shapely_geom, properties) from a GeoJSON FeatureCollection."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    logger.info("Reading %d features from %s", len(features), path.name)
    for feat in features:
        geom_data = feat.get("geometry")
        if geom_data is None:
            continue
        geom = shape(geom_data)
        props = feat.get("properties", {})
        yield geom, props


def read_shapefile(path: Path) -> Iterator[tuple[Any, dict[str, Any]]]:
    """Yield (shapely_geom, properties) from a Shapefile (.shp).

    Uses pyshp — no GDAL dependency required.
    Tries UTF-8 first, falls back to CP932 (Shift_JIS) for Japanese data.
    """
    # Determine encoding: check .cpg file, then try utf-8, fallback cp932
    cpg_path = path.with_suffix(".cpg")
    encoding = "utf-8"
    if cpg_path.exists():
        encoding = cpg_path.read_text().strip() or "utf-8"
    else:
        # Probe: try to read first record with utf-8
        try:
            test_reader = shp.Reader(str(path), encoding="utf-8")
            next(test_reader.iterShapeRecords())
        except (UnicodeDecodeError, StopIteration):
            encoding = "cp932"

    reader = shp.Reader(str(path), encoding=encoding)
    count = len(reader)
    logger.info("Reading %d records from %s (encoding=%s)", count, path.name, encoding)
    for sr in reader.iterShapeRecords():
        geom = shape(sr.shape.__geo_interface__)
        props = sr.record.as_dict()
        yield geom, props


def read_features(path: Path) -> Iterator[tuple[Any, dict[str, Any]]]:
    """Auto-detect format and yield (geom, properties).

    Supports: .geojson / .json (GeoJSON) and .shp (Shapefile).
    """
    suffix = path.suffix.lower()
    if suffix in (".geojson", ".json"):
        yield from read_geojson(path)
    elif suffix == ".shp":
        yield from read_shapefile(path)
    else:
        msg = f"Unsupported file format: {suffix}  (use .geojson or .shp)"
        raise ValueError(msg)


def find_files(
    directory: Path,
    patterns: tuple[str, ...] = ("*.geojson", "*.shp"),
    *,
    recursive: bool = True,
) -> list[Path]:
    """Glob for matching files in a directory.

    When *recursive* is True (default), searches subdirectories as well.
    """
    files: list[Path] = []
    for pat in patterns:
        if recursive:
            files.extend(sorted(directory.rglob(pat)))
        else:
            files.extend(sorted(directory.glob(pat)))
    return files


# ── Attribute helpers ────────────────────────────────────────

def resolve_attr(
    props: dict[str, Any],
    candidates: list[str],
    *,
    default: Any = None,
) -> Any:
    """Return the value of the first matching key from *candidates*."""
    for key in candidates:
        if key in props and props[key] is not None:
            return props[key]
    return default


def safe_int(value: Any, *, default: int | None = None) -> int | None:
    """Convert value to int, returning *default* on failure."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, *, default: float | None = None) -> float | None:
    """Convert value to float, returning *default* on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
