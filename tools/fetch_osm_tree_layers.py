import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch tree and canopy proxy layers from OpenStreetMap.")
    parser.add_argument("--south", type=float, default=-23.595)
    parser.add_argument("--west", type=float, default=-46.675)
    parser.add_argument("--north", type=float, default=-23.545)
    parser.add_argument("--east", type=float, default=-46.625)
    parser.add_argument("--output-dir", default="data/processed")
    args = parser.parse_args()

    payload = fetch(build_query(args.south, args.west, args.north, args.east))
    canopy_patches, tree_points = parse_overpass(payload)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "canopy_patches.json").write_text(
        json.dumps({"source": "openstreetmap_overpass_proxy", "canopy_patches": canopy_patches}, indent=2),
        encoding="utf-8",
    )
    (output_dir / "tree_points.json").write_text(
        json.dumps({"source": "openstreetmap_overpass", "tree_points": tree_points}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(canopy_patches)} canopy patches and {len(tree_points)} tree points to {output_dir}")


def fetch(query: str) -> dict:
    request = urllib.request.Request(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
        headers={"User-Agent": "TreeCheck MVP"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def build_query(south: float, west: float, north: float, east: float) -> str:
    bbox = f"{south},{west},{north},{east}"
    return f"""
    [out:json][timeout:45];
    (
      node["natural"="tree"]({bbox});
      way["natural"~"^(wood|tree_row)$"]({bbox});
      relation["natural"~"^(wood|tree_row)$"]({bbox});
      way["landuse"="forest"]({bbox});
      relation["landuse"="forest"]({bbox});
    );
    out center tags;
    """


def parse_overpass(payload: dict) -> tuple[list[dict], list[dict]]:
    canopy_patches = []
    tree_points = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        point = center_or_node(element)
        if not point:
            continue
        lat, lng = point
        if element["type"] == "node" and tags.get("natural") == "tree":
            tree_points.append({"lat": lat, "lng": lng, "species": tags.get("species", "osm")})
            canopy_patches.append({"lat": lat, "lng": lng, "radius_m": 6})
            continue
        canopy_patches.append(
            {
                "lat": lat,
                "lng": lng,
                "radius_m": radius_for(tags),
                "osm_id": element["id"],
            },
        )
    return canopy_patches, tree_points


def center_or_node(element: dict) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return element["lat"], element["lon"]
    center = element.get("center")
    if center:
        return center["lat"], center["lon"]
    return None


def radius_for(tags: dict) -> int:
    if tags.get("natural") == "tree_row":
        return 18
    if tags.get("natural") == "wood" or tags.get("landuse") == "forest":
        return 90
    return 35


if __name__ == "__main__":
    main()

