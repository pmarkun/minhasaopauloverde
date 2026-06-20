from enum import Enum
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from treecheck_api.sample_data import CANOPY_PATCHES, GREEN_AREAS, SAMPLE_ADDRESSES, TREE_POINTS
from treecheck_api.spatial import circle_polygon, estimate_canopy_percent, haversine_m, walking_distance_m


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
    source: str = "sample_local"


class ParkAccessCriterion(BaseModel):
    status: str
    distance_m: int
    target_m: int = 300
    source: str = "sample_local_walking_estimate"


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
    source: str = "sample_local"


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
    for key, (lat, lng, label) in SAMPLE_ADDRESSES.items():
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
    canopy_100m = estimate_canopy_percent(lat, lng, radius_m=100, patches=CANOPY_PATCHES)
    canopy_300m = estimate_canopy_percent(lat, lng, radius_m=300, patches=CANOPY_PATCHES)
    park_distance = nearest_green_area_distance(lat, lng)

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
        parks=geojson_feature_collection(nearby_parks(lat, lng)),
        canopy=geojson_feature_collection(nearby_canopy(lat, lng)),
        trees=geojson_feature_collection(nearby_trees(lat, lng)),
    )


def status_for_bool(passed: bool, known: bool = True) -> str:
    if not known:
        return "unknown"
    return "passed" if passed else "failed"


def nearest_green_area_distance(lat: float, lng: float) -> int:
    return min(
        walking_distance_m(lat, lng, park["entrances"])
        for park in GREEN_AREAS
    )


def nearby_parks(lat: float, lng: float) -> list[dict]:
    parks = [
        rectangle_feature(
            park["lng"],
            park["lat"],
            park["width"],
            park["height"],
            {"name": park["name"]},
        )
        for park in GREEN_AREAS
        if haversine_m(lat, lng, park["lat"], park["lng"]) <= 2500
    ]
    if parks:
        return parks
    nearest = min(GREEN_AREAS, key=lambda park: haversine_m(lat, lng, park["lat"], park["lng"]))
    return [
        rectangle_feature(
            nearest["lng"],
            nearest["lat"],
            nearest["width"],
            nearest["height"],
            {"name": nearest["name"]},
        ),
    ]


def nearby_canopy(lat: float, lng: float) -> list[dict]:
    return [
        circle_polygon(patch["lng"], patch["lat"], patch["radius_m"])
        for patch in CANOPY_PATCHES
        if haversine_m(lat, lng, patch["lat"], patch["lng"]) <= 2500
    ]


def nearby_trees(lat: float, lng: float) -> list[dict]:
    trees = [
        point_feature(tree["lng"], tree["lat"], {"species": tree["species"]})
        for tree in TREE_POINTS
        if haversine_m(lat, lng, tree["lat"], tree["lng"]) <= 2500
    ]
    if len(trees) >= 3:
        return trees
    nearest = sorted(TREE_POINTS, key=lambda tree: haversine_m(lat, lng, tree["lat"], tree["lng"]))[:3]
    return [point_feature(tree["lng"], tree["lat"], {"species": tree["species"]}) for tree in nearest]


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
