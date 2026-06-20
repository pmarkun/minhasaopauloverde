from enum import Enum
from math import asin, atan2, cos, sin
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class TreeVisibility(str, Enum):
    yes = "yes"
    no = "no"
    unknown = "unknown"


class Location(BaseModel):
    lat: float
    lng: float


class Criterion(BaseModel):
    status: str
    value: bool | float | int | None = None
    source: str
    target: float | int | None = None


class CanopyCriterion(BaseModel):
    status: str
    canopy_100m: float
    canopy_300m: float
    target: int = 30
    source: str = "mock"


class ParkAccessCriterion(BaseModel):
    status: str
    distance_m: int
    target_m: int = 300
    source: str = "mock"


class ScoreCriteria(BaseModel):
    trees_visible: Criterion
    canopy: CanopyCriterion
    park_access: ParkAccessCriterion


class ScoreSummary(BaseModel):
    passed: int
    total: int = 3


class ScoreResponse(BaseModel):
    location: Location
    criteria: ScoreCriteria
    score: ScoreSummary
    recommendations: list[str] = Field(default_factory=list)


class MapDataResponse(BaseModel):
    user_buffer_300m: dict
    parks: dict
    canopy: dict
    trees: dict


class GeocodeResponse(BaseModel):
    query: str
    lat: float
    lng: float
    label: str
    source: str = "mock"


app = FastAPI(title="TreeCheck API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/geocode", response_model=GeocodeResponse)
def geocode(q: Annotated[str, Query(min_length=3)]) -> GeocodeResponse:
    normalized = q.strip().lower()
    known = {
        "avenida paulista": (-23.5614, -46.6559, "Avenida Paulista, Sao Paulo"),
        "ibirapuera": (-23.5874, -46.6576, "Parque Ibirapuera, Sao Paulo"),
        "se": (-23.5503, -46.6339, "Se, Sao Paulo"),
    }
    for key, (lat, lng, label) in known.items():
        if key in normalized:
            return GeocodeResponse(query=q, lat=lat, lng=lng, label=label)

    offset = (sum(ord(char) for char in normalized) % 1000) / 100000
    return GeocodeResponse(
        query=q,
        lat=round(-23.55 + offset, 6),
        lng=round(-46.63 - offset, 6),
        label=f"{q}, Sao Paulo aproximado",
    )


@app.get("/score", response_model=ScoreResponse)
def score(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    trees_visible: TreeVisibility = TreeVisibility.unknown,
) -> ScoreResponse:
    canopy_100m = mock_canopy(lat, lng, radius_m=100)
    canopy_300m = mock_canopy(lat, lng, radius_m=300)
    park_distance = mock_park_distance(lat, lng)

    trees_passed = trees_visible == TreeVisibility.yes
    canopy_passed = canopy_300m >= 30
    park_passed = park_distance <= 300

    return ScoreResponse(
        location=Location(lat=lat, lng=lng),
        criteria=ScoreCriteria(
            trees_visible=Criterion(
                status=status_for_bool(trees_passed, trees_visible != TreeVisibility.unknown),
                value=trees_passed if trees_visible != TreeVisibility.unknown else None,
                source="self_reported",
                target=3,
            ),
            canopy=CanopyCriterion(
                status=status_for_bool(canopy_passed),
                canopy_100m=canopy_100m,
                canopy_300m=canopy_300m,
            ),
            park_access=ParkAccessCriterion(
                status=status_for_bool(park_passed),
                distance_m=park_distance,
            ),
        ),
        score=ScoreSummary(
            passed=sum([trees_passed, canopy_passed, park_passed]),
        ),
        recommendations=recommendations(canopy_300m, park_distance, trees_visible),
    )


@app.get("/map-data", response_model=MapDataResponse)
def map_data(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
) -> MapDataResponse:
    return MapDataResponse(
        user_buffer_300m=geojson_feature_collection([circle_polygon(lng, lat, 300)]),
        parks=geojson_feature_collection(
            [
                rectangle_feature(lng + 0.0045, lat + 0.0028, 0.0035, 0.0022, {"name": "Praca Verde"}),
                rectangle_feature(lng - 0.0052, lat - 0.003, 0.004, 0.0025, {"name": "Parque Local"}),
            ],
        ),
        canopy=geojson_feature_collection(
            [
                rectangle_feature(lng - 0.002, lat + 0.002, 0.0025, 0.0012, {"canopy": "alta"}),
                rectangle_feature(lng + 0.002, lat - 0.0018, 0.003, 0.0015, {"canopy": "media"}),
            ],
        ),
        trees=geojson_feature_collection(
            [
                point_feature(lng + 0.001, lat + 0.0015, {"species": "mock"}),
                point_feature(lng - 0.0012, lat + 0.0006, {"species": "mock"}),
                point_feature(lng + 0.0028, lat - 0.001, {"species": "mock"}),
                point_feature(lng - 0.0024, lat - 0.0014, {"species": "mock"}),
            ],
        ),
    )


def status_for_bool(passed: bool, known: bool = True) -> str:
    if not known:
        return "unknown"
    return "passed" if passed else "failed"


def mock_canopy(lat: float, lng: float, radius_m: int) -> float:
    seed = abs((lat * 137.0) + (lng * 71.0) + radius_m)
    return round(12 + (seed % 31), 1)


def mock_park_distance(lat: float, lng: float) -> int:
    seed = abs((lat * 1000.0) - (lng * 900.0))
    return int(120 + (seed % 520))


def recommendations(
    canopy_300m: float,
    park_distance: int,
    trees_visible: TreeVisibility,
) -> list[str]:
    items: list[str] = []
    if canopy_300m < 30:
        items.append(f"Faltam {round(30 - canopy_300m, 1)} pontos percentuais para atingir 30%.")
    if park_distance > 300:
        items.append(f"O parque mais proximo esta {park_distance - 300} m alem da meta de 300 m.")
    if trees_visible == TreeVisibility.no:
        items.append("A janela principal nao atende ao criterio de 3 arvores visiveis.")
    if trees_visible == TreeVisibility.unknown:
        items.append("Responda sobre as arvores visiveis para completar o criterio 3.")
    return items


def geojson_feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def point_feature(lng: float, lat: float, properties: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": properties,
    }


def rectangle_feature(lng: float, lat: float, width: float, height: float, properties: dict) -> dict:
    west = lng - width / 2
    east = lng + width / 2
    south = lat - height / 2
    north = lat + height / 2
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]],
        },
        "properties": properties,
    }


def circle_polygon(lng: float, lat: float, radius_m: int) -> dict:
    points = 72
    earth_radius = 6_371_000
    lat_rad = lat * 3.141592653589793 / 180
    lng_rad = lng * 3.141592653589793 / 180
    distance = radius_m / earth_radius
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
