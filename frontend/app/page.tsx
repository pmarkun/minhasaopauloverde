"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";

type TreeVisibility = "yes" | "no";

type ScoreResponse = {
  location: { lat: number; lng: number };
  criteria: {
    trees_visible: { status: string; value: boolean | null; source: string; target: number };
    canopy: { status: string; canopy_100m: number; canopy_300m: number; target: number; source: string };
    park_access: { status: string; distance_m: number; name: string; target_m: number; source: string };
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
  nearest_park: FeatureCollection;
};

type GeocodeResponse = {
  lat: number;
  lng: number;
  label: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_TREECHECK_API_BASE_URL ??
  (typeof window !== "undefined" && window.location.port === "3000" ? "http://127.0.0.1:8000" : "");
const DEFAULT_LOCATION = { lat: -23.5614, lng: -46.6559 };
const STREET_STYLE = "https://tiles.openfreemap.org/styles/liberty";
const SATELLITE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    satellite: {
      type: "raster",
      tiles: [
        "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      attribution: "Imagery: Esri",
    },
  },
  layers: [{ id: "satellite", type: "raster", source: "satellite" }],
};
const SHARE_WIDTH = 1080;
const SHARE_HEIGHT = 1440;

export default function Home() {
  const mapContainer = useRef<HTMLDivElement | null>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const activeMapView = useRef<"street" | "satellite">("street");
  const [address, setAddress] = useState("Avenida Paulista");
  const [lat, setLat] = useState(String(DEFAULT_LOCATION.lat));
  const [lng, setLng] = useState(String(DEFAULT_LOCATION.lng));
  const [treesVisible, setTreesVisible] = useState<TreeVisibility | null>(null);
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [mapData, setMapData] = useState<MapDataResponse | null>(null);
  const [error, setError] = useState("");
  const [locationHint, setLocationHint] = useState("Pedimos sua localizacao para comecar pelo seu entorno.");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [mapView, setMapView] = useState<"street" | "satellite">("street");

  const parsedLocation = useMemo(
    () => ({ lat: Number(lat), lng: Number(lng) }),
    [lat, lng],
  );

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const mapOptions = {
      container: mapContainer.current,
      style: STREET_STYLE,
      center: [DEFAULT_LOCATION.lng, DEFAULT_LOCATION.lat],
      zoom: 15.8,
      interactive: true,
      preserveDrawingBuffer: true,
      attributionControl: false,
    } as maplibregl.MapOptions & { preserveDrawingBuffer: boolean };

    map.current = new maplibregl.Map(mapOptions);

    map.current.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
  }, []);

  useEffect(() => {
    requestGps(true);
  }, []);

  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap || !Number.isFinite(parsedLocation.lat) || !Number.isFinite(parsedLocation.lng)) return;

    currentMap.flyTo({ center: [parsedLocation.lng, parsedLocation.lat], zoom: 15.8, duration: 700 });
    if (currentMap.isStyleLoaded()) renderCurrentLocation(currentMap, parsedLocation, mapData);
    currentMap.once("load", () => renderCurrentLocation(currentMap, parsedLocation, mapData));
  }, [mapData, parsedLocation]);

  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap) return;
    if (activeMapView.current === mapView) return;

    activeMapView.current = mapView;
    currentMap.setStyle(mapView === "satellite" ? SATELLITE_STYLE : STREET_STYLE);
    renderWhenStyleReady(currentMap, parsedLocation, mapData);
  }, [mapView]);

  async function calculateScore() {
    setError("");
    if (!treesVisible) {
      setError("Responda sobre as 3 arvores da janela para calcular.");
      return;
    }
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
      radius_m: "300",
    });
    const response = await fetch(`${API_BASE}/map-data?${params}`);
    if (!response.ok) throw new Error("Nao foi possivel carregar o mapa do entorno.");
    setMapData(await response.json());
  }

  async function geocodeAddress() {
    setError("");
    try {
      const params = new URLSearchParams({ q: address });
      const response = await fetch(`${API_BASE}/geocode?${params}`);
      if (!response.ok) throw new Error("Endereco nao encontrado.");
      const result: GeocodeResponse = await response.json();
      setLat(result.lat.toFixed(6));
      setLng(result.lng.toFixed(6));
      setAddress(result.label);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro inesperado.");
    }
  }

  async function sharePng() {
    if (!score || !mapData) return;
    setExporting(true);
    try {
      const blob = await buildShareBlob(score, mapData, parsedLocation);
      const file = new File([blob], "minha-sao-paulo-verde.png", { type: "image/png" });
      const shareNavigator = navigator as Navigator & {
        canShare?: (data: ShareData) => boolean;
        share?: (data: ShareData) => Promise<void>;
      };
      if (shareNavigator.share && (!shareNavigator.canShare || shareNavigator.canShare({ files: [file] }))) {
        await shareNavigator.share({
          files: [file],
          title: "Minha Sao Paulo Verde",
          text: "Olha quanta natureza existe no entorno da minha casa.",
        });
      } else {
        triggerDownload(blob);
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Nao foi possivel compartilhar.");
    } finally {
      setExporting(false);
    }
  }

  function requestGps(isInitial = false) {
    setError("");
    if (!navigator.geolocation) {
      setLocationHint("GPS indisponivel neste navegador. Busque pelo endereco.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(position.coords.latitude.toFixed(6));
        setLng(position.coords.longitude.toFixed(6));
        setLocationHint("Usando sua localizacao atual. Voce tambem pode buscar outro endereco.");
      },
      () => {
        setLocationHint("Nao conseguimos usar sua localizacao. Busque pelo endereco.");
        if (!isInitial) setError("Nao foi possivel obter a localizacao.");
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  return (
    <main className="pageShell">
      <section className="introPanel">
        <p className="eyebrow">Minha Sao Paulo Verde</p>
        <h1>Quanto verde tem perto da sua casa?</h1>
        <p className="intro">
          Veja seu entorno em 300 metros e gere uma imagem para cobrar, comparar e compartilhar.
        </p>

        <fieldset>
          <legend>Da sua janela principal, da para ver pelo menos 3 arvores?</legend>
          <div className="segmented twoChoices">
            {[
              ["yes", "Sim :)"],
              ["no", "Nao :("],
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

        <div className="formStack">
          <label>
            Seu endereco em Sao Paulo
            <input value={address} onChange={(event) => setAddress(event.target.value)} />
          </label>
          <p className="locationHint">{locationHint}</p>
          <div className="buttonRow">
            <button className="secondary" onClick={geocodeAddress} type="button">
              Encontrar
            </button>
          </div>
        </div>

        <button className="primary" disabled={loading} onClick={calculateScore} type="button">
          {loading ? "Calculando..." : "Calcular"}
        </button>

        {error && <p className="error">{error}</p>}
      </section>

      <section className="shareCard" aria-label="Cartao de resultado">
        <div className="cardHeader">
          <div>
            <p className="eyebrow">Minha Sao Paulo Verde</p>
            <h2>{score ? scoreTierMessage(score.score.passed) : "Seu mapa de vizinhanca"}</h2>
          </div>
          <div className="scoreBadge">{score ? `${score.score.passed}/3` : "3-30-300"}</div>
        </div>

        <div className="mapFrame">
          <div ref={mapContainer} className="map" />
          <div className="mapToggle" aria-label="Tipo de mapa">
            <button className={mapView === "street" ? "active" : ""} onClick={() => setMapView("street")} type="button">
              Rua
            </button>
            <button
              className={mapView === "satellite" ? "active" : ""}
              onClick={() => setMapView("satellite")}
              type="button"
            >
              Satelite
            </button>
          </div>
          <div className="mapCaption">Seu entorno em 300 m</div>
        </div>

        {score ? (
          <>
            <div className="kpiGrid">
              <Metric label="Janela com 3 arvores" value={labelStatus(score.criteria.trees_visible.status)} />
              <Metric label="Verde no entorno" value={`${score.criteria.canopy.canopy_300m}%`} />
              <Metric label="Praca mais perto" value={`${score.criteria.park_access.distance_m} m`} />
            </div>

            <div className="nearestPark">
              <span>Area verde mais proxima</span>
              <strong>{score.criteria.park_access.name}</strong>
              <small>Distancia estimada. O caminho real pode variar.</small>
            </div>

            <div className="actionRow">
              <button className="primary" disabled={exporting} onClick={sharePng} type="button">
                {exporting ? "Preparando..." : "Compartilhar imagem"}
              </button>
            </div>
          </>
        ) : (
          <div className="emptyState">
            Busque seu endereco, responda sobre a vista da janela e veja o mapa do seu entorno.
          </div>
        )}

        <footer className="sourceLine">
          Dados: GeoSampa. Distancia estimada. <a href="/metodologia">Como calculamos?</a>
        </footer>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function renderCurrentLocation(
  map: maplibregl.Map,
  location: { lat: number; lng: number },
  data: MapDataResponse | null,
) {
  const point = pointFeature(location.lng, location.lat);
  upsertCircleLayer(map, "home-point", geojsonFeatureCollection([point]), {
    color: "#17231d",
    radius: 7,
    strokeColor: "#ffffff",
    strokeWidth: 3,
  });
  if (data) renderMapData(map, data);
}

function renderWhenStyleReady(
  map: maplibregl.Map,
  location: { lat: number; lng: number },
  data: MapDataResponse | null,
) {
  if (map.isStyleLoaded()) {
    renderCurrentLocation(map, location, data);
    return;
  }
  map.once("style.load", () => renderCurrentLocation(map, location, data));
}

function renderMapData(map: maplibregl.Map, data: MapDataResponse) {
  upsertFillLayer(map, "buffer-300m", data.user_buffer_300m, "#b7f0c8", 0.18);
  upsertLineLayer(map, "buffer-300m-line", "buffer-300m", "#127044", 2);
  upsertFillLayer(map, "canopy-layer", data.canopy, "#8fbe6b", 0.34);
  upsertLineLayer(map, "canopy-layer-line", "canopy-layer", "#4f8f46", 0.8);
  upsertFillLayer(map, "parks-layer", data.parks, "#35b66c", 0.32);
  upsertLineLayer(map, "parks-layer-line", "parks-layer", "#087a42", 1.5);
  upsertFillLayer(map, "nearest-park-layer", data.nearest_park, "#14b86f", 0.54);
  upsertLineLayer(map, "nearest-park-line", "nearest-park-layer", "#005f38", 2.5);
  upsertCircleLayer(map, "trees-layer", data.trees, {
    color: "#0f5132",
    radius: 2.6,
    strokeColor: "rgba(255,255,255,0.75)",
    strokeWidth: 0.8,
  });
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

function upsertCircleLayer(
  map: maplibregl.Map,
  id: string,
  data: FeatureCollection,
  options: { color: string; radius: number; strokeColor: string; strokeWidth: number },
) {
  if (!map.getSource(id)) {
    map.addSource(id, { type: "geojson", data });
    map.addLayer({
      id,
      type: "circle",
      source: id,
      paint: {
        "circle-radius": options.radius,
        "circle-color": options.color,
        "circle-stroke-width": options.strokeWidth,
        "circle-stroke-color": options.strokeColor,
      },
    });
    return;
  }
  (map.getSource(id) as maplibregl.GeoJSONSource).setData(data);
}

function labelStatus(status: string) {
  if (status === "passed") return "atendido";
  if (status === "failed") return "nao";
  return "nao sei";
}

function scoreTierMessage(passed: number) {
  if (passed >= 3) return "Seu entorno esta respirando verde";
  if (passed === 2) return "Quase la: o verde ja aparece";
  if (passed === 1) return "Tem verde, mas ainda falta perto";
  return "Seu entorno precisa de mais natureza";
}

function pointFeature(lng: number, lat: number) {
  return {
    type: "Feature" as const,
    geometry: {
      type: "Point" as const,
      coordinates: [lng, lat],
    },
    properties: {},
  };
}

function geojsonFeatureCollection(features: GeoJSON.Feature[]): FeatureCollection {
  return { type: "FeatureCollection", features };
}

async function buildShareBlob(
  score: ScoreResponse,
  data: MapDataResponse,
  location: { lat: number; lng: number },
): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = SHARE_WIDTH;
  canvas.height = SHARE_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas indisponivel.");

  ctx.fillStyle = "#f4f0e6";
  ctx.fillRect(0, 0, SHARE_WIDTH, SHARE_HEIGHT);

  roundRect(ctx, 70, 70, 940, 1300, 42, "#ffffff");

  ctx.fillStyle = "#0f3d2b";
  ctx.font = "700 42px Arial";
  ctx.fillText("Minha Sao Paulo Verde", 120, 155);
  ctx.font = "700 86px Arial";
  ctx.fillText(`${score.score.passed}/3`, 120, 255);
  ctx.font = "700 44px Arial";
  ctx.fillText("sinais de verde no entorno", 300, 230);

  drawMetric(ctx, "Janela com 3 arvores", labelStatus(score.criteria.trees_visible.status), 120, 345);
  drawMetric(ctx, "Verde no entorno de 300 m", `${score.criteria.canopy.canopy_300m}%`, 120, 465);
  drawMetric(ctx, "Area verde mais proxima", `${score.criteria.park_access.distance_m} m`, 120, 585);

  ctx.fillStyle = "#17392b";
  ctx.font = "700 34px Arial";
  ctx.fillText(score.criteria.park_access.name.slice(0, 42), 120, 695);
  ctx.fillStyle = "#607067";
  ctx.font = "26px Arial";
  ctx.fillText("Distancia estimada. O caminho real pode variar.", 120, 735);

  drawShareMap(ctx, data, location, 120, 790, 840, 420);

  ctx.fillStyle = "#596b61";
  ctx.font = "24px Arial";
  ctx.fillText("Dados: GeoSampa. Veja a metodologia no app.", 120, 1290);

  return await new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Falha ao criar PNG."))), "image/png");
  });
}

function drawMetric(ctx: CanvasRenderingContext2D, label: string, value: string, x: number, y: number) {
  ctx.fillStyle = "#607067";
  ctx.font = "26px Arial";
  ctx.fillText(label, x, y);
  ctx.fillStyle = "#113c2a";
  ctx.font = "700 52px Arial";
  ctx.fillText(value, x, y + 58);
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
  color: string,
) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.fill();
}

function triggerDownload(blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "minha-sao-paulo-verde.png";
  link.click();
  URL.revokeObjectURL(url);
}

function drawShareMap(
  ctx: CanvasRenderingContext2D,
  data: MapDataResponse,
  location: { lat: number; lng: number },
  x: number,
  y: number,
  width: number,
  height: number,
) {
  const bounds = featureBounds(data.user_buffer_300m) ?? {
    minLng: location.lng - 0.004,
    minLat: location.lat - 0.004,
    maxLng: location.lng + 0.004,
    maxLat: location.lat + 0.004,
  };
  const project = (lng: number, lat: number) => {
    const pad = 28;
    const innerWidth = width - pad * 2;
    const innerHeight = height - pad * 2;
    const lngSpan = bounds.maxLng - bounds.minLng || 0.001;
    const latSpan = bounds.maxLat - bounds.minLat || 0.001;
    return {
      x: x + pad + ((lng - bounds.minLng) / lngSpan) * innerWidth,
      y: y + pad + ((bounds.maxLat - lat) / latSpan) * innerHeight,
    };
  };

  roundRect(ctx, x, y, width, height, 24, "#e6efe2");
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, width, height);
  ctx.clip();

  drawFeatureCollection(ctx, data.canopy, project, "#8fbe6b", "rgba(79,143,70,0.7)", 0.9);
  drawFeatureCollection(ctx, data.parks, project, "#35b66c", "rgba(8,122,66,0.9)", 1.5);
  drawFeatureCollection(ctx, data.nearest_park, project, "#14b86f", "#005f38", 2.2);
  drawFeatureCollection(ctx, data.user_buffer_300m, project, "rgba(183,240,200,0.08)", "#127044", 3);

  const home = project(location.lng, location.lat);
  ctx.fillStyle = "#17231d";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.arc(home.x, home.y, 10, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fill();
  ctx.restore();

  ctx.strokeStyle = "#d6e4d9";
  ctx.lineWidth = 4;
  ctx.strokeRect(x, y, width, height);
}

function drawFeatureCollection(
  ctx: CanvasRenderingContext2D,
  collection: FeatureCollection,
  project: (lng: number, lat: number) => { x: number; y: number },
  fill: string,
  stroke: string,
  lineWidth: number,
) {
  for (const feature of collection.features) {
    drawGeometry(ctx, feature.geometry, project, fill, stroke, lineWidth);
  }
}

function drawGeometry(
  ctx: CanvasRenderingContext2D,
  geometry: GeoJSON.Geometry | null,
  project: (lng: number, lat: number) => { x: number; y: number },
  fill: string,
  stroke: string,
  lineWidth: number,
) {
  if (!geometry) return;
  const polygons =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];
  if (!polygons.length) return;

  ctx.fillStyle = fill;
  ctx.strokeStyle = stroke;
  ctx.lineWidth = lineWidth;
  for (const polygon of polygons) {
    ctx.beginPath();
    for (const ring of polygon) {
      ring.forEach(([lng, lat], index) => {
        const point = project(lng, lat);
        if (index === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
      });
      ctx.closePath();
    }
    ctx.fill();
    ctx.stroke();
  }
}

function featureBounds(collection: FeatureCollection) {
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  for (const feature of collection.features) {
    forEachCoordinate(feature.geometry, ([lng, lat]) => {
      minLng = Math.min(minLng, lng);
      minLat = Math.min(minLat, lat);
      maxLng = Math.max(maxLng, lng);
      maxLat = Math.max(maxLat, lat);
    });
  }
  if (!Number.isFinite(minLng)) return null;
  return { minLng, minLat, maxLng, maxLat };
}

function forEachCoordinate(geometry: GeoJSON.Geometry | null, visit: (coordinate: [number, number]) => void) {
  if (!geometry) return;
  if (geometry.type === "Point") {
    visit(geometry.coordinates as [number, number]);
  }
  if (geometry.type === "Polygon") {
    geometry.coordinates.flat().forEach((coordinate) => visit(coordinate as [number, number]));
  }
  if (geometry.type === "MultiPolygon") {
    geometry.coordinates.flat(2).forEach((coordinate) => visit(coordinate as [number, number]));
  }
}
