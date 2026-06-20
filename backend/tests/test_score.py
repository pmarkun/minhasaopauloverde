from fastapi.testclient import TestClient

from treecheck_api.main import GeocodeResponse, app, recommendations, status_for_bool


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_geocode_known_address(monkeypatch) -> None:
    monkeypatch.setattr("treecheck_api.main.geocode_nominatim_options", lambda q, limit=5: [])
    response = client.get("/geocode?q=Avenida%20Paulista")
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Avenida Paulista, Sao Paulo"
    assert body["source"] == "sample_local"


def test_geocode_unknown_address_returns_404(monkeypatch) -> None:
    monkeypatch.setattr("treecheck_api.main.geocode_nominatim_options", lambda q, limit=5: [])
    response = client.get("/geocode?q=Endereco%20Inexistente%20XYZ")
    assert response.status_code == 404


def test_geocode_options_returns_candidates(monkeypatch) -> None:
    monkeypatch.setattr("treecheck_api.main.geocode_nominatim_options", lambda q, limit=5: [])
    response = client.get("/geocode-options?q=Avenida%20Paulista")
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Avenida Paulista"
    assert body["options"][0]["label"] == "Avenida Paulista, Sao Paulo"


def test_geocode_options_collapses_near_duplicate_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        "treecheck_api.main.geocode_nominatim_options",
        lambda q, limit=5: [
            GeocodeResponse(query=q, lat=-23.561400, lng=-46.655900, label="Avenida Paulista grafia 1"),
            GeocodeResponse(query=q, lat=-23.561430, lng=-46.655930, label="Avenida Paulista grafia 2"),
            GeocodeResponse(query=q, lat=-23.565000, lng=-46.662000, label="Avenida Paulista outro trecho"),
        ],
    )
    response = client.get("/geocode-options?q=Paulista%20sem%20sample")
    assert response.status_code == 200
    body = response.json()
    assert [option["label"] for option in body["options"]] == [
        "Avenida Paulista grafia 1",
        "Avenida Paulista outro trecho",
    ]


def test_indicators_contract() -> None:
    response = client.get("/indicators")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert "green_inequality_index" in body[0]
    assert 0 <= body[0]["pct_meets_30"] <= 100
    assert 0 <= body[0]["pct_meets_300"] <= 100


def test_score_contract() -> None:
    response = client.get("/score?lat=-23.55&lng=-46.63&trees_visible=yes")
    assert response.status_code == 200
    body = response.json()
    assert body["location"] == {"lat": -23.55, "lng": -46.63}
    assert body["score"]["total"] == 3
    assert 0 <= body["score"]["passed"] <= 3
    assert "canopy_100m" in body["criteria"]["canopy"]
    assert "distance_m" in body["criteria"]["park_access"]
    assert body["criteria"]["park_access"]["name"]
    assert body["criteria"]["canopy"]["source"] in {
        "sample_local",
        "openstreetmap_overpass_proxy",
        "geosampa_cobertura_vegetal",
    }
    assert body["criteria"]["park_access"]["source"].endswith("_walking_estimate")


def test_map_data_contract() -> None:
    response = client.get("/map-data?lat=-23.55&lng=-46.63&radius_m=300")
    assert response.status_code == 200
    body = response.json()
    assert body["parks"]["type"] == "FeatureCollection"
    assert body["canopy"]["type"] == "FeatureCollection"
    assert body["trees"]["type"] == "FeatureCollection"
    assert body["nearest_park"]["type"] == "FeatureCollection"
    assert len(body["trees"]["features"]) >= 3
    assert len(body["nearest_park"]["features"]) == 1
    assert body["nearest_park"]["features"][0]["properties"]["name"]


def test_map_data_radius_validation() -> None:
    response = client.get("/map-data?lat=-23.55&lng=-46.63&radius_m=20")
    assert response.status_code == 422


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
