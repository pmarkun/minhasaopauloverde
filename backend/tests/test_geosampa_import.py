from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "tools"))

from geosampa_import import canopy_patch_from_feature, tree_point_from_feature


def test_tree_point_from_geosampa_point_feature() -> None:
    feature = {
        "type": "Feature",
        "id": "arvore.1",
        "properties": {"nome_popular": "Ipe"},
        "geometry": {"type": "Point", "coordinates": [-46.65, -23.56]},
    }

    tree = tree_point_from_feature(feature)

    assert tree == {
        "lat": -23.56,
        "lng": -46.65,
        "species": "Ipe",
        "source_id": "arvore.1",
    }


def test_canopy_patch_from_polygon_feature() -> None:
    feature = {
        "type": "Feature",
        "properties": {"objectid": 7},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-46.6500, -23.5600],
                [-46.6490, -23.5600],
                [-46.6490, -23.5590],
                [-46.6500, -23.5590],
                [-46.6500, -23.5600],
            ]],
        },
    }

    patch = canopy_patch_from_feature(feature)

    assert patch is not None
    assert patch["source_id"] == 7
    assert patch["radius_m"] > 8

