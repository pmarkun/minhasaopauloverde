from fastapi.testclient import TestClient

from treecheck_api.main import app, recommendations, status_for_bool


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_score_contract() -> None:
    response = client.get("/score?lat=-23.55&lng=-46.63&trees_visible=yes")
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == {"lat": -23.55, "lng": -46.63}
    assert body["score"]["total"] == 3
    assert 0 <= body["score"]["passed"] <= 3
    assert "canopy_100m" in body["criteria"]["canopy"]
    assert "distance_m" in body["criteria"]["park_access"]


def test_map_data_contract() -> None:
    response = client.get("/map-data?lat=-23.55&lng=-46.63")
    assert response.status_code == 200
    body = response.json()
    assert body["parks"]["type"] == "FeatureCollection"
    assert body["canopy"]["type"] == "FeatureCollection"
    assert body["trees"]["type"] == "FeatureCollection"
    assert len(body["parks"]["features"]) >= 1
    assert len(body["trees"]["features"]) >= 3


def test_unknown_tree_visibility_does_not_pass() -> None:
    response = client.get("/score?lat=-23.55&lng=-46.63")
    body = response.json()
    assert body["criteria"]["trees_visible"]["status"] == "unknown"
    assert body["criteria"]["trees_visible"]["value"] is None


def test_status_for_bool() -> None:
    assert status_for_bool(True) == "passed"
    assert status_for_bool(False) == "failed"
    assert status_for_bool(False, known=False) == "unknown"


def test_recommendations_for_failed_inputs() -> None:
    items = recommendations(24.0, 480, trees_visible="no")  # type: ignore[arg-type]
    assert "Faltam 6.0 pontos percentuais para atingir 30%." in items
    assert "O parque mais proximo esta 180 m alem da meta de 300 m." in items
