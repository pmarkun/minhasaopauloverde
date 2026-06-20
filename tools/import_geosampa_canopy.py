import argparse
import json
from pathlib import Path

from geosampa_import import (
    canopy_patch_from_feature,
    canopy_patch_from_shape_record,
    features,
    in_bbox,
    iter_shapefile_records,
    load_geojson,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoSampa cobertura vegetal GeoJSON into TreeCheck.")
    parser.add_argument("source", help="GeoJSON file path or URL exported from GeoSampa.")
    parser.add_argument("--output", default="data/processed/canopy_patches.json")
    parser.add_argument("--south", type=float, default=-23.595)
    parser.add_argument("--west", type=float, default=-46.675)
    parser.add_argument("--north", type=float, default=-23.545)
    parser.add_argument("--east", type=float, default=-46.625)
    parser.add_argument("--all", action="store_true", help="Importa Sao Paulo inteira, sem filtrar pelo bbox piloto.")
    args = parser.parse_args()

    if Path(args.source).suffix.lower() in {".zip", ".shp"}:
        patches = []
        for item in iter_shapefile_records(args.source, default_epsg=31983):
            patch = canopy_patch_from_shape_record(item)
            if patch and (args.all or in_bbox(patch["lat"], patch["lng"], args.south, args.west, args.north, args.east)):
                patches.append(patch)
    else:
        payload = load_geojson(args.source)
        patches = [
            patch
            for feature in features(payload)
            if (patch := canopy_patch_from_feature(feature))
            and (args.all or in_bbox(patch["lat"], patch["lng"], args.south, args.west, args.north, args.east))
        ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "geosampa_cobertura_vegetal", "canopy_patches": patches}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(patches)} GeoSampa canopy patches to {output}")


if __name__ == "__main__":
    main()
