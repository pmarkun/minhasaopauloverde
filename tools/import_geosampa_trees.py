import argparse
import json
from pathlib import Path

from geosampa_import import (
    features,
    in_bbox,
    iter_shapefile_records,
    load_geojson,
    tree_point_from_feature,
    tree_point_from_shape_record,
    write_trees_sqlite,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoSampa arborizacao viaria GeoJSON into TreeCheck.")
    parser.add_argument("source", help="GeoJSON file path or URL exported from GeoSampa.")
    parser.add_argument("--output", default="data/processed/tree_points.json")
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

    if Path(args.source).suffix.lower() in {".zip", ".shp"}:
        trees = []
        for item in iter_shapefile_records(args.source, default_epsg=31983):
            tree = tree_point_from_shape_record(item)
            if tree and (args.all or in_bbox(tree["lat"], tree["lng"], args.south, args.west, args.north, args.east)):
                trees.append(tree)
    else:
        payload = load_geojson(args.source)
        trees = [
            tree
            for feature in features(payload)
            if (tree := tree_point_from_feature(feature))
            and (args.all or in_bbox(tree["lat"], tree["lng"], args.south, args.west, args.north, args.east))
        ]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "geosampa_arborizacao_viaria", "tree_points": trees}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(trees)} GeoSampa tree points to {output}")
    if args.sqlite_output:
        write_trees_sqlite(Path(args.sqlite_output), trees)
        print(f"wrote {len(trees)} GeoSampa tree points to {args.sqlite_output}")


if __name__ == "__main__":
    main()
