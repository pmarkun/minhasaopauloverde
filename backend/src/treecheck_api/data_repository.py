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


def spatial_db_path() -> Path:
    return data_root() / "treecheck.sqlite"


def canopy_sqlite_path() -> Path:
    return data_root() / "canopy_polygons.sqlite"


def sqlite_has_table(path: Path, table_name: str) -> bool:
    if not path.exists():
        return False
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = ?",
            (table_name,),
        ).fetchone()
    return bool(row)


def sqlite_source(path: Path, key: str, default: str) -> str:
    if not path.exists():
        return default
    with sqlite3.connect(path) as connection:
        row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


@lru_cache
def green_areas() -> list[dict[str, Any]]:
    path = data_root() / "green_areas.json"
    if not path.exists():
        return GREEN_AREAS
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload["green_areas"]


@lru_cache
def canopy_patches() -> list[dict[str, Any]]:
    path = data_root() / "canopy_patches.json"
    if not path.exists():
        return CANOPY_PATCHES
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload["canopy_patches"]


def canopy_patches_near(lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    if sqlite_has_table(spatial_db_path(), "canopy"):
        return canopy_patches_from_sqlite(spatial_db_path(), lat, lng, radius_m)
    if sqlite_has_table(canopy_sqlite_path(), "canopy"):
        return canopy_patches_from_sqlite(canopy_sqlite_path(), lat, lng, radius_m)
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
    if sqlite_has_table(spatial_db_path(), "canopy"):
        return sqlite_source(spatial_db_path(), "canopy_source", "geosampa_cobertura_vegetal")
    if sqlite_has_table(canopy_sqlite_path(), "canopy"):
        return sqlite_source(canopy_sqlite_path(), "canopy_source", "geosampa_cobertura_vegetal")
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


def green_areas_near(lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    if sqlite_has_table(spatial_db_path(), "green_area"):
        return green_areas_from_sqlite(spatial_db_path(), lat, lng, radius_m)
    return nearby_items(lat, lng, radius_m, green_areas())


def green_areas_for_nearest(lat: float, lng: float) -> list[dict[str, Any]]:
    if not sqlite_has_table(spatial_db_path(), "green_area"):
        return green_areas()
    for radius_m in (500, 1000, 2500, 5000, 10000, 25000):
        candidates = green_areas_from_sqlite(spatial_db_path(), lat, lng, radius_m)
        if candidates:
            return candidates
    return green_areas_from_sqlite(spatial_db_path(), lat, lng, 50000)


def green_areas_from_sqlite(path: Path, lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    min_lng, min_lat, max_lng, max_lat = bbox_for_radius(lat, lng, radius_m)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT g.source_id, g.name, g.lat, g.lng, g.width, g.height, g.entrances, g.geometry
            FROM green_area_index i
            JOIN green_area g ON g.id = i.id
            WHERE i.min_lng <= ?
              AND i.max_lng >= ?
              AND i.min_lat <= ?
              AND i.max_lat >= ?
            """,
            (max_lng, min_lng, max_lat, min_lat),
        ).fetchall()
    return [
        {
            "name": row["name"],
            "lat": row["lat"],
            "lng": row["lng"],
            "width": row["width"],
            "height": row["height"],
            "entrances": [tuple(point) for point in json.loads(row["entrances"])],
            "geometry": json.loads(row["geometry"]) if row["geometry"] else None,
            "source_id": row["source_id"],
        }
        for row in rows
    ]


def tree_points_source() -> str:
    if sqlite_has_table(spatial_db_path(), "tree"):
        return sqlite_source(spatial_db_path(), "tree_source", "geosampa_arborizacao_viaria")
    path = data_root() / "tree_points.json"
    if not path.exists():
        return "sample_local"
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("source", "processed_local")


def green_areas_source() -> str:
    if sqlite_has_table(spatial_db_path(), "green_area"):
        return sqlite_source(spatial_db_path(), "green_area_source", "geosampa_praca_largo")
    path = data_root() / "green_areas.json"
    if not path.exists():
        return "sample_local"
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("source", "processed_local")


def tree_points_near(lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    if sqlite_has_table(spatial_db_path(), "tree"):
        return tree_points_from_sqlite(spatial_db_path(), lat, lng, radius_m)
    return nearby_items(lat, lng, radius_m, tree_points())


def nearest_tree_points(lat: float, lng: float, limit: int = 3) -> list[dict[str, Any]]:
    if sqlite_has_table(spatial_db_path(), "tree"):
        for radius_m in (100, 300, 600, 1200, 2500):
            trees = tree_points_from_sqlite(spatial_db_path(), lat, lng, radius_m)
            if len(trees) >= limit:
                return sorted(trees, key=lambda tree: abs(tree["lat"] - lat) + abs(tree["lng"] - lng))[:limit]
    return sorted(tree_points(), key=lambda tree: abs(tree["lat"] - lat) + abs(tree["lng"] - lng))[:limit]


def tree_points_from_sqlite(path: Path, lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    min_lng, min_lat, max_lng, max_lat = bbox_for_radius(lat, lng, radius_m)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT t.source_id, t.lat, t.lng, t.species
            FROM tree_index i
            JOIN tree t ON t.id = i.id
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
            "species": row["species"],
            "source_id": row["source_id"],
        }
        for row in rows
    ]


def sample_addresses() -> dict:
    return SAMPLE_ADDRESSES


def pilot_territories() -> list[dict]:
    return PILOT_TERRITORIES
