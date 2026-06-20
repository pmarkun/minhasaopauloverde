from contextlib import asynccontextmanager
from enum import Enum
import json
import os
from pathlib import Path
from typing import Annotated
import urllib.parse
import urllib.request
import zipfile

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from treecheck_api.data_repository import (
    canopy_patches_near,
    canopy_patches_source,
    green_areas_for_nearest,
    green_areas_near,
    green_areas_source,
    nearest_tree_points,
    pilot_territories,
    sample_addresses,
    tree_points_near,
)
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


def prepare_data_volume() -> None:
    data_dir = Path(os.environ.get("TREECHECK_DATA_DIR", "data/processed"))
    sqlite_path = data_dir / "treecheck.sqlite"
    zip_path = data_dir / "treecheck.sqlite.zip"
    if sqlite_path.exists() or not zip_path.exists():
        return
    data_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extract("treecheck.sqlite", data_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    prepare_data_volume()
    yield


app = FastAPI(title="TreeCheck API", version="0.1.0", lifespan=lifespan)

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
    nominatim = geocode_nominatim(q)
    if nominatim:
        return nominatim

    normalized = q.strip().lower()
    for key, (lat, lng, label) in sample_addresses().items():
        if key in normalized:
            return GeocodeResponse(query=q, lat=lat, lng=lng, label=label)

    raise HTTPException(status_code=404, detail="Endereco nao encontrado")


def geocode_nominatim(q: str) -> GeocodeResponse | None:
    params = urllib.parse.urlencode(
        {
            "q": f"{q}, Sao Paulo, SP, Brasil",
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 0,
            "countrycodes": "br",
            "viewbox": "-46.83,-23.35,-46.36,-24.05",
            "bounded": 0,
        },
    )
    request = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "TreeCheck MVP contato-local"},
    )
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.load(response)
    except Exception:
        return None
    if not payload:
        return None
    result = payload[0]
    return GeocodeResponse(
        query=q,
        lat=round(float(result["lat"]), 6),
        lng=round(float(result["lon"]), 6),
        label=result.get("display_name", q),
        source="nominatim_openstreetmap",
    )


@app.get("/score", response_model=ScoreResponse)
def score(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    trees_visible: TreeVisibility = TreeVisibility.unknown,
) -> ScoreResponse:
    canopy_100m = estimate_canopy_percent(lat, lng, radius_m=100, patches=canopy_patches_near(lat, lng, 100))
    canopy_300m = estimate_canopy_percent(lat, lng, radius_m=300, patches=canopy_patches_near(lat, lng, 300))
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
    park = min(green_areas_for_nearest(lat, lng), key=lambda item: walking_distance_m(lat, lng, item["entrances"]))
    return {
        **park,
        "distance_m": walking_distance_m(lat, lng, park["entrances"]),
        "source": green_areas_source(),
    }


def territory_indicator(territory: dict) -> TerritoryIndicator:
    samples = territory["samples"]
    canopy_values = [
        estimate_canopy_percent(lat, lng, radius_m=300, patches=canopy_patches_near(lat, lng, 300))
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
    candidates = green_areas_near(lat, lng, radius_m)
    parks = [
        rectangle_feature(
            park["lng"],
            park["lat"],
            park["width"],
            park["height"],
            {"name": park["name"]},
            geometry=park.get("geometry"),
        )
        for park in candidates
    ]
    return parks


def nearby_canopy(lat: float, lng: float, radius_m: int) -> list[dict]:
    return [
        polygon_or_circle_feature(patch)
        for patch in canopy_patches_near(lat, lng, radius_m)
    ]


def nearby_trees(lat: float, lng: float, radius_m: int) -> list[dict]:
    trees = [
        point_feature(tree["lng"], tree["lat"], {"species": tree["species"]})
        for tree in tree_points_near(lat, lng, radius_m)
    ]
    if len(trees) >= 3:
        return trees[:120]
    nearest = sorted(nearest_tree_points(lat, lng), key=lambda tree: haversine_m(lat, lng, tree["lat"], tree["lng"]))[:3]
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


def rectangle_feature(
    lng: float,
    lat: float,
    width: float,
    height: float,
    properties: dict,
    geometry: dict | None = None,
) -> dict:
    if geometry:
        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": properties,
        }
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
        geometry=park.get("geometry"),
    )


def polygon_or_circle_feature(patch: dict) -> dict:
    if patch.get("geometry"):
        return {
            "type": "Feature",
            "geometry": patch["geometry"],
            "properties": {"source_id": patch.get("source_id")},
        }
    return circle_polygon(patch["lng"], patch["lat"], patch["radius_m"])


FRONTEND_OUT = Path(__file__).resolve().parents[3] / "frontend" / "out"

if FRONTEND_OUT.exists():
    app.mount("/_next", StaticFiles(directory=FRONTEND_OUT / "_next"), name="next-static")


@app.get("/{page_path:path}", include_in_schema=False)
def frontend_page(page_path: str) -> FileResponse:
    if not FRONTEND_OUT.exists():
        raise HTTPException(status_code=404, detail="Frontend nao encontrado")
    requested = FRONTEND_OUT / page_path
    if requested.is_dir() and (requested / "index.html").exists():
        return FileResponse(requested / "index.html")
    if requested.is_file():
        return FileResponse(requested)
    return FileResponse(FRONTEND_OUT / "index.html")
