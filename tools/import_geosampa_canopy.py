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
    write_canopy_sqlite,
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
    parser.add_argument("--include-geometry", action="store_true", help="Inclui poligonos no JSON; aumenta muito o arquivo.")
    parser.add_argument(
        "--sqlite-output",
        default="data/processed/canopy_polygons.sqlite",
        help="Arquivo SQLite com poligonos reais e indice RTree.",
    )
    args = parser.parse_args()

    include_geometry = args.include_geometry or bool(args.sqlite_output)
    if Path(args.source).suffix.lower() in {".zip", ".shp"}:
        patches = []
        for item in iter_shapefile_records(args.source, default_epsg=31983):
            patch = canopy_patch_from_shape_record(item, include_geometry=include_geometry)
            if patch and (args.all or in_bbox(patch["lat"], patch["lng"], args.south, args.west, args.north, args.east)):
                patches.append(patch)
    else:
        payload = load_geojson(args.source)
        patches = [
            patch
            for feature in features(payload)
            if (patch := canopy_patch_from_feature(feature, include_geometry=include_geometry))
            and (args.all or in_bbox(patch["lat"], patch["lng"], args.south, args.west, args.north, args.east))
        ]
    if args.sqlite_output:
        write_canopy_sqlite(Path(args.sqlite_output), patches)
        print(f"wrote {len(patches)} GeoSampa canopy polygons to {args.sqlite_output}")
    json_patches = [
        {key: value for key, value in patch.items() if key not in {"geometry", "bounds"} or args.include_geometry}
        for patch in patches
    ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "geosampa_cobertura_vegetal", "canopy_patches": json_patches}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(json_patches)} GeoSampa canopy patches to {output}")


if __name__ == "__main__":
    main()
