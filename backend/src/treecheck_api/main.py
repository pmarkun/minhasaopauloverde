from enum import Enum
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from treecheck_api.data_repository import (
    canopy_patches,
    canopy_patches_source,
    green_areas,
    green_areas_source,
    pilot_territories,
    sample_addresses,
    tree_points,
)
from treecheck_api.spatial import circle_polygon, estimate_canopy_percent, haversine_m, nearby_items, walking_distance_m


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
    name: str
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
    nearest_park: dict


class GeocodeResponse(BaseModel):
    query: str
    lat: float
    lng: float
    label: str
    source: str = "sample_local"


class TerritoryIndicator(BaseModel):
    id: str
    name: str
    canopy_mean_300m: float
    park_distance_mean_m: int
    pct_meets_30: float
    pct_meets_300: float
    green_inequality_index: float


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


@app.get("/indicators", response_model=list[TerritoryIndicator])
def indicators() -> list[TerritoryIndicator]:
    return [territory_indicator(territory) for territory in pilot_territories()]


@app.get("/geocode", response_model=GeocodeResponse)
def geocode(q: Annotated[str, Query(min_length=3)]) -> GeocodeResponse:
    normalized = q.strip().lower()
    for key, (lat, lng, label) in sample_addresses().items():
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
    canopy_100m = estimate_canopy_percent(lat, lng, radius_m=100, patches=canopy_patches())
    canopy_300m = estimate_canopy_percent(lat, lng, radius_m=300, patches=canopy_patches())
    nearest_park = nearest_green_area(lat, lng)
    park_distance = nearest_park["distance_m"]

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
                source=canopy_patches_source(),
            ),
            park_access=ParkAccessCriterion(
                status=status_for_bool(park_passed),
                distance_m=park_distance,
                name=nearest_park["name"],
                source=f"{green_areas_source()}_walking_estimate",
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
    radius_m: Annotated[int, Query(ge=50, le=1000)] = 300,
) -> MapDataResponse:
    nearest_park = nearest_green_area(lat, lng)
    return MapDataResponse(
        user_buffer_300m=geojson_feature_collection([circle_polygon(lng, lat, radius_m)]),
        parks=geojson_feature_collection(nearby_parks(lat, lng, radius_m)),
        canopy=geojson_feature_collection(nearby_canopy(lat, lng, radius_m)),
        trees=geojson_feature_collection(nearby_trees(lat, lng, radius_m)),
        nearest_park=geojson_feature_collection([park_feature(nearest_park)]),
    )


def status_for_bool(passed: bool, known: bool = True) -> str:
    if not known:
        return "unknown"
    return "passed" if passed else "failed"


def nearest_green_area_distance(lat: float, lng: float) -> int:
    return nearest_green_area(lat, lng)["distance_m"]


def nearest_green_area(lat: float, lng: float) -> dict:
    park = min(green_areas(), key=lambda item: walking_distance_m(lat, lng, item["entrances"]))
    return {
        **park,
        "distance_m": walking_distance_m(lat, lng, park["entrances"]),
        "source": green_areas_source(),
    }


def territory_indicator(territory: dict) -> TerritoryIndicator:
    samples = territory["samples"]
    canopy_values = [
        estimate_canopy_percent(lat, lng, radius_m=300, patches=canopy_patches())
        for lat, lng in samples
    ]
    park_distances = [nearest_green_area_distance(lat, lng) for lat, lng in samples]
    canopy_mean = round(sum(canopy_values) / len(canopy_values), 1)
    distance_mean = round(sum(park_distances) / len(park_distances))
    pct_meets_30 = round(sum(value >= 30 for value in canopy_values) / len(canopy_values) * 100, 1)
    pct_meets_300 = round(sum(value <= 300 for value in park_distances) / len(park_distances) * 100, 1)
    deficit = ((100 - pct_meets_30) + (100 - pct_meets_300)) / 2
    return TerritoryIndicator(
        id=territory["id"],
        name=territory["name"],
        canopy_mean_300m=canopy_mean,
        park_distance_mean_m=distance_mean,
        pct_meets_30=pct_meets_30,
        pct_meets_300=pct_meets_300,
        green_inequality_index=round(deficit, 1),
    )


def nearby_parks(lat: float, lng: float, radius_m: int) -> list[dict]:
    candidates = nearby_items(lat, lng, radius_m, green_areas())
    parks = [
        rectangle_feature(
            park["lng"],
            park["lat"],
            park["width"],
            park["height"],
            {"name": park["name"]},
        )
        for park in candidates
    ]
    return parks


def nearby_canopy(lat: float, lng: float, radius_m: int) -> list[dict]:
    return [
        circle_polygon(patch["lng"], patch["lat"], patch["radius_m"])
        for patch in nearby_items(lat, lng, radius_m, canopy_patches())
    ]


def nearby_trees(lat: float, lng: float, radius_m: int) -> list[dict]:
    trees = [
        point_feature(tree["lng"], tree["lat"], {"species": tree["species"]})
        for tree in nearby_items(lat, lng, radius_m, tree_points())
    ]
    if len(trees) >= 3:
        return trees[:120]
    nearest = sorted(tree_points(), key=lambda tree: haversine_m(lat, lng, tree["lat"], tree["lng"]))[:3]
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


def park_feature(park: dict) -> dict:
    return rectangle_feature(
        park["lng"],
        park["lat"],
        park["width"],
        park["height"],
        {
            "name": park["name"],
            "distance_m": park["distance_m"],
            "source": park["source"],
        },
    )
