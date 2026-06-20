from math import asin, atan2, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000
DEG_LAT_M = 111_320


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    rlat1 = radians(lat1)
    rlat2 = radians(lat2)
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def walking_distance_m(lat: float, lng: float, targets: list[tuple[float, float]]) -> int:
    direct = min(haversine_m(lat, lng, target_lat, target_lng) for target_lat, target_lng in targets)
    return round(direct * 1.25)


def estimate_canopy_percent(lat: float, lng: float, radius_m: int, patches: list[dict]) -> float:
    step_m = 25
    hits = 0
    total = 0
    lng_meter = DEG_LAT_M * cos(radians(lat))
    steps = range(-radius_m, radius_m + 1, step_m)
    for y_m in steps:
        for x_m in steps:
            if x_m * x_m + y_m * y_m > radius_m * radius_m:
                continue
            total += 1
            point_lat = lat + y_m / DEG_LAT_M
            point_lng = lng + x_m / lng_meter
            if any(
                haversine_m(point_lat, point_lng, patch["lat"], patch["lng"]) <= patch["radius_m"]
                for patch in patches
            ):
                hits += 1
    return round((hits / total) * 100, 1) if total else 0.0


def circle_polygon(lng: float, lat: float, radius_m: int) -> dict:
    points = 72
    lat_rad = radians(lat)
    lng_rad = radians(lng)
    distance = radius_m / EARTH_RADIUS_M
    coordinates = []
    for index in range(points + 1):
        bearing = (index / points) * 3.141592653589793 * 2
        point_lat = asin(
            sin(lat_rad) * cos(distance)
            + cos(lat_rad) * sin(distance) * cos(bearing),
        )
        point_lng = lng_rad + atan2(
            sin(bearing) * sin(distance) * cos(lat_rad),
            cos(distance) - sin(lat_rad) * sin(point_lat),
        )
        coordinates.append([point_lng * 180 / 3.141592653589793, point_lat * 180 / 3.141592653589793])
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coordinates]},
        "properties": {},
    }
