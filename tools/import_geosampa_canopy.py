import argparse
import json
from pathlib import Path

from geosampa_import import canopy_patch_from_feature, features, load_geojson


def main() -> None:
    parser = argparse.ArgumentParser(description="Import GeoSampa cobertura vegetal GeoJSON into TreeCheck.")
    parser.add_argument("source", help="GeoJSON file path or URL exported from GeoSampa.")
    parser.add_argument("--output", default="data/processed/canopy_patches.json")
    args = parser.parse_args()

    payload = load_geojson(args.source)
    patches = [patch for feature in features(payload) if (patch := canopy_patch_from_feature(feature))]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": "geosampa_cobertura_vegetal", "canopy_patches": patches}, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {len(patches)} GeoSampa canopy patches to {output}")


if __name__ == "__main__":
    main()

