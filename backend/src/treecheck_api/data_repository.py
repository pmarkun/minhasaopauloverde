import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from treecheck_api.sample_data import CANOPY_PATCHES, GREEN_AREAS, PILOT_TERRITORIES, SAMPLE_ADDRESSES, TREE_POINTS


def data_root() -> Path:
    return Path(os.environ.get("TREECHECK_DATA_DIR", "data/processed"))


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


def canopy_patches_source() -> str:
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
