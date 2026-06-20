from enum import Enum
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

