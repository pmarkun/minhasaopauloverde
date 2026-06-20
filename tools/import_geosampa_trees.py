import argparse
import json
from pathlib import Path

from geosampa_import import features, load_geojson, tree_point_from_feature


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoSampa arborizacao viaria GeoJSON into TreeCheck.")
    parser.add_argument("source", help="GeoJSON file path or URL exported from GeoSampa.")
    parser.add_argument("--output", default="data/processed/tree_points.json")
    args = parser.parse_args()

    payload = load_geojson(args.source)
    trees = [tree for feature in features(payload) if (tree := tree_point_from_feature(feature))]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "geosampa_arborizacao_viaria", "tree_points": trees}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(trees)} GeoSampa tree points to {output}")


if __name__ == "__main__":
    main()

