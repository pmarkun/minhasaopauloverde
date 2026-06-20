import json
import math
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

import pyproj
import shapefile


def load_geojson(source: str) -> dict[str, Any]:
    if source.startswith(("http://", "https://")):
        request = urllib.request.Request(source, headers={"User-Agent": "TreeCheck MVP"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def load_shapefile_records(source: str, default_epsg: int = 31983) -> list[dict[str, Any]]:
    source_path = Path(source)
    with tempfile.TemporaryDirectory() as temp_dir:
        if source_path.suffix.lower() == ".zip":
            zipfile.ZipFile(source_path).extractall(temp_dir)
            shp_path = next(Path(temp_dir).rglob("*.shp"))
        else:
            shp_path = source_path
        reader = shapefile.Reader(str(shp_path), encoding=encoding_for(shp_path))
        transformer = transformer_for(shp_path, default_epsg)
        fields = [field[0] for field in reader.fields[1:]]
        records = []
        for index, shape_record in enumerate(reader.iterShapeRecords()):
            properties = dict(zip(fields, shape_record.record))
            records.append(
                {
                    "index": index,
                    "shape": shape_record.shape,
                    "properties": properties,
                    "transformer": transformer,
                },
            )
        return records


def iter_shapefile_records(source: str, default_epsg: int = 31983):
    source_path = Path(source)
    with tempfile.TemporaryDirectory() as temp_dir:
        if source_path.suffix.lower() == ".zip":
            zipfile.ZipFile(source_path).extractall(temp_dir)
            shp_path = next(Path(temp_dir).rglob("*.shp"))
        else:
            shp_path = source_path
        reader = shapefile.Reader(str(shp_path), encoding=encoding_for(shp_path))
        transformer = transformer_for(shp_path, default_epsg)
        fields = [field[0] for field in reader.fields[1:]]
        for index, shape_record in enumerate(reader.iterShapeRecords()):
            yield {
                "index": index,
                "shape": shape_record.shape,
                "properties": dict(zip(fields, shape_record.record)),
                "transformer": transformer,
            }


def transformer_for(shp_path: Path, default_epsg: int) -> pyproj.Transformer:
    prj_path = shp_path.with_suffix(".prj")
    if prj_path.exists():
        source_crs = pyproj.CRS.from_wkt(prj_path.read_text(encoding="utf-8", errors="ignore"))
    else:
        source_crs = pyproj.CRS.from_epsg(default_epsg)
    return pyproj.Transformer.from_crs(source_crs, pyproj.CRS.from_epsg(4326), always_xy=True)


def encoding_for(shp_path: Path) -> str:
    cpg_path = shp_path.with_suffix(".cpg")
    if not cpg_path.exists():
        return "latin1"
    value = cpg_path.read_text(encoding="utf-8", errors="ignore").strip().lower()
    if value in {"1252", "windows-1252"}:
        return "cp1252"
    if value in {"65001", "utf-8"}:
        return "utf-8"
    return value or "latin1"


def tree_point_from_shape_record(item: dict[str, Any]) -> dict[str, Any] | None:
    shape = item["shape"]
    if not shape.points:
        return None
    x, y = shape.points[0]
    lng, lat = item["transformer"].transform(x, y)
    properties = item["properties"]
    return {
        "lat": round(lat, 7),
        "lng": round(lng, 7),
        "species": properties.get("especie") or properties.get("nome_popular") or "geosampa",
        "source_id": item["index"],
    }


def canopy_patch_from_shape_record(item: dict[str, Any]) -> dict[str, Any] | None:
    shape = item["shape"]
    if not shape.points:
        return None
    min_x, min_y, max_x, max_y = shape.bbox
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    lng, lat = item["transformer"].transform(center_x, center_y)
    radius = max(8, min(180, round(math.sqrt((max_x - min_x) ** 2 + (max_y - min_y) ** 2) / 2)))
    return {
        "lat": round(lat, 7),
        "lng": round(lng, 7),
        "radius_m": radius,
        "source_id": item["index"],
    }


def green_area_from_shape_record(item: dict[str, Any]) -> dict[str, Any] | None:
    shape = item["shape"]
    if not shape.points:
        return None
    min_x, min_y, max_x, max_y = shape.bbox
    transformer = item["transformer"]
    west, south = transformer.transform(min_x, min_y)
    east, north = transformer.transform(max_x, max_y)
    center_lng = (west + east) / 2
    center_lat = (south + north) / 2
    properties = item["properties"]
    name_parts = [
        str(properties.get("categoria") or "").strip(),
        str(properties.get("titulo") or "").strip(),
        str(properties.get("preposicao") or "").strip(),
        str(properties.get("nome") or "").strip(),
    ]
    name = " ".join(part for part in name_parts if part) or f"GeoSampa {item['index']}"
    return {
        "name": name,
        "lat": round(center_lat, 7),
        "lng": round(center_lng, 7),
        "width": max(0.0001, abs(east - west)),
        "height": max(0.0001, abs(north - south)),
        "entrances": [(round(center_lat, 7), round(center_lng, 7))],
        "source_id": properties.get("cd_identif") or item["index"],
    }


def in_bbox(lat: float, lng: float, south: float, west: float, north: float, east: float) -> bool:
    return south <= lat <= north and west <= lng <= east


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
