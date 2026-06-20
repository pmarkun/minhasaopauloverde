import json
import math
import urllib.request
from pathlib import Path
from typing import Any


def load_geojson(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "TreeCheck MVP"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def features(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("type") == "FeatureCollection":
        return payload.get("features", [])
    if payload.get("features"):
        return payload["features"]
    raise ValueError("Entrada deve ser GeoJSON FeatureCollection.")


def point_from_feature(feature: dict[str, Any]) -> tuple[float, float] | None:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return None
    geometry_type = geometry.get("type")
    if geometry_type == "Point":
        lng, lat = coordinates[:2]
        return float(lat), float(lng)
    if geometry_type == "MultiPoint":
        lng, lat = coordinates[0][:2]
        return float(lat), float(lng)
    if geometry_type == "Polygon":
        return centroid(coordinates[0])
    if geometry_type == "MultiPolygon":
        return centroid(coordinates[0][0])
    return None


def canopy_patch_from_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    point = point_from_feature(feature)
    if not point:
        return None
    lat, lng = point
    radius = radius_from_geometry(feature.get("geometry") or {})
    return {
        "lat": lat,
        "lng": lng,
        "radius_m": radius,
        "source_id": source_id(feature),
    }


def tree_point_from_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    point = point_from_feature(feature)
    if not point:
        return None
    lat, lng = point
    properties = feature.get("properties") or {}
    return {
        "lat": lat,
        "lng": lng,
        "species": properties.get("especie") or properties.get("nome_popular") or properties.get("species") or "geosampa",
        "source_id": source_id(feature),
    }


def centroid(ring: list[list[float]]) -> tuple[float, float]:
    lng_sum = 0.0
    lat_sum = 0.0
    count = 0
    for point in ring:
        lng_sum += float(point[0])
        lat_sum += float(point[1])
        count += 1
    if count == 0:
        raise ValueError("Geometria sem coordenadas.")
    return lat_sum / count, lng_sum / count


def radius_from_geometry(geometry: dict[str, Any]) -> int:
    coordinates = geometry.get("coordinates")
    if not coordinates:
        return 12
    geometry_type = geometry.get("type")
    ring = coordinates[0] if geometry_type == "Polygon" else coordinates[0][0] if geometry_type == "MultiPolygon" else []
    if not ring:
        return 12
    lat, lng = centroid(ring)
    distances = [distance_m(lat, lng, float(point[1]), float(point[0])) for point in ring]
    return max(8, min(180, round(max(distances) if distances else 12)))


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat_m = (lat2 - lat1) * 111_320
    lng_m = (lng2 - lng1) * 111_320 * math.cos(math.radians(lat1))
    return math.sqrt(lat_m * lat_m + lng_m * lng_m)


def source_id(feature: dict[str, Any]) -> str | int | None:
    properties = feature.get("properties") or {}
    return feature.get("id") or properties.get("id") or properties.get("fid") or properties.get("objectid")

