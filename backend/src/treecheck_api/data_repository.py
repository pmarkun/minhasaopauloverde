import json
import os
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

from treecheck_api.sample_data import CANOPY_PATCHES, GREEN_AREAS, PILOT_TERRITORIES, SAMPLE_ADDRESSES, TREE_POINTS
from treecheck_api.spatial import bbox_for_radius, nearby_items


def data_root() -> Path:
    return Path(os.environ.get("TREECHECK_DATA_DIR", "data/processed"))


def canopy_sqlite_path() -> Path:
    return data_root() / "canopy_polygons.sqlite"


@lru_cache
def green_areas() -> list[dict[str, Any]]:
    path = data_root() / "green_areas.json"
    if not path.exists():
        return GREEN_AREAS
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload["green_areas"]


def green_areas_source() -> str:
    path = data_root() / "green_areas.json"
    if not path.exists():
        return "sample_local"
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("source", "processed_local")


@lru_cache
def canopy_patches() -> list[dict[str, Any]]:
    path = data_root() / "canopy_patches.json"
    if not path.exists():
        return CANOPY_PATCHES
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload["canopy_patches"]


def canopy_patches_near(lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    sqlite_path = canopy_sqlite_path()
    if sqlite_path.exists():
        return canopy_patches_from_sqlite(sqlite_path, lat, lng, radius_m)
    return nearby_items(lat, lng, radius_m, canopy_patches())


def canopy_patches_from_sqlite(path: Path, lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    min_lng, min_lat, max_lng, max_lat = bbox_for_radius(lat, lng, radius_m)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT c.source_id, c.lat, c.lng, c.radius_m, c.geometry
            FROM canopy_index i
            JOIN canopy c ON c.id = i.id
            WHERE i.min_lng <= ?
              AND i.max_lng >= ?
              AND i.min_lat <= ?
              AND i.max_lat >= ?
            """,
            (max_lng, min_lng, max_lat, min_lat),
        ).fetchall()
    return [
        {
            "lat": row["lat"],
            "lng": row["lng"],
            "radius_m": row["radius_m"],
            "source_id": row["source_id"],
            "geometry": json.loads(row["geometry"]),
        }
        for row in rows
    ]


def canopy_patches_source() -> str:
    sqlite_path = canopy_sqlite_path()
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = ?", ("source",)).fetchone()
        return row[0] if row else "geosampa_cobertura_vegetal"
    path = data_root() / "canopy_patches.json"
    if not path.exists():
        return "sample_local"
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("source", "processed_local")


@lru_cache
def tree_points() -> list[dict[str, Any]]:
    path = data_root() / "tree_points.json"
    if not path.exists():
        return TREE_POINTS
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload["tree_points"]


def tree_points_source() -> str:
    path = data_root() / "tree_points.json"
    if not path.exists():
        return "sample_local"
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("source", "processed_local")


def sample_addresses() -> dict:
    return SAMPLE_ADDRESSES


def pilot_territories() -> list[dict]:
    return PILOT_TERRITORIES
