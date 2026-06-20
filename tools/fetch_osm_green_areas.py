import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch public green areas from OpenStreetMap Overpass.")
    parser.add_argument("--south", type=float, default=-23.595)
    parser.add_argument("--west", type=float, default=-46.675)
    parser.add_argument("--north", type=float, default=-23.545)
    parser.add_argument("--east", type=float, default=-46.625)
    parser.add_argument("--output", default="data/processed/green_areas.json")
    args = parser.parse_args()

    query = build_query(args.south, args.west, args.north, args.east)
    request = urllib.request.Request(
        OVERPASS_URL,
        data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
        headers={"User-Agent": "TreeCheck MVP"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)

    green_areas = [area for area in parse_overpass(payload) if area["entrances"]]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "openstreetmap_overpass", "green_areas": green_areas}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(green_areas)} green areas to {output}")


def build_query(south: float, west: float, north: float, east: float) -> str:
    bbox = f"{south},{west},{north},{east}"
    tags = """
      way["leisure"~"^(park|garden|recreation_ground|nature_reserve)$"]["access"!~"private"]({bbox});
      relation["leisure"~"^(park|garden|recreation_ground|nature_reserve)$"]["access"!~"private"]({bbox});
    """
    return f"""
    [out:json][timeout:45];
    (
      {tags.format(bbox=bbox)}
    );
    out center tags;
    """


def parse_overpass(payload: dict) -> list[dict]:
    areas = []
    for element in payload.get("elements", []):
        center = element.get("center")
        tags = element.get("tags", {})
        if not center:
            continue
        lat = center["lat"]
        lng = center["lon"]
        name = tags.get("name") or tags.get("leisure") or f"osm-{element['id']}"
        areas.append(
            {
                "name": name,
                "lat": lat,
                "lng": lng,
                "width": 0.0025,
                "height": 0.002,
                "entrances": [(lat, lng)],
                "osm_id": element["id"],
            },
        )
    return areas


if __name__ == "__main__":
    main()

