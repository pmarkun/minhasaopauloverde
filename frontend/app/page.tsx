"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";

type TreeVisibility = "yes" | "no" | "unknown";

type ScoreResponse = {
  location: { lat: number; lng: number };
  criteria: {
    trees_visible: { status: string; value: boolean | null; source: string; target: number };
    canopy: { status: string; canopy_100m: number; canopy_300m: number; target: number };
    park_access: { status: string; distance_m: number; target_m: number };
  };
  score: { passed: number; total: number };
  recommendations: string[];
};

type FeatureCollection = GeoJSON.FeatureCollection;

type MapDataResponse = {
  user_buffer_300m: FeatureCollection;
  parks: FeatureCollection;
  canopy: FeatureCollection;
  trees: FeatureCollection;
};

const API_BASE = process.env.NEXT_PUBLIC_TREECHECK_API_BASE_URL ?? "http://127.0.0.1:8000";
const DEFAULT_LOCATION = { lat: -23.55, lng: -46.63 };

export default function Home() {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [lat, setLat] = useState(String(DEFAULT_LOCATION.lat));
  const [lng, setLng] = useState(String(DEFAULT_LOCATION.lng));
  const [treesVisible, setTreesVisible] = useState<TreeVisibility>("unknown");
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [mapData, setMapData] = useState<MapDataResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const parsedLocation = useMemo(
    () => ({ lat: Number(lat), lng: Number(lng) }),
    [lat, lng],
  );

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [DEFAULT_LOCATION.lng, DEFAULT_LOCATION.lat],
      zoom: 13,
    });

    map.current.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  }, []);

  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap || !Number.isFinite(parsedLocation.lat) || !Number.isFinite(parsedLocation.lng)) return;

    currentMap.flyTo({ center: [parsedLocation.lng, parsedLocation.lat], zoom: 14 });
    const sourceId = "user-location";
    const point = {
      type: "Feature" as const,
      geometry: {
        type: "Point" as const,
        coordinates: [parsedLocation.lng, parsedLocation.lat],
      },
      properties: {},
    };

    const upsertLayers = () => {
      if (!currentMap.getSource(sourceId)) {
        currentMap.addSource(sourceId, { type: "geojson", data: point });
        currentMap.addLayer({
          id: sourceId,
          type: "circle",
          source: sourceId,
          paint: {
            "circle-radius": 8,
            "circle-color": "#0f766e",
            "circle-stroke-width": 3,
            "circle-stroke-color": "#ffffff",
          },
        });
      } else {
        (currentMap.getSource(sourceId) as maplibregl.GeoJSONSource).setData(point);
      }

      if (mapData) renderMapData(currentMap, mapData);
    };

    if (currentMap.isStyleLoaded()) upsertLayers();
    currentMap.once("load", upsertLayers);
  }, [mapData, parsedLocation]);

  async function calculateScore() {
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams({
        lat: String(parsedLocation.lat),
        lng: String(parsedLocation.lng),
        trees_visible: treesVisible,
      });
      const response = await fetch(`${API_BASE}/score?${params}`);
      if (!response.ok) throw new Error("Nao foi possivel calcular o score.");
      setScore(await response.json());
      await loadMapData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
    } finally {
      setLoading(false);
    }
  }

  async function loadMapData() {
    const params = new URLSearchParams({
      lat: String(parsedLocation.lat),
      lng: String(parsedLocation.lng),
    });
    const response = await fetch(`${API_BASE}/map-data?${params}`);
    if (!response.ok) throw new Error("Nao foi possivel carregar as camadas do mapa.");
    setMapData(await response.json());
  }

  function useGps() {
    setError("");
    if (!navigator.geolocation) {
      setError("GPS indisponivel neste navegador.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(position.coords.latitude.toFixed(6));
        setLng(position.coords.longitude.toFixed(6));
      },
      () => setError("Nao foi possivel obter a localizacao."),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  return (
    <main className="shell">
      <section className="panel">
        <div>
          <p className="eyebrow">TreeCheck Brasil</p>
          <h1>Score 3-30-300</h1>
          <p className="intro">Avalie acesso a arvores, cobertura arborea e areas verdes publicas perto de casa.</p>
        </div>

        <div className="grid">
          <label>
            Latitude
            <input value={lat} onChange={(event) => setLat(event.target.value)} inputMode="decimal" />
          </label>
          <label>
            Longitude
            <input value={lng} onChange={(event) => setLng(event.target.value)} inputMode="decimal" />
          </label>
        </div>

        <button className="secondary" onClick={useGps} type="button">
          Usar GPS
        </button>

        <fieldset>
          <legend>Da principal janela voce ve pelo menos 3 arvores?</legend>
          <div className="segmented">
            {[
              ["yes", "Sim"],
              ["no", "Nao"],
              ["unknown", "Nao sei"],
            ].map(([value, label]) => (
              <button
                className={treesVisible === value ? "active" : ""}
                key={value}
                onClick={() => setTreesVisible(value as TreeVisibility)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </fieldset>

        <button className="primary" disabled={loading} onClick={calculateScore} type="button">
          {loading ? "Calculando..." : "Calcular score"}
        </button>

        {error && <p className="error">{error}</p>}

        {score && (
          <section className="result" aria-label="Resultado">
            <h2>
              {score.score.passed}/{score.score.total} criterios atendidos
            </h2>
            <ul>
              <li>3 arvores visiveis: {labelStatus(score.criteria.trees_visible.status)}</li>
              <li>Cobertura 100 m: {score.criteria.canopy.canopy_100m}%</li>
              <li>Cobertura 300 m: {score.criteria.canopy.canopy_300m}%</li>
              <li>Area verde mais proxima: {score.criteria.park_access.distance_m} m</li>
            </ul>
            {score.recommendations.length > 0 && (
              <div>
                <h3>Recomendacoes</h3>
                <ul>
                  {score.recommendations.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </section>

      <section className="mapWrap" aria-label="Mapa">
        <div ref={mapContainer} className="map" />
        <div className="legend" aria-label="Legenda">
          <span><b className="swatch buffer" />300 m</span>
          <span><b className="swatch canopy" />Cobertura</span>
          <span><b className="swatch park" />Areas verdes</span>
          <span><b className="swatch tree" />Arvores</span>
        </div>
      </section>
    </main>
  );
}

function renderMapData(map: maplibregl.Map, data: MapDataResponse) {
  upsertFillLayer(map, "buffer-300m", data.user_buffer_300m, "#86efac", 0.2);
  upsertLineLayer(map, "buffer-300m-line", "buffer-300m", "#15803d", 2);
  upsertFillLayer(map, "canopy-layer", data.canopy, "#166534", 0.42);
  upsertFillLayer(map, "parks-layer", data.parks, "#34d399", 0.48);
  upsertLineLayer(map, "parks-layer-line", "parks-layer", "#047857", 2);
  upsertCircleLayer(map, "trees-layer", data.trees);
}

function upsertFillLayer(
  map: maplibregl.Map,
  id: string,
  data: FeatureCollection,
  color: string,
  opacity: number,
) {
  if (!map.getSource(id)) {
    map.addSource(id, { type: "geojson", data });
    map.addLayer({
      id,
      type: "fill",
      source: id,
      paint: { "fill-color": color, "fill-opacity": opacity },
    });
    return;
  }
  (map.getSource(id) as maplibregl.GeoJSONSource).setData(data);
}

function upsertLineLayer(map: maplibregl.Map, id: string, sourceId: string, color: string, width: number) {
  if (map.getLayer(id)) return;
  map.addLayer({
    id,
    type: "line",
    source: sourceId,
    paint: { "line-color": color, "line-width": width },
  });
}

function upsertCircleLayer(map: maplibregl.Map, id: string, data: FeatureCollection) {
  if (!map.getSource(id)) {
    map.addSource(id, { type: "geojson", data });
    map.addLayer({
      id,
      type: "circle",
      source: id,
      paint: {
        "circle-radius": 5,
        "circle-color": "#14532d",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
    return;
  }
  (map.getSource(id) as maplibregl.GeoJSONSource).setData(data);
}

function labelStatus(status: string) {
  if (status === "passed") return "atendido";
  if (status === "failed") return "nao atendido";
  return "nao informado";
}
