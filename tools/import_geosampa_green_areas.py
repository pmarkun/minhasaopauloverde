import argparse
import json
from pathlib import Path

from geosampa_import import green_area_from_shape_record, in_bbox, iter_shapefile_records, write_green_areas_sqlite


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoSampa pracas/largos Shapefile into TreeCheck.")
    parser.add_argument("source", help="Shapefile .zip or .shp from GeoSampa.")
    parser.add_argument("--output", default="data/processed/green_areas.json")
    parser.add_argument("--south", type=float, default=-23.595)
    parser.add_argument("--west", type=float, default=-46.675)
    parser.add_argument("--north", type=float, default=-23.545)
    parser.add_argument("--east", type=float, default=-46.625)
    parser.add_argument("--all", action="store_true", help="Importa Sao Paulo inteira, sem filtrar pelo bbox piloto.")
    parser.add_argument(
        "--sqlite-output",
        default="data/processed/treecheck.sqlite",
        help="Arquivo SQLite operacional com indice RTree.",
    )
    args = parser.parse_args()

    green_areas = []
    for item in iter_shapefile_records(args.source, default_epsg=31983):
        area = green_area_from_shape_record(item)
        if not area:
            continue
        if args.all or in_bbox(area["lat"], area["lng"], args.south, args.west, args.north, args.east):
            green_areas.append(area)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "geosampa_praca_largo", "green_areas": green_areas}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(green_areas)} GeoSampa green areas to {output}")
    if args.sqlite_output:
        write_green_areas_sqlite(Path(args.sqlite_output), green_areas)
        print(f"wrote {len(green_areas)} GeoSampa green areas to {args.sqlite_output}")


if __name__ == "__main__":
    main()
